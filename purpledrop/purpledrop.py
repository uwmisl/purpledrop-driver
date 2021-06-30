"""Low-level driver for communicating with PurpleDrop via serial messages
"""
import inspect
import fnmatch
import logging
import queue
import struct
import serial
import serial.tools.list_ports
import sys
import threading
import time
from typing import Any, AnyStr, Callable, Dict, List, Optional, Sequence

from purpledrop.calibration import ElectrodeOffsetCalibration
from purpledrop.electrode_board import Board
import purpledrop.messages as messages
import purpledrop.protobuf.messages_pb2 as messages_pb2
from .messages import PurpleDropMessage, ElectrodeEnableMsg, SetPwmMsg
from .message_framer import MessageFramer, serialize
from .move_drop import move_drop, MoveDropResult

logger = logging.getLogger("purpledrop")

# Versions of purpledrop software supported by this driver
SUPPORTED_VERSIONS = [
    "v0.5.*",
]

# List of USB VID/PID pairs which will be recognized as a purpledrop
PURPLEDROP_VIDPIDS = [
    (0x02dd, 0x7da3),
    (0x1209, 0xCCAA),
]

def pinlist2bool(pins):
    pin_state = [False] * N_PINS

    for p in pins:
        if(p >= N_PINS):
            raise ValueError(f"Pin {p} is invalid. Must be < {N_PINS}")
        pin_state[p] = True
    return pin_state

def pinlist2mask(pins):
    mask = [0] * int(((N_PINS + 7) / 8))
    for p in pins:
        word = int(p / 8)
        bit = p % 8
        mask[word] |= (1<<bit)
    return mask

def validate_version(v):
    for pattern in SUPPORTED_VERSIONS:
        if fnmatch.fnmatch(v, pattern):
            return True
    return False

def resolve_msg_filter(filt):
    """If the filter provided is a message type, then create a filter which returns
    any message of that type. Otherwise, assume the filter is a lambda method.
    """
    if inspect.isclass(filt): # and issubclass(filt, PurpleDropMessage):
        return lambda x: isinstance(x, filt)
    else:
        return filt

def list_purpledrop_devices() -> List[serial.tools.list_ports_common.ListPortInfo]:
    """Get a list of detected purpledrop devices

    Returns:
        A list of `ListPortInfo` objects
    """
    devices = serial.tools.list_ports.comports()
    selected_devices = [x for x in devices if (x.vid, x.pid) in PURPLEDROP_VIDPIDS]
    return selected_devices

def get_pb_timestamp():
    """Get a protobuf timestamp for the current system time
    """
    time_f = time.time()
    ts = messages_pb2.Timestamp()
    ts.seconds = int(time_f)
    ts.nanos = int((time_f % 1) * 1e9)
    return ts
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
                            logger.exception(e)


    def set_callback(self, callback):
        self._callback = callback

class SyncListener(object):
    class MsgDelegate(object):
        def __init__(self, filter_func, fifo):
            self.filter = filter_func
            self.fifo = fifo

        def __call__(self, msg: PurpleDropMessage):
            if self.filter is None or self.filter(msg):
                self.fifo.put(msg)

    def __init__(self, owner, msg_filter=None):
        self.owner = owner
        self.filter = resolve_msg_filter(msg_filter)
        self.fifo = queue.Queue()
        self.delegate = self.MsgDelegate(self.filter, self.fifo)

    def __del__(self):
        self.unregister()

    def unregister(self):
        self.owner.unregister_listener(self.delegate)

    def get_msg_handler(self):
        return self.delegate

    def wait(self, timeout: Optional[float]=None) -> Optional[PurpleDropMessage]:
        try:
            return self.fifo.get(timeout=timeout)
        except queue.Empty:
            return None

