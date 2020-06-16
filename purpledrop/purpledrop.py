"""Low-level driver for communicating with PurpleDrop via serial messages
"""
import inspect
import logging
import queue
import serial
import serial.tools.list_ports
import sys
import threading
import time
from typing import Any, AnyStr, Callable, List, Optional, Sequence

import purpledrop.messages as messages
import purpledrop.protobuf.messages_pb2 as messages_pb2
from .messages import PurpleDropMessage, ElectrodeEnableMsg, SetPwmMsg
from .message_framer import MessageFramer, serialize
from .move_drop import move_drop, MoveDropResult

logger = logging.getLogger("purpledrop")

def resolve_msg_filter(filt):
    """If the filter provided is a message type, then create a filter which returns
    any message of that type. Otherwise, assume the filter is a lambda method.
    """
    if inspect.isclass(filt): # and issubclass(filt, PurpleDropMessage):
        return lambda x: isinstance(x, filt)
    else:
        return filt

def list_purpledrop_devices():
    devices = serial.tools.list_ports.comports()
    devices = [x for x in devices if x.vid == 0x02dd and x.pid == 0x7da3]
    return devices

def parameter_list():
    """Return the config parameters for the embedded software

    This should be configurable eventually. Or better yet come from the device.
    """
    def make_param(id, name, description, type="int"):
        if not isinstance(id, int) or type not in ["int", "float", "bool"]:
            raise ValueError(f"Invalid param: {id}: {name} {type}")
        return {
                "id": id,
                "name": name,
                "description": description,
                "type": type,
            }

    return [
        make_param(10, "HV Control Enabled", "Enable feedback control", "bool"),
        make_param(11, "HV Voltage Setting", "High voltage regulator output setting in volts", "float"),
        make_param(12, "HV Target Out", "V target out when regulator is disabled (counts, 0-4095)"),
        make_param(20, "Scan Sync Pin", "Set timing of the capacitance scan sync to given electrode"),
        make_param(21, "Scan Start Delay", "ns, Settling time before first scan measurement"),
        make_param(22, "Scan Blank Delay", "ns, Settling time after each scan measurement"),
        make_param(23, "Sample Delay", "ns, Time between first and second integrator sample"),
        make_param(24, "Blanking Delay", "ns, Time between blank and integrator reset for active measure"),
        make_param(25, "Integrator Reset Delay", "ns, Time between reset release and first sample"),
        make_param(26, "Augment Top Plate Low Side", "Enable the extra FET to pulldown GND", "bool"),
        make_param(30, "Top Plate Pin", "Pin number of HV507 output driving top plate"),
    ]

class PurpleDropRxThread(object):
    def __init__(self, port: serial.Serial, callback: Callable[[PurpleDropMessage], None]=None):
        self._thread = threading.Thread(target=self.run, name="PurpleDrop Rx", daemon=True)
        self._ser = port
        self._framer = MessageFramer(PurpleDropMessage.predictSize)
        self._callback = callback
        self.running = True

    def start(self):
        self._thread.start()

    def stop(self):
        self.running = False

    def join(self):
        self._thread.join()

    def run(self):
        while self.running:
            rxBytes = None
            try:
                rxBytes = self._ser.read(64)
            except serial.serialutil.SerialException as e:
                logger.warn(f"Failed reading from port: {e}")
                self.running = False
                return
            if(len(rxBytes) > 0):
                for buf in self._framer.parse(rxBytes):
                    if(self._callback):
                        try:
                            self._callback(PurpleDropMessage.from_bytes(buf))
                        except Exception as e:
                            logger.error(f"Exception in RxThread callback: {e}")


    def set_callback(self, callback):
        self._callback = callback

class SyncListener(object):
    def __init__(self, owner, msg_filter=None):
        self.owner = owner
        self.filter = resolve_msg_filter(msg_filter)

        self.fifo = queue.Queue()

    def __del__(self):
        self.owner.unregister_listener(self)

    def push_msg(self, msg: PurpleDropMessage):
        if self.filter is None or self.filter(msg):
            self.fifo.put(msg)

    def wait(self, timeout: Optional[float]=None) -> Optional[PurpleDropMessage]:
        try:
            return self.fifo.get(timeout=timeout)
        except queue.Empty:
            return None

