"""Low-level driver for communicating with PurpleDrop via serial messages
"""
import inspect
import queue
import serial
import serial.tools.list_ports
import sys
import threading
from typing import AnyStr, Callable, List, Optional, Sequence

import purpledrop.messages as messages
import purpledrop.protobuf.messages_pb2 as messages_pb2
from .messages import PurpleDropMessage, ElectrodeEnableMsg, SetPwmMsg
from .message_framer import MessageFramer, serialize

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

    This should be configurable eventually. Or perhaps come from the device.
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
        #make_param(0, "Target Voltage", "High voltage regulator output in volts", "float"),
        make_param(10, "HV Control Enabled", "Enable feedback control", "bool"),
        make_param(11, "HV Voltage Setting", "High voltage regulator output in volts", "float"),
        make_param(12, "HV Target Out", "V target out when regulator is disabled (counts, 0-4096)"),
        make_param(20, "Scan Sync Pin", "Set timing of the capacitance scan sync to given electrode"),
        make_param(21, "Scan Start Delay", "ns, Settling time before first scan measurement"),
        make_param(22, "Scan Blank Delay", "ns, Settling time after each scan measurement"),
        make_param(23, "Sample Delay", "ns, Time between first and second integrator sample"),
        make_param(24, "Blanking Delay", "ns, Time between blank and integrator reset for active measure"),
        make_param(25, "Integrator Reset Delay", "ns, Time between reset release and first sample"),
    ]

class PurpleDropRxThread(object):
    def __init__(self, port: serial.Serial, callback: Callable[[PurpleDropMessage], None]=None):
        self._thread = threading.Thread(target=self.run, name="PurpleDrop Rx", daemon=True)
        self._ser = port
        self._framer = MessageFramer(PurpleDropMessage.predictSize)
        self._callback = callback

    def start(self):
        self._thread.start()

    def run(self):
        while True:
            rxBytes = None
            #try:
            rxBytes = self._ser.read(64)
            #except serial.serialutil.SerialException:
            #    continue # This happens intermittently, because select returns
                         # but then read returns no data. pyserial thinks this
                         # shouldn't be able to happen; I'm not so sure but it
                         # needs investigation
                         # See serial/serialposix.py:500

            if(len(rxBytes) > 0):
                for buf in self._framer.parse(rxBytes):
                    if(self._callback):
                        self._callback(PurpleDropMessage.from_bytes(buf))

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
    def __init__(self, port):
        self.port = port
        self._ser = serial.Serial(self.port, timeout=0.01, write_timeout=0.5)
        self._rx_thread = PurpleDropRxThread(self._ser, callback=self.message_callback)
        self._rx_thread.start()
        self.lock = threading.Lock()
        self.listeners = []

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
        print(f"Sending {tx_bytes} ")
        with self.lock:
            self._ser.write(tx_bytes)

    def message_callback(self, msg: PurpleDropMessage):
        with self.lock:
            for l in self.listeners:
                l.push_msg(msg)

class MoveDropResult(dict):
        def __init__(self, success=False, closed_loop=False, closed_loop_result=None):
            dict.__init__(self, success=success, closed_loop=closed_loop, closed_loop_result=closed_loop_result)

class MoveDropClosedLoopResult(object):
    def __init__(self,
                    pre_capacitance: float,
                    post_capacitance: float,
                    time_series: Sequence[float],
                    capacitance_series: Sequence[float]):
        self.pre_capacitance = pre_capacitance
        self.post_capacitance = post_capacitance
        self.time_series = time_series
        self.capacitance_series = capacitance_series