class AsyncListener(object):
    class MsgDelegate(object):
        def __init__(self, filter_func, callback):
            self.filter = filter_func
            self.callback = callback

        def __call__(self, msg: PurpleDropMessage):
            if self.filter is None or self.filter(msg):
                self.callback(msg)


    def __init__(self, owner, callback, msg_filter=None):
        self.owner = owner
        self.callback = callback
        self.filter = resolve_msg_filter(msg_filter)
        self.delegate = self.MsgDelegate(self.filter, callback)

    def __del__(self):
        self.owner.unregister_listener(self.delegate)

    def get_msg_handler(self):
        return self.delegate

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
        self.__connected_callbacks: List[Callable] = []
        self.__disconnected_callbacks: List[Callable] = []

        if port is not None:
            self.open(port)

    def register_connected_callback(self, callback: Callable):
        self.__connected_callbacks.append(callback)

    def register_disconnected_callback(self, callback: Callable):
        self.__disconnected_callbacks.append(callback)

    def open(self, port):
        logger.debug(f"PurpleDropDevice: opening {port}")
        self._ser = serial.Serial(port, timeout=0.01, write_timeout=0.5)
        self._rx_thread = PurpleDropRxThread(self._ser, callback=self.message_callback)
        self._rx_thread.start()
        for cb in self.__connected_callbacks:
            cb()

    def close(self):
        logger.debug("Closing PurpleDropDevice")
        if self._rx_thread is not None:
            self._rx_thread.stop()
            self._rx_thread.join()
        if self._ser is not None:
            self._ser.close()
            for cb in self.__disconnected_callbacks:
                cb()

    def connected(self):
        return self._ser is not None and \
            self._rx_thread is not None and \
            self._rx_thread.running

    def unregister_listener(self, listener):
        with self.lock:
            self.listeners.remove(listener)

    def get_sync_listener(self, msg_filter=None) -> SyncListener:
        new_listener = SyncListener(owner=self, msg_filter=msg_filter)
        with self.lock:
            self.listeners.append(new_listener.get_msg_handler())
        return new_listener

    def get_async_listener(self, callback, msg_filter=None) -> AsyncListener:
        new_listener = AsyncListener(owner=self, callback=callback, msg_filter=msg_filter)
        with self.lock:
            self.listeners.append(new_listener.get_msg_handler())
        return new_listener

    def send_message(self, msg: PurpleDropMessage):
        tx_bytes = serialize(msg.to_bytes())
        with self.lock:
            self._ser.write(tx_bytes)

    def message_callback(self, msg: PurpleDropMessage):
        with self.lock:
            for handler in self.listeners:
                handler(msg)

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
        self.device_info: Optional[Any] = None
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

        self.device_info = selected_device
        self.open(selected_device.device)
        logger.warning(f"Connected to purpledrop {selected_device.serial_number} on {selected_device.device}")
        return True

    def __thread_entry(self):
        status = False
        while True:
            if not self.connected():
                if status:
                    logger.warning("Closing purpledrop device")
                    self.close()
                    self.device_info = None
                    status = False
                logger.debug("Attempting to connect to purpledrop")
                status = self.__try_to_connect()
            time.sleep(5.0)

N_PINS = 128
N_MASK_BYTES = 16

# Compute coefficients to convert integrated voltage to integrated charge
# These values are nominal calculated values, not calibrated in any way
# Divide by the voltage to get farads. 
# First stage gain
GAIN1 = 2.0
# Integrator gain (Vout per integrated input V*s)
GAIN2 = 25000.0
# Output stage gain
GAIN3 = 22.36
# Sense resistances for high/low gain
RLOW = 33.0
RHIGH = 220.0
CAPGAIN_HIGH = RHIGH * GAIN1 * GAIN2 * GAIN3 * 4096. / 3.3
CAPGAIN_LOW = RLOW * GAIN1 * GAIN2 * GAIN3 * 4096. / 3.3

class PinState(object):
    """Data record to store the state of purpledrop pin setting, including 
    active pins and capacitance scan groups
    """
    N_DRIVE_GROUPS = 2
    N_SCAN_GROUPS = 5

    class PinGroup(object):
        def __init__(self, pin_mask: Sequence[int], setting: int):
            self.pin_mask = pin_mask
            self.setting = setting

    class DriveGroup(PinGroup):
        def __init__(self, pin_mask=None, duty_cycle=255):
            if pin_mask is None:
                pin_mask = pinlist2bool([])
            super().__init__(pin_mask, duty_cycle)

        @property
        def duty_cycle(self):
            return self.setting

        @duty_cycle.setter
        def duty_cycle(self, dc):
            self.setting = dc

        def to_dict(self):
            return {
                'pins': self.pin_mask,
                'duty_cycle': self.duty_cycle,
            }

    class ScanGroup(PinGroup):
        def __init__(self, pin_mask=None, setting=0):
            if pin_mask is None:
                pin_mask = pinlist2bool([])
            super().__init__(pin_mask, setting)

        def to_dict(self):
            return {
                'pins': self.pin_mask,
                'setting': self.setting,
            }

    def __init__(self):
        self.drive_groups = [self.DriveGroup() for _ in range(self.N_DRIVE_GROUPS)]
        self.scan_groups = [self.ScanGroup() for _ in range(self.N_SCAN_GROUPS)]

    def to_dict(self):
        return {
            'drive_groups': [x.to_dict() for x in self.drive_groups],
            'scan_groups': [x.to_dict() for x in self.scan_groups],
        }