class AsyncListener(object):
    def __init__(self, owner, callback, msg_filter=None):
        self.owner = owner
        self.callback = callback
        self.filter = resolve_msg_filter(msg_filter)

    def __del__(self):
        self.owner.unregister_listener(self)

    def push_msg(self, msg: PurpleDropMessage):
        if self.filter is None or self.filter(msg):
            self.callback(msg)

class PurpleDropDevice():
    """Low level messaging for controlling a PurpleDrop via a serial port

    Use `list_purpledrop_devices()` to find devices based on their USB VID/PID
    and serial number. Then provide the com port (e.g. `/dev/ttyACM0`) when
    instantiating a PurpleDropDevice.

    NOTE: This class provides low level control of the device. For most uses,
    you should be using PurpleDropControl which provides higher level
    functionality and matches the JSON-RPC methods provided by `pd-server`.
    """
    def __init__(self, port=None):
        self._rx_thread = None
        self._ser = None
        self.lock = threading.Lock()
        self.listeners = []

        if port is not None:
            self.open(port)

    def open(self, port):
        self.close() # close any opened ports
        logger.debug(f"PurpleDropDevice: opening {port}")
        self._ser = serial.Serial(port, timeout=0.01, write_timeout=0.5)
        self._rx_thread = PurpleDropRxThread(self._ser, callback=self.message_callback)
        self._rx_thread.start()

    def close(self):
        logger.debug("Closing PurpleDropDevice")
        if self._rx_thread is not None:
            self._rx_thread.stop()
            self._rx_thread.join()
        if self._ser is not None:
            self._ser.close()

    def connected(self):
        return self._ser is not None and \
            self._rx_thread is not None and \
            self._rx_thread.running

    def unregister_listener(self, listener):
        with self.lock:
            self.listeners.remove(listener)

    def get_sync_listener(self, msg_filter=None):
        new_listener = SyncListener(owner=self, msg_filter=msg_filter)
        with self.lock:
            self.listeners.append(new_listener)
        return new_listener

    def get_async_listener(self, callback, msg_filter=None):
        new_listener = AsyncListener(owner=self, callback=callback, msg_filter=msg_filter)
        with self.lock:
            self.listeners.append(new_listener)
        return new_listener

    def send_message(self, msg: PurpleDropMessage):
        tx_bytes = serialize(msg.to_bytes())
        with self.lock:
            self._ser.write(tx_bytes)

    def message_callback(self, msg: PurpleDropMessage):
        with self.lock:
            for l in self.listeners:
                l.push_msg(msg)

class PersistentPurpleDropDevice(PurpleDropDevice):
    """A wrapper for PurpleDropDevice that transparently tries to
    connect/reconnect to a device.

    If a serial is provided, it will only connect to that serial number.
    Otherwise, it will connect to any purple drop detected (and may choose
    one arbitrarilty if there are multiple).
    """
    def __init__(self, serial_number: Optional[str]=None):
        super().__init__()
        self.target_serial_number: Optional[str] = serial_number
        self.device_info: Optional[Any]
        self.__thread = threading.Thread(
            name="PersistentPurpleDropDevice Monitor",
            target=self.__thread_entry,
            daemon=True)
        self.__thread.start()

    def connected_serial_number(self) -> Optional[str]:
        """Returns the serial number of the connected device
        """
        if self.device_info is None:
            return None
        else:
            return self.device_info.serial_number

    def __try_to_connect(self) -> bool:
        device_list = list_purpledrop_devices()
        selected_device = None
        if len(device_list) == 0:
            logger.debug("No purpledrop devices found to connect to")
            return False
        if self.target_serial_number:
            for device in device_list:
                if device.serial_number == self.target_serial_number:
                    selected_device = device
        else:
            selected_device = device_list[0]

        if selected_device is None:
            serial_numbers = [d.serial_number for d in device_list]
            logger.warn(f"Found purpledrop, but not connecting because it has unexpected serial number ({serial_numbers}")
            return False

        self.open(selected_device.device)
        self.device_info = selected_device
        logger.warning(f"Connected to purpledrop {selected_device.serial_number} on {selected_device.device}")
        return True

    def __thread_entry(self):
        status = False
        while True:
            if not self.connected():
                if status:
                    logger.warning("Closing purpledrop device")
                    self.close()
                    status = False
                logger.debug("Attempting to connect to purpledrop")
                status = self.__try_to_connect()
            time.sleep(5.0)