class PurpleDropController(object):
    def __init__(self, purpledrop):
        self.purpledrop = purpledrop
        self.active_capacitance = 0.0
        self.bulk_capacitance = []
        self.temperatures: Sequence[float] = []
        self.hv_supply_voltage = 0.0
        self.parameter_list = parameter_list()
        self.lock = threading.Lock()
        self.event_listeners = []
        self.active_capacitance_counter = 0

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
            if (self.active_capacitance_counter % 100) == 0:
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
            self.hv_supply_voltage = msg.voltage
            event = messages_pb2.PurpleDropEvent()
            event.hv_regulator.voltage = msg.voltage
            event.hv_regulator.v_target_out = msg.v_target_out
            self.__fire_event(event)

        elif isinstance(msg, messages.TemperatureMsg):
            self.temperatures = [float(x) / 100.0 for x in msg.measurements]

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
        with self.lock:
            self.event_listeners.append(func)

    def get_parameter_definitions(self):
        """Get a list of all of the parameters supported by the PurpleDrop
        """
        return {
            "parameters": self.parameter_list,
        }

    def get_parameter(self, paramIdx):
        print(f"Requesting param {paramIdx}")
        req_msg = messages.SetParameterMsg()
        req_msg.set_param_idx(paramIdx)
        req_msg.set_param_value_int(0)
        req_msg.set_write_flag(0)
        def msg_filter(msg):
            return isinstance(msg, messages.SetParameterMsg) and msg.param_idx() == paramIdx
        listener = self.purpledrop.get_sync_listener(msg_filter=msg_filter)
        self.purpledrop.send_message(req_msg)
        resp = listener.wait(timeout=0.5)
        print (resp)
        if resp is None:
            raise TimeoutError("No response from purpledrop")
        else:
            paramDesc = self.__get_parameter_definition(paramIdx)
            if paramDesc is not None and paramDesc['type'] == 'float':
                print(f"Param value: {resp.param_value_float()}")
                return resp.param_value_float()
            else:
                print(f"Param value: {resp.param_value_int()}")
                return resp.param_value_int()

    def set_parameter(self, paramIdx, value):
        req_msg = messages.SetParameterMsg()
        req_msg.set_param_idx(paramIdx)
        paramDesc = self.__get_parameter_definition(paramIdx)
        if paramDesc is not None and paramDesc['type'] == 'float':
            req_msg.set_param_value_float(value)
        else:
            req_msg.set_param_value_int(value)
        req_msg.set_write_flag(1)
        self.purpledrop.send_message(req_msg)

    def get_board_definition(self):
        """Get electrode board configuratin object

        Arguments: None
        """
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
                "extra": [
                    {
                        "class": "reservoirB",
                        "id": 1,
                        "origin": (-0.5, 2.5),
                        "rotation": 180.0,
                        "electrodes": [
                            {
                                "pin_class": "A",
                                "pin": 8,
                                "polygon": [(0, -0.5), (-0.8, -0.5), (-0.8, -2), (2.4, -2), (2.4, 2), (-0.8, 2), (-0.8, 0.5), (0, 0.5)],
                                "origin": (2.1, 0.00),
                            },
                            {
                                "pin_class": "B",
                                "pin": 9,
                                "polygon": [(-0.8, -0.5), (0.8, -0.5), (0.8, 0.5), (-0.8, 0.5)],
                                "origin": (1.2, 0.0),
                            },
                            {
                                "pin_class": "C",
                                "pin": 10,
                                "polygon": [(-0.5, -0.5), (0.5, -0.5), (0.5, 0.5), (-0.5, 0.5)],
                                "origin": (0.0, 0.0),
                            },
                        ],
                    },
                    {
                        "class": "reservoirA",
                        "id": 2,
                        "origin": (-0.5, 7.5),
                        "rotation": 180.0,
                        "electrodes": [
                            {
                                "pin_class": "A",
                                "pin": 58,
                                "polygon": [(-0.5, -1.5), (3.5, -1.5), (3.5, 2.5), (-0.5, 2.5), (-0.5, 1), (0.5, 1), (0.5, 0), (-0.5, 0)],
                                "origin": (1.5, -0.5),
                            },
                            {
                                "pin_class": "B",
                                "pin": 57,
                                "polygon": [(-0.5, -0.5), (1.0, -0.5), (1.0, 0.5), (-0.5, 0.5)],
                                "origin": (1.0, 0.0),
                            },
                            {
                                "pin_class": "C",
                                "pin": 56,
                                "polygon": [(-0.5, -0.5), (0.5, -0.5), (0.5, 0.5), (-0.5, 0.5)],
                                "origin": (0.0, 0.0),
                            },
                            {
                                "pin_class": "C",
                                "pin": 52,
                                "polygon": [(-0.5, -0.5), (0.5, -0.5), (0.5, 0.5), (-0.5, 0.5)],
                                "origin": (0.5, -1.0),
                            },
                            {
                                "pin_class": "C",
                                "pin": 59,
                                "polygon": [(-0.5, -0.5), (0.5, -0.5), (0.5, 0.5), (-0.5, 0.5)],
                                "origin": (0.5, 1.0),
                            },
                        ],
                    },
                    {
                        "class": "reservoirA",
                        "id": 3,
                        "origin": (14.5, 7.5),
                        "electrodes": [
                            {
                                "pin_class": "A",
                                "pin": 120,
                                "polygon": [(-0.5, -1.5), (3.5, -1.5), (3.5, 2.5), (-0.5, 2.5), (-0.5, 1), (0.5, 1), (0.5, 0), (-0.5, 0)],
                                "origin": (1.5, -0.5),
                            },
                            {
                                "pin_class": "B",
                                "pin": 119,
                                "polygon": [(-0.5, -0.5), (1.0, -0.5), (1.0, 0.5), (-0.5, 0.5)],
                                "origin": (1.0, 0.0),
                            },
                            {
                                "pin_class": "C",
                                "pin": 118,
                                "polygon": [(-0.5, -0.5), (0.5, -0.5), (0.5, 0.5), (-0.5, 0.5)],
                                "origin": (0.0, 0.0),
                            },
                            {
                                "pin_class": "C",
                                "pin": 117,
                                "polygon": [(-0.5, -0.5), (0.5, -0.5), (0.5, 0.5), (-0.5, 0.5)],
                                "origin": (0.5, -1.0),
                            },
                            {
                                "pin_class": "C",
                                "pin": 121,
                                "polygon": [(-0.5, -0.5), (0.5, -0.5), (0.5, 0.5), (-0.5, 0.5)],
                                "origin": (0.5, 1.0),
                            },
                        ],
                    },
                    {
                        "class": "reservoirA",
                        "id": 4,
                        "origin": (14.5, 2.5),
                        "electrodes": [
                            {
                                "pin_class": "A",
                                "pin": 71,
                                "polygon": [(-0.5, -1.5), (3.5, -1.5), (3.5, 2.5), (-0.5, 2.5), (-0.5, 1), (0.5, 1), (0.5, 0), (-0.5, 0)],
                                "origin": (1.5, -0.5),
                            },
                            {
                                "pin_class": "B",
                                "pin": 72,
                                "polygon": [(-0.5, -0.5), (1.0, -0.5), (1.0, 0.5), (-0.5, 0.5)],
                                "origin": (1.0, 0.0),
                            },
                            {
                                "pin_class": "C",
                                "pin": 73,
                                "polygon": [(-0.5, -0.5), (0.5, -0.5), (0.5, 0.5), (-0.5, 0.5)],
                                "origin": (0.0, 0.0),
                            },
                            {
                                "pin_class": "C",
                                "pin": 70,
                                "polygon": [(-0.5, -0.5), (0.5, -0.5), (0.5, 0.5), (-0.5, 0.5)],
                                "origin": (0.5, -1.0),
                            },
                            {
                                "pin_class": "C",
                                "pin": 74,
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
        return self.bulk_capacitance

    def get_active_capacitance(self) -> float:
        """Get the most recent active electrode capacitance

        Arguments: None
        """
        return self.active_capacitance

    def set_electrode_pins(self, pins: Sequence[int]):
        """Set the currently enabled pins

        Specified electrodes will be activated, all other will be deactivated.
        Providing an empty array will deactivate all electrodes.

        Arguments:
            - pins: A list of pin numbers
        """

        msg = ElectrodeEnableMsg()
        event = messages_pb2.PurpleDropEvent()
        event.electrode_state.electrodes[:] = [False] * 128
        for p in pins:
            word = int(p / 8)
            bit = p % 8
            msg.values[word] |= (1<<bit)
            event.electrode_state.electrodes[p] = True
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
        return MoveDropResult()

    def get_temperatures(self) -> Sequence[float]:
        """Returns an array with all temperature sensor measurements in degrees C
        """
        return self.temperatures

    def set_pwm_duty_cycle(self, chan: int, duty_cycle: float):
        """Set the PWM output duty cycle for a single channel

        Arguments:
            - chan: An integer specifying the channel to set
            - duty_cycle: Float specifying the duty cycle in range [0, 1.0]
        """
        msg = SetPwmMsg()
        msg.chan = chan
        msg.duty_cycle = duty_cycle
        self.purpledrop.send_message(msg)

    def get_hv_supply_voltage(self):
        return self.hv_supply_voltage

class PurpleDropRpc(object):
    """Wrapper to define the RPC methods for remote control of purpledrop

    TODO: This is pretty verbose. Maybe a decorator to mark methods on
    PurpleDropController for inclusion? Or just a list of method names.
    """
    def __init__(self, purple_drop_controller):
        self.pdc = purple_drop_controller

    def get_board_definition(self):
        return self.pdc.get_board_definition()

    def get_parameter_definitions(self):
        return self.pdc.get_parameter_definitions()

    def get_parameter(self, id):
        return self.pdc.get_parameter(id)

    def set_parameter(self, id, value):
        return self.pdc.set_parameter(id, value)

    def get_bulk_capacitance(self) -> List[float]:
        """Get the most recent capacitance scan results

        Arguments: None
        """
        return self.pdc.get_bulk_capacitance()

    def get_active_capacitance(self) -> float:
        """Get the most recent active electrode capacitance

        Arguments: None
        """
        return self.pdc.get_active_capacitance()

    def set_electrode_pins(self, pins: Sequence[int]):
        """Set the currently enabled pins

        Specified electrodes will be activated, all other will be deactivated.
        Providing an empty array will deactivate all electrodes.

        Arguments:
            - pins: A list of pin numbers
        """
        return self.pdc.set_electrode_pins(pins)

    def get_electrode_pins(self) -> Sequence[bool]:
        """Get the state of all pins
        """
        return [False] * 128

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
        return self.pdc.move_drop(start, size, direction)

    def get_temperatures(self) -> Sequence[float]:
        """Returns an array with all temperature sensor measurements in degrees C
        """
        return self.pdc.get_temperatures()

    def set_pwm_duty_cycle(self, chan: int, duty_cycle: float):
        """Set the PWM output duty cycle for a single channel

        Arguments:
            - chan: An integer specifying the channel to set
            - duty_cycle: Float specifying the duty cycle in range [0, 1.0]
        """
        return self.pdc.set_pwm_duty_cycle(chan, duty_cycle)

    def get_hv_supply_voltage(self) -> float:
        return self.pdc.get_hv_supply_voltage()