class PurpleDropController(object):
    # Define the method names which will be made available via RPC server
    RPC_METHODS = [
        'get_board_definition',
        'get_parameter_definitions',
        'get_parameter',
        'set_parameter',
        'get_bulk_capacitance',
        'get_scan_capacitance',
        'get_group_capacitance',
        'get_active_capacitance',
        'set_capacitance_group',
        'set_electrode_pins',
        'get_electrode_pins',
        'set_feedback_command',
        'move_drop',
        'get_temperatures',
        'set_pwm_duty_cycle',
        'get_hv_supply_voltage',
        'calibrate_capacitance_offset',
        'get_device_info',
        'read_gpio',
        'write_gpio',
        'set_scan_gains',
        'get_scan_gains',
        'set_electrode_calibration',
    ]

    def __init__(self, purpledrop, board_definition: Board, electrode_calibration: Optional[ElectrodeOffsetCalibration]=None):
        self.purpledrop = purpledrop
        self.board_definition = board_definition

        self.active_capacitance = 0.0
        self.electrode_calibration = electrode_calibration
        self.raw_scan_capacitance: List[float] = []
        self.calibrated_scan_capacitance: List[float] = []
        self.raw_group_capacitance: List[float] = []
        self.calibrated_group_capacitance: List[float] = []
        self.scan_gains = [1.0] * N_PINS
        self.temperatures: Sequence[float] = []
        self.duty_cycles: Dict[int, float] = {}
        self.hv_supply_voltage = 0.0
        self.parameter_list: List[dict] = []
        self.lock = threading.Lock()
        self.event_listeners: List[Callable] = []
        self.active_capacitance_counter = 0
        self.group_capacitance_counter = 0
        self.duty_cycle_updated_counter = 0
        self.hv_regulator_counter = 0
        self.pin_state = PinState()

        def msg_filter(msg):
            desired_types = [
                messages.ActiveCapacitanceMsg,
                messages.BulkCapacitanceMsg,
                messages.CommandAckMsg,
                messages.DutyCycleUpdatedMsg,
                messages.TemperatureMsg,
                messages.HvRegulatorMsg,
            ]

            for t in desired_types:
                if isinstance(msg, t):
                    return True
            return False
        
        if self.purpledrop.connected():
            self.__on_connected()
        self.purpledrop.register_connected_callback(self.__on_connected)
        self.purpledrop.register_disconnected_callback(self.__on_disconnected)

        self.listener = self.purpledrop.get_async_listener(self.__message_callback, msg_filter)

    def __on_connected(self):
        self.__set_scan_gains()
        self.__get_parameter_descriptors()
        software_version = self.get_software_version()
        if not validate_version(software_version):
            logger.error(f"Unsupported software version '{software_version}'. This driver may not" + \
                "work correcly, and you should upgrade your purpledrop firmware to one of the following: " +  \
                    f"{SUPPORTED_VERSIONS}")
        self.__send_device_info_event(
            True, 
            self.purpledrop.connected_serial_number() or '',
            software_version or ''
        )
        if self.electrode_calibration is not None:
            logger.info("Loading electrode calibration")
            self.set_electrode_calibration(self.electrode_calibration.voltage, self.electrode_calibration.offsets)

    def __on_disconnected(self):
        self.__send_device_info_event(False, '', '')

    def __send_device_info_event(self, connected: bool, serial_number: str, software_version: str):
        event = messages_pb2.PurpleDropEvent()
        event.device_info.connected = connected
        event.device_info.serial_number = serial_number
        event.device_info.software_version = software_version
        self.__fire_event(event)

    def __get_parameter_descriptors(self):
        """Request and receive the list of parameters from device 
        """
        listener = self.purpledrop.get_sync_listener(messages.ParameterDescriptorMsg)
        self.purpledrop.send_message(messages.ParameterDescriptorMsg())
        descriptors = []
        while True:
            msg = listener.wait(timeout=1.0)
            if msg is None:
                logger.error("Timed out waiting for parameter descriptors")
                break
            descriptors.append({
                'id': msg.param_id,
                'name': msg.name,
                'description': msg.description,
                'type': msg.type,
            })
            if msg.sequence_number == msg.sequence_total - 1:
                break
        self.parameter_list = descriptors

    def __set_scan_gains(self, gains: Sequence[bool]=None):
        """Setup gains used for capacitance scan

        If no gains are provided, the gains will be set based on the "oversized"
        electrodes defined in the active board definition. Any oversized
        electrodes are set to low gain, and the rest to high gain.

        Args:
          gains: A list of booleans. True indicates low gain should be used for
          the corresponding electrode
        """
        if gains is None:
            gains = [False] * N_PINS
            for pin in self.board_definition.oversized_electrodes:
                gains[pin] = True # low gain
        self.scan_gains = list(map(lambda x: CAPGAIN_LOW if x else CAPGAIN_HIGH, gains))

        msg = messages.SetGainMsg()
        msg.gains = list(map(lambda x: 1 if x else 0, gains))
        listener = self.purpledrop.get_sync_listener(messages.CommandAckMsg)
        self.purpledrop.send_message(msg)
        ack = listener.wait(timeout=1.0)
        if ack is None:
            logger.error("Got no ACK for SetGains message")

    def __calibrate_capacitance(self, raw, gain):
        # Can't measure capacitance unless high voltage is on
        if self.hv_supply_voltage < 60.0:
            return 0.0
        # Return as pF
        return raw * 1e12 / gain / self.hv_supply_voltage
        
    def __message_callback(self, msg):
        if isinstance(msg, messages.ActiveCapacitanceMsg):
            # TODO: I-sense resistor values are adjustable, and the
            # CAPGAIN_HIGH/CAPGAIN_LOW should be gotten from the device at some
            # point, rather than duplicated here
            capgain = CAPGAIN_LOW if (msg.settings & 1 == 1) else CAPGAIN_HIGH
            self.active_capacitance = self.__calibrate_capacitance(msg.measurement - msg.baseline, capgain)
            self.active_capacitance_counter += 1
            # Throttle the events. 500Hz messages is a lot for the browser to process.
            # This also means logs don't have a full resolution, and it would be better
            # if clients could choose what they get
            if (self.active_capacitance_counter % 10) == 0:
                cap_event = messages_pb2.PurpleDropEvent()
                cap_event.active_capacitance.baseline = msg.baseline
                cap_event.active_capacitance.measurement = msg.measurement
                cap_event.active_capacitance.calibrated = float(self.active_capacitance)
                cap_event.active_capacitance.timestamp.CopyFrom(get_pb_timestamp())
                self.__fire_event(cap_event)

        elif isinstance(msg, messages.BulkCapacitanceMsg):
            if(msg.group_scan != 0):
                self.group_capacitance_counter += 1
                if (self.group_capacitance_counter % 10) == 0:
                    self.raw_group_capacitance = msg.measurements
                    self.calibrated_group_capacitance = [0.0] * len(self.raw_group_capacitance)
                    for i in range(msg.count):
                        if self.pin_state.scan_groups[i].setting == 0:
                            gain = CAPGAIN_HIGH
                        else:
                            gain = CAPGAIN_LOW
                        self.calibrated_group_capacitance[i] = self.__calibrate_capacitance(msg.measurements[i], gain)
                    group_event = messages_pb2.PurpleDropEvent()
                    group_event.group_capacitance.timestamp.CopyFrom(get_pb_timestamp())
                    group_event.group_capacitance.measurements[:] = self.calibrated_group_capacitance
                    group_event.group_capacitance.raw_measurements[:] = self.raw_group_capacitance
                    self.__fire_event(group_event)
            else:
                # Scan capacitance measurements are broken up into multiple messages
                if len(self.raw_scan_capacitance) < msg.start_index + msg.count:
                    self.raw_scan_capacitance.extend([0] * (msg.start_index + msg.count - len(self.raw_scan_capacitance)))
                    self.calibrated_scan_capacitance.extend([0] * (msg.start_index + msg.count - len(self.calibrated_scan_capacitance)))
                for i in range(msg.count):
                    chan = msg.start_index + i
                    gain = self.scan_gains[chan]
                    self.raw_scan_capacitance[chan] = msg.measurements[i]
                    self.calibrated_scan_capacitance[chan] = self.__calibrate_capacitance(msg.measurements[i], gain)
                # Fire event on the last group
                if msg.start_index + msg.count == 128:
                    bulk_event = messages_pb2.PurpleDropEvent()
                    def make_cap_measurement(raw, calibrated):
                        m = messages_pb2.CapacitanceMeasurement()
                        m.raw = float(raw)
                        m.capacitance = float(calibrated)
                        return m
                    bulk_event.scan_capacitance.measurements.extend(
                        [make_cap_measurement(raw, cal)
                        for (raw, cal) in zip(self.raw_scan_capacitance, self.calibrated_scan_capacitance)]
                    )
                    bulk_event.scan_capacitance.timestamp.CopyFrom(get_pb_timestamp())
                    self.__fire_event(bulk_event)

        elif isinstance(msg, messages.DutyCycleUpdatedMsg):
            self.duty_cycle_updated_counter += 1
            if (self.duty_cycle_updated_counter%10) == 0:
                # Update local state of duty cycle
                self.pin_state.drive_groups[0].duty_cycle = msg.duty_cycle_A
                self.pin_state.drive_groups[1].duty_cycle = msg.duty_cycle_B

                # Publish event with new values
                duty_cycle_event = messages_pb2.PurpleDropEvent()
                duty_cycle_event.duty_cycle_updated.timestamp.CopyFrom(get_pb_timestamp())
                duty_cycle_event.duty_cycle_updated.duty_cycles[:] = [msg.duty_cycle_A, msg.duty_cycle_B]
                self.__fire_event(duty_cycle_event)

        elif isinstance(msg, messages.HvRegulatorMsg):
            self.hv_regulator_counter += 1
            if (self.hv_regulator_counter % 10) == 0:
                self.hv_supply_voltage = msg.voltage
                event = messages_pb2.PurpleDropEvent()
                event.hv_regulator.voltage = msg.voltage
                event.hv_regulator.v_target_out = msg.v_target_out
                event.hv_regulator.timestamp.CopyFrom(get_pb_timestamp())
                self.__fire_event(event)

        elif isinstance(msg, messages.TemperatureMsg):
            self.temperatures = [float(x) / 100.0 for x in msg.measurements]
            event = messages_pb2.PurpleDropEvent()
            event.temperature_control.temperatures[:] = self.temperatures
            duty_cycles = []
            for i in range(len(self.temperatures)):
                duty_cycles.append(self.duty_cycles.get(i, 0.0))
            event.temperature_control.duty_cycles[:] = duty_cycles
            event.temperature_control.timestamp.CopyFrom(get_pb_timestamp())
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

    def __fire_pinstate_event(self):
        def create_electrode_group(x):
            eg = messages_pb2.ElectrodeGroup()
            eg.electrodes[:] = x.pin_mask
            eg.setting = x.setting
            return eg
        event = messages_pb2.PurpleDropEvent()
        for g in self.pin_state.drive_groups:
            event.electrode_state.drive_groups.add(electrodes=g.pin_mask, setting=g.setting)
        for g in self.pin_state.scan_groups:
            event.electrode_state.scan_groups.add(electrodes=g.pin_mask, setting=g.setting)

        self.__fire_event(event)

    def get_software_version(self) -> Optional[str]:
        listener = self.purpledrop.get_sync_listener(msg_filter=messages.DataBlobMsg)
        versionRequest = messages.DataBlobMsg()
        versionRequest.blob_id = messages.DataBlobMsg.SOFTWARE_VERSION_ID
        self.purpledrop.send_message(versionRequest)
        msg = listener.wait(0.5)
        if msg is None:
            software_version = None
            logger.warning("Timed out requesting software version")
        else:
            software_version = msg.payload.decode('utf-8')
        return software_version

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
            logger.debug(f"get_parameter({paramIdx}) returning {value}")
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
        return self.board_definition.as_dict()

    def get_bulk_capacitance(self) -> List[float]:
        """Get the most recent capacitance scan results

        DEPRECATED. Use get_scan_capacitance.

        Arguments: None
        """
        logging.debug("Received get_bulk_capacitance")
        return self.calibrated_scan_capacitance

    def get_scan_capacitance(self) -> Dict[str, Any]:
        """Get the most recent capacitance scan results

        Arguments: None
        """
        return {
            "raw": self.raw_scan_capacitance,
            "calibrated": self.calibrated_scan_capacitance
        }

    def get_group_capacitance(self) -> Dict[str, List[float]]:
        """Get the latest group scan capacitances

        Arguments: None
        """
        return {
            "raw": self.raw_group_capacitance,
            "calibrated": self.calibrated_group_capacitance,
        }

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
        return self.pin_state.to_dict()

    def set_capacitance_group(self, pins: Sequence[int], group_id: int, setting: int):
        """Set a capacitance scan group.

        Purpledrop support 5 scan groups. Each group defines a set of electrodes
        which are measured together after each AC drive cycle.

        Arguments:
          - pins: A list of pins included in the group (may be empty to clear the group)
          - group_id: The group number to set (0-4)
        """
        if group_id >= 5:
            raise ValueError("group_id must be < 5")

        # Send message to device to update
        msg = ElectrodeEnableMsg()
        msg.group_id = group_id + 100
        msg.setting = setting
        msg.values = pinlist2mask(pins)
        self.purpledrop.send_message(msg)

        # Update local state
        self.pin_state.scan_groups[group_id] = PinState.ScanGroup(pinlist2bool(pins), setting)

        # Send event with new state
        self.__fire_pinstate_event()

    def set_electrode_pins(self, pins: Sequence[int], group_id: int=0, duty_cycle: int=255):
        """Set the currently enabled pins

        Specified electrodes will be activated, all other will be deactivated.
        Providing an empty array will deactivate all electrodes.

        Arguments:
            - pins: A list of pin numbers to activate
            - group_id: Which electrode enable group to be set (default: 0)
                0: Drive group A
                1: Drive group B
            - duty_cycle: Duty cycle for the group (0-255)
        """
        logging.debug(f"Received set_electrode_pins({pins})")

        if group_id < 0 or group_id > 1:
            raise ValueError(f"group_id={group_id} is invalid. It must be 0 or 1.")

        # Send message to device to update
        msg = ElectrodeEnableMsg()
        msg.group_id = group_id
        msg.setting = duty_cycle
        msg.values = pinlist2mask(pins)
        self.purpledrop.send_message(msg)

        # Update local state
        self.pin_state.drive_groups[group_id] = PinState.DriveGroup(pinlist2bool(pins), duty_cycle)

        # Send event with new state
        self.__fire_pinstate_event()

    def set_feedback_command(self, target, mode, input_groups_p_mask, input_groups_n_mask, baseline):
        """Update feedback control settings

        When enabled, the purpledrop controller will adjust the duty cycle of
        electrode drive groups based on capacitance measurements.

        Arguments:
            - target: The controller target in counts
            - mode:
                - 0: Disabled
                - 1: Normal
                - 2: Differential
            - input_groups_p_mask: Bit mask indicating which capacitance groups to 
              sum for positive input (e.g. for groups 0 and 2: 5)
            - input_groups_n_mask: Bit mask for negative input groups (used in differential mode)
            - baseline: The duty cycle to apply to both drive groups when no error signal is 
              present (0-255)
        """
        msg = messages.FeedbackCommandMsg()
        msg.target = target
        msg.mode = mode
        msg.input_groups_p_mask = input_groups_p_mask
        msg.input_groups_n_mask = input_groups_n_mask
        msg.baseline = baseline
        self.purpledrop.send_message(msg)

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

    def calibrate_capacitance_offset(self):
        """Request a calibration of the capacitance measurement zero offset

        Arguments: None

        Returns: None
        """
        msg = messages.CalibrateCommandMsg()
        msg.command = messages.CalibrateCommandMsg.CAP_OFFSET_CMD
        self.purpledrop.send_message(msg)

    def get_device_info(self):
        """Gets information about the connected purpledrop device

        Arguments: None

        Returns: Object with the following fields: 
          - connected: boolean indicating if a device is currently connected
          - serial_number: The serial number of the connected device
          - software_version: The software version string of the connected device
        """
        serial_number = self.purpledrop.connected_serial_number()
        if serial_number is None:
            return {
                'connected': False,
                'serial_number': '',
                'software_version': ''
            }
        else:
            software_version = self.get_software_version()
            return {
                'connected': True,
                'serial_number': serial_number,
                'software_version': software_version
            }

    def read_gpio(self, gpio_num):
        """Reads the current input value of a GPIO pin

        Arguments:
          - gpio_num:  The ID of the GPIO to read

        Returns: A bool
        """
        msg = messages.GpioControlMsg()

        msg.pin = gpio_num
        msg.read = True

        listener = self.purpledrop.get_sync_listener(msg_filter=messages.GpioControlMsg)
        self.purpledrop.send_message(msg)
        rxmsg  = listener.wait(0.5)
        if rxmsg is None:
            raise TimeoutError("No response from purpledrop to GPIO read request")
        else:
            return rxmsg.value

    def write_gpio(self, gpio_num, value, output_enable):
        """Set the output state of a GPIO pin

        Arguments:
          - gpio_num: The ID of the GPIO to set
          - value: The output value (boolean)
          - output_enable: Set the GPIO as an output (true) or input (false)

        Returns:
          - The value read on the GPIO (bool)
        """
        msg = messages.GpioControlMsg()

        msg.pin = gpio_num
        msg.read = False
        msg.value = value
        msg.output_enable = output_enable

        listener = self.purpledrop.get_sync_listener(msg_filter=messages.GpioControlMsg)
        self.purpledrop.send_message(msg)
        rxmsg  = listener.wait(0.5)
        if rxmsg is None:
            raise TimeoutError("No response from purpledrop to GPIO read request")
        else:
            return rxmsg.value

    def set_electrode_calibration(self, voltage: float, offsets: Sequence[int]):
        """Set the capacitance offset for each electrode

        Provides a table of values to be subtracted for each electrode to
        compensate for parasitic capacitance of the electrode. Values are
        measured at high gain, with no liquid on the device, at a certain
        voltage.

        These values will be adjusted for changes in voltage from the measured
        voltage, and for low gain when applied by the purpledrop.

        Arguments:
          - voltage: The voltage setting at which the offsets were measured
          - offsets: A list of 128 16-bit values to be subtracted

        Returns: None
        """
        offsets = list(map(int, offsets))
        table = struct.pack("<f128H", voltage, *offsets)

        tx_pos = 0
        while tx_pos < len(table):
            tx_size = min(64, len(table) - tx_pos)
            msg = messages.DataBlobMsg()
            msg.blob_id = msg.OFFSET_CALIBRATION_ID
            msg.chunk_index = tx_pos
            msg.payload_size = tx_size
            msg.payload = table[tx_pos:tx_pos+tx_size]
            tx_pos += tx_size
            listener = self.purpledrop.get_sync_listener(messages.CommandAckMsg)
            self.purpledrop.send_message(msg)
            ack = listener.wait(timeout=0.5)
            if ack is None:
                raise TimeoutError("No ACK while setting electrode calibration")

    def set_scan_gains(self, gains: Optional[Sequence[bool]]=None):
        """Set the gains used for capacitance scan measurement

        If no gains argument is provided, scan gains will be set based on
        oversized electrodes defined in the board definition file.

        Arguments:
          - gains: A list of 128 booleans, true indicating that an electrode
            should be scanned with low gain
        """
        if gains is not None:
            if len(gains) != 128:
                raise ValueError("Scan gains must have 128 values")
            # Make sure they are all convertible to bool
            gains = [bool(x) for x in gains]
        self.__set_scan_gains(gains)

    def get_scan_gains(self) -> List[bool]:
        """Return the current scan gain settings
        """
        return [x == CAPGAIN_LOW for x in self.scan_gains]