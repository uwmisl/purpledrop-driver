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
        self.lock = threading.Lock()
        self.event_listeners = []

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

        elif isinstance(msg, messages.TemperatureMsg):
            self.temperatures = [float(x) / 100.0 for x in msg.measurements]

    def __fire_event(self, event):
        with self.lock:
            for listener in self.event_listeners:
                listener(event)

    def register_event_listener(self, func):
        with self.lock:
            self.event_listeners.append(func)

    def get_board_definition(self):
        """Get electrode board configuratin object

        Arguments: None
        """
        return {
            "layout": {
                "pins": [
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

class PurpleDropRpc(object):
    """Wrapper to define the RPC methods for remote control of purpledrop
    """
    def __init__(self, purple_drop_controller):
        self.pdc = purple_drop_controller

    def get_board_definition(self):
        return self.pdc.get_board_definition()

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