class PurpleDropController(object):
    # Define the method names which will be made available via RPC server
    RPC_METHODS = [
        'get_board_definition',
        'get_parameter_definitions',
        'get_parameter',
        'set_parameter',
        'get_bulk_capacitance',
        'get_active_capacitance',
        'set_electrode_pins',
        'get_electrode_pins',
        'move_drop',
        'get_temperatures',
        'set_pwm_duty_cycle',
        'get_hv_supply_voltage',
    ]

    def __init__(self, purpledrop):
        self.purpledrop = purpledrop
        self.active_capacitance = 0.0
        self.bulk_capacitance = []
        self.temperatures: Sequence[float] = []
        self.duty_cycles = {}
        self.hv_supply_voltage = 0.0
        self.parameter_list = parameter_list()
        self.lock = threading.Lock()
        self.event_listeners = []
        self.active_capacitance_counter = 0
        self.hv_regulator_counter = 0
        self.pin_state = [False] * 128

        def msg_filter(msg):
            desired_types = [
                messages.ActiveCapacitanceMsg,
                messages.BulkCapacitanceMsg,
                messages.CommandAckMsg,
                messages.TemperatureMsg,
                messages.HvRegulatorMsg,
            ]

            for t in desired_types:
                if isinstance(msg, t):
                    return True
            return False

        self.purpledrop.get_async_listener(self.__message_callback, msg_filter)

    def __message_callback(self, msg):
        if isinstance(msg, messages.ActiveCapacitanceMsg):
            self.active_capacitance = msg.measurement - msg.baseline
            self.active_capacitance_counter += 1
            # Throttle the events. 500Hz messages is a lot for the browser to process.
            # This also means logs don't have a full resolution, and it would be better
            # if clients could choose what they get
            if (self.active_capacitance_counter % 50) == 0:
                cap_event = messages_pb2.PurpleDropEvent()
                cap_event.active_capacitance.measurement.capacitance = float(self.active_capacitance)
                cap_event.active_capacitance.measurement.drop_present = False
                self.__fire_event(cap_event)

        elif isinstance(msg, messages.BulkCapacitanceMsg):
            if len(self.bulk_capacitance) < msg.start_index + msg.count:
                self.bulk_capacitance.extend([0] * (msg.start_index + msg.count - len(self.bulk_capacitance)))
            for i in range(msg.count):
                self.bulk_capacitance[msg.start_index + i] = msg.measurements[i]
            bulk_event = messages_pb2.PurpleDropEvent()
            def make_cap_measurement(raw):
                m = messages_pb2.CapacitanceMeasurement()
                m.capacitance = float(raw)
                m.drop_present = raw > 50
                return m
            bulk_event.bulk_capacitance.measurements.extend([make_cap_measurement(x) for x in self.bulk_capacitance])
            self.__fire_event(bulk_event)

        elif isinstance(msg, messages.HvRegulatorMsg):
            self.hv_regulator_counter += 1
            if (self.hv_regulator_counter % 10) == 0:
                self.hv_supply_voltage = msg.voltage
                event = messages_pb2.PurpleDropEvent()
                event.hv_regulator.voltage = msg.voltage
                event.hv_regulator.v_target_out = msg.v_target_out
                self.__fire_event(event)

        elif isinstance(msg, messages.TemperatureMsg):
            self.temperatures = [float(x) / 100.0 for x in msg.measurements]
            event = messages_pb2.PurpleDropEvent()
            event.temperature_control.temperatures[:] = self.temperatures
            duty_cycles = []
            for i in range(len(self.temperatures)):
                duty_cycles.append(self.duty_cycles.get(i, 0.0))
            event.temperature_control.duty_cycles[:] = duty_cycles
            self.__fire_event(event)

    def __fire_event(self, event):
        with self.lock:
            for listener in self.event_listeners:
                listener(event)

    def __get_parameter_definition(self, id):
        for p in self.parameter_list:
            if p['id'] == id:
                return p
        return None

    def register_event_listener(self, func):
        """Register a callback for state update events
        """
        with self.lock:
            self.event_listeners.append(func)

    def get_parameter_definitions(self):
        """Get a list of all of the parameters supported by the PurpleDrop

        Arguments:
          - None
        """
        logger.debug("Recieved get_parameter_definitions")
        return {
            "parameters": self.parameter_list,
        }

    def get_parameter(self, paramIdx):
        """Request the current value of a parameter from the device

        Arguments:
          - paramIdx: The ID of the parameter to request (from the list of
            parameters provided by 'get_parameter_definition')
        """
        req_msg = messages.SetParameterMsg()
        req_msg.set_param_idx(paramIdx)
        req_msg.set_param_value_int(0)
        req_msg.set_write_flag(0)
        def msg_filter(msg):
            return isinstance(msg, messages.SetParameterMsg) and msg.param_idx() == paramIdx
        listener = self.purpledrop.get_sync_listener(msg_filter=msg_filter)
        self.purpledrop.send_message(req_msg)
        resp = listener.wait(timeout=0.5)
        if resp is None:
            raise TimeoutError("No response from purpledrop")
        else:
            paramDesc = self.__get_parameter_definition(paramIdx)
            value = None
            if paramDesc is not None and paramDesc['type'] == 'float':
                value = resp.param_value_float()
            else:
                value = resp.param_value_int()
            logger.info(f"get_parameter({paramIdx}) returning {value}")
            return value

    def set_parameter(self, paramIdx, value):
        """Set a config parameter

        A special paramIdx value of 0xFFFFFFFF is used to trigger the saving
        of all parameters to flash.

        Arguments:
            - paramIdx: The index of the parameter to set (from
             'get_parameter_definitions')
            - value: A float or int (based on the definition) with the new
              value to assign
        """
        logging.debug(f"Received set_parameter({paramIdx}, {value})")
        req_msg = messages.SetParameterMsg()
        req_msg.set_param_idx(paramIdx)
        paramDesc = self.__get_parameter_definition(paramIdx)
        if paramDesc is not None and paramDesc['type'] == 'float':
            req_msg.set_param_value_float(value)
        else:
            req_msg.set_param_value_int(value)
        req_msg.set_write_flag(1)
        def msg_filter(msg):
            return isinstance(msg, messages.SetParameterMsg) and msg.param_idx() == paramIdx
        listener = self.purpledrop.get_sync_listener(msg_filter=msg_filter)
        self.purpledrop.send_message(req_msg)
        resp = listener.wait(timeout=0.5)
        if resp is None:
            raise TimeoutError(f"No response from purpledrop to set parameter ({paramIdx})")


    def get_board_definition(self):
        """Get electrode board configuratin object

        Arguments: None
        """
        logger.debug(f"Received get_board_definition")
        # TODO: This should be configurable
        return {
            "layout": {
                "grid": [
                    [None, None, None, None, None, None, 28, 98, None, None, None, None, None, None],
                    [None, None, None, None, None, None, 27, 99, None, None, None, None, None, None],
                    [11, 14, 16, 18, 20, 23, 26, 100, 102, 105, 109, 111, 113, 114],
                    [12, 13, 15, 17, 19, 22, 25, 101, 104, 107, 110, 112, 115, 116],
                    [5, 6, 7, 4, 3, 21, 24, 103, 108, 126, 125, 122, 123, 124],
                    [0, 63, 62, 1, 2, 55, 46, 68, 106, 127, 64, 67, 66, 65],
                    [60, 61, 54, 49, 51, 48, 44, 69, 82, 81, 79, 77, 76, 75],
                    [53, 50, 47, 45, 42, 41, 43, 87, 86, 85, 84, 83, 80, 78],
                    [None, None, None, None, None, None, 40, 88, None, None, None, None, None, None],
                    [None, None, None, None, None, None, 39, 89, None, None, None, None, None, None],
                    [None, None, None, None, None, None, 38, 90, None, None, None, None, None, None],
                ],
                "peripherals": [
                    {
                        "class": "reservoir",
                        "type": "reservoirB",
                        "id": 1,
                        "origin": (-0.5, 2.5),
                        "rotation": 180.0,
                        "electrodes": [
                            {
                                "id": "A",
                                "pin": 8,
                                "polygon": [(0, -0.5), (-0.8, -0.5), (-0.8, -2), (2.4, -2), (2.4, 2), (-0.8, 2), (-0.8, 0.5), (0, 0.5)],
                                "origin": (2.1, 0.00),
                            },
                            {
                                "id": "B",
                                "pin": 9,
                                "polygon": [(-0.8, -0.5), (0.8, -0.5), (0.8, 0.5), (-0.8, 0.5)],
                                "origin": (1.2, 0.0),
                            },
                            {
                                "id": "C",
                                "pin": 10,
                                "polygon": [(-0.5, -0.5), (0.5, -0.5), (0.5, 0.5), (-0.5, 0.5)],
                                "origin": (0.0, 0.0),
                            },
                        ],
                    },
                    {
                        "class": "reservoir",
                        "type": "reservoirA",
                        "id": 2,
                        "origin": (-0.5, 7.5),
                        "rotation": 180.0,
                        "exit": 53,
                        "electrodes": [
                            {
                                "id": "A",
                                "pin": 58,
                                "polygon": [(-0.5, -1.5), (3.5, -1.5), (3.5, 2.5), (-0.5, 2.5), (-0.5, 1), (0.5, 1), (0.5, 0), (-0.5, 0)],
                                "origin": (1.5, -0.5),
                            },
                            {
                                "id": "B",
                                "pin": 57,
                                "polygon": [(-0.5, -0.5), (1.0, -0.5), (1.0, 0.5), (-0.5, 0.5)],
                                "origin": (1.0, 0.0),
                            },
                            {
                                "id": "C",
                                "pin": 56,
                                "polygon": [(-0.5, -0.5), (0.5, -0.5), (0.5, 0.5), (-0.5, 0.5)],
                                "origin": (0.0, 0.0),
                            },
                            {
                                "id": "D",
                                "pin": 52,
                                "polygon": [(-0.5, -0.5), (0.5, -0.5), (0.5, 0.5), (-0.5, 0.5)],
                                "origin": (0.5, -1.0),
                            },
                            {
                                "id": "E",
                                "pin": 59,
                                "polygon": [(-0.5, -0.5), (0.5, -0.5), (0.5, 0.5), (-0.5, 0.5)],
                                "origin": (0.5, 1.0),
                            },
                        ],
                    },
                    {
                        "class": "reservoir",
                        "type": "reservoirA",
                        "id": 3,
                        "origin": (14.5, 7.5),
                        "exit": 78,
                        "electrodes": [
                            {
                                "id": "A",
                                "pin": 71,
                                "polygon": [(-0.5, -1.5), (3.5, -1.5), (3.5, 2.5), (-0.5, 2.5), (-0.5, 1), (0.5, 1), (0.5, 0), (-0.5, 0)],
                                "origin": (1.5, -0.5),
                            },
                            {
                                "id": "B",
                                "pin": 72,
                                "polygon": [(-0.5, -0.5), (1.0, -0.5), (1.0, 0.5), (-0.5, 0.5)],
                                "origin": (1.0, 0.0),
                            },
                            {
                                "id": "C",
                                "pin": 73,
                                "polygon": [(-0.5, -0.5), (0.5, -0.5), (0.5, 0.5), (-0.5, 0.5)],
                                "origin": (0.0, 0.0),
                            },
                            {
                                "id": "D",
                                "pin": 70,
                                "polygon": [(-0.5, -0.5), (0.5, -0.5), (0.5, 0.5), (-0.5, 0.5)],
                                "origin": (0.5, -1.0),
                            },
                            {
                                "id": "E",
                                "pin": 74,
                                "polygon": [(-0.5, -0.5), (0.5, -0.5), (0.5, 0.5), (-0.5, 0.5)],
                                "origin": (0.5, 1.0),
                            },
                        ],
                    },
                    {
                        "class": "reservoir",
                        "type": "reservoirA",
                        "id": 4,
                        "origin": (14.5, 2.5),
                        "exit": 114,
                        "electrodes": [
                            {
                                "id": "A",
                                "pin": 120,
                                "polygon": [(-0.5, -1.5), (3.5, -1.5), (3.5, 2.5), (-0.5, 2.5), (-0.5, 1), (0.5, 1), (0.5, 0), (-0.5, 0)],
                                "origin": (1.5, -0.5),
                            },
                            {
                                "id": "B",
                                "pin": 119,
                                "polygon": [(-0.5, -0.5), (1.0, -0.5), (1.0, 0.5), (-0.5, 0.5)],
                                "origin": (1.0, 0.0),
                            },
                            {
                                "id": "C",
                                "pin": 118,
                                "polygon": [(-0.5, -0.5), (0.5, -0.5), (0.5, 0.5), (-0.5, 0.5)],
                                "origin": (0.0, 0.0),
                            },
                            {
                                "id": "D",
                                "pin": 117,
                                "polygon": [(-0.5, -0.5), (0.5, -0.5), (0.5, 0.5), (-0.5, 0.5)],
                                "origin": (0.5, -1.0),
                            },
                            {
                                "id": "E",
                                "pin": 121,
                                "polygon": [(-0.5, -0.5), (0.5, -0.5), (0.5, 0.5), (-0.5, 0.5)],
                                "origin": (0.5, 1.0),
                            },
                        ],
                    },

                ]
            }
        }

    def get_bulk_capacitance(self) -> List[float]:
        """Get the most recent capacitance scan results

        Arguments: None
        """
        logging.debug("Received get_bulk_capacitance")
        return self.bulk_capacitance

    def get_active_capacitance(self) -> float:
        """Get the most recent active electrode capacitance

        Arguments: None
        """
        logging.debug("Received get_active_capacitance")
        return self.active_capacitance

    def get_electrode_pins(self):
        """Get the current state of all electrodes

        Arguments: None

        Returns: List of booleans
        """
        logging.debug("Received get_electrode_pins")
        return self.pin_state

    def set_electrode_pins(self, pins: Sequence[int]):
        """Set the currently enabled pins

        Specified electrodes will be activated, all other will be deactivated.
        Providing an empty array will deactivate all electrodes.

        Arguments:
            - pins: A list of pin numbers to activate
        """
        logging.debug(f"Received set_electrode_pins({pins})")
        msg = ElectrodeEnableMsg()
        event = messages_pb2.PurpleDropEvent()
        self.pin_state = [False] * 128

        for p in pins:
            word = int(p / 8)
            bit = p % 8
            msg.values[word] |= (1<<bit)
            self.pin_state[p] = True

        event.electrode_state.electrodes[:] = self.pin_state
        self.purpledrop.send_message(msg)
        self.__fire_event(event)

    def move_drop(self,
                  start: Sequence[int],
                  size: Sequence[int],
                  direction: str) -> MoveDropResult:
        """Execute a drop move sequence

        Arguments:
            - start: A list -- [x, y] -- specifying the top-left corner of the current drop location
            - size: A list -- [width, height] -- specifying the size of the drop to be moved
            - direction: One of, "Up", "Down", "Left", "Right"
        """
        logging.debug(f"Received move_drop({start}, {size}, {direction})")
        return move_drop(self, start, size, direction)

    def get_temperatures(self) -> Sequence[float]:
        """Returns an array of all temperature sensor measurements in degrees C

        Arguments: None
        """
        logging.debug("Received get_temperatures")
        return self.temperatures

    def set_pwm_duty_cycle(self, chan: int, duty_cycle: float):
        """Set the PWM output duty cycle for a single channel

        Arguments:
            - chan: An integer specifying the channel to set
            - duty_cycle: A float specifying the duty cycle in range [0, 1.0]
        """
        logging.debug(f"Received set_pwm_duty_cycle({chan}, {duty_cycle})")
        self.duty_cycles[chan] = duty_cycle
        msg = SetPwmMsg()
        msg.chan = chan
        msg.duty_cycle = duty_cycle
        self.purpledrop.send_message(msg)

    def get_hv_supply_voltage(self):
        """Return the latest high voltage rail measurement

        Arguments: None

        Returns: A float, in volts
        """
        logging.debug("Received get_hv_supply_voltage")
        return self.hv_supply_voltage
