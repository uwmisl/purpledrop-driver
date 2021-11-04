"""Low-level driver for communicating with PurpleDrop via serial messages
"""
from abc import abstractmethod, ABC
import gevent
import inspect
import logging
import queue
import serial
import serial.tools.list_ports
from typing import Any, AnyStr, Callable, Dict, List, Optional

from .messages import PurpleDropMessage
from .message_framer import MessageFramer, serialize


logger = logging.getLogger("purpledrop")

# List of USB VID/PID pairs which will be recognized as a purpledrop
PURPLEDROP_VIDPIDS = [
    (0x02dd, 0x7da3),
    (0x1209, 0xCCAA),
]

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


class PurpleDropRxThread(object):
    def __init__(self, port: serial.Serial, callback: Callable[[PurpleDropMessage], None]=None):
        self._thread = gevent.Greenlet(self.run)
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

    def __init__(self,
                 purpledrop: 'PurpleDropDevice',
                 msg_filter: Callable[[PurpleDropMessage], bool]=None,
                 transform: Callable[[PurpleDropMessage], Any]=None):
        """Create a listener object

        The SyncListener can be used in a with statement, e.g.

            with purpledrop.get_sync_listener(filter) as listener:
                msg = listener.next()

        Alternatively, you can call the `register` method to begin listening for
        messages, and `unregister` to stop. However, be sure to always call
        `unregister` when finished, or else you will create a memory leak and
        performance hit as incoming messages will continue to be passed to the
        listener queue until it is unregistered.
        """
        self.owner = purpledrop
        self.filter = resolve_msg_filter(msg_filter)
        self.fifo: queue.Queue[PurpleDropMessage] = queue.Queue()
        self.transform = transform
        self.delegate = self.MsgDelegate(self.filter, self.fifo)

    def __enter__(self):
        self.register()
        return self

    def __exit__(self, type, value, traceback):
        self.unregister()

    def register(self):
        self.owner.register_listener(self.delegate)

    def unregister(self):
        self.owner.unregister_listener(self.delegate)

    def get_msg_handler(self):
        return self.delegate

    def empty(self) -> bool:
        return self.fifo.empty()

    def next(self, timeout: Optional[float]=None) -> Optional[PurpleDropMessage]:
        try:
            msg = self.fifo.get(timeout=timeout)
            if self.transform is not None:
                msg = self.transform(msg)
            return msg
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

class PurpleDropDevice(ABC):
    """Abstract class for a purple drop device
    """
    def __init__(self):
        self.lock = gevent.lock.RLock()
        self.listeners = []
        self.__connected_callbacks: List[Callable] = []
        self.__disconnected_callbacks: List[Callable] = []

    def register_connected_callback(self, callback: Callable):
        self.__connected_callbacks.append(callback)

    def register_disconnected_callback(self, callback: Callable):
        self.__disconnected_callbacks.append(callback)

    def on_connected(self):
        for cb in self.__connected_callbacks:
            cb()

    def on_disconnected(self):
        for cb in self.__disconnected_callbacks:
            cb()

    def register_listener(self, listener):
        with self.lock:
            self.listeners.append(listener)

    def unregister_listener(self, listener):
        with self.lock:
            if listener in self.listeners:
                self.listeners.remove(listener)

    def get_sync_listener(self, msg_filter=None, transform=None) -> SyncListener:
        return SyncListener(purpledrop=self, msg_filter=msg_filter, transform=transform)

    def get_async_listener(self, callback, msg_filter=None) -> AsyncListener:
        new_listener = AsyncListener(owner=self, callback=callback, msg_filter=msg_filter)
        with self.lock:
            self.listeners.append(new_listener.get_msg_handler())
        return new_listener

    def on_message_received(self, msg):
        with self.lock:
            for handler in self.listeners:
                handler(msg)

    def connected_serial_number(self) -> Optional[str]:
        """Returns the serial number of the connected device
        """
        return "NA"

    @abstractmethod
    def send_message(self, msg: PurpleDropMessage):
        pass

    @abstractmethod
    def connected(self) -> bool:
        pass

class SerialPurpleDropDevice(PurpleDropDevice):
    """Low level messaging for controlling a PurpleDrop via a serial port

    Use `list_purpledrop_devices()` to find devices based on their USB VID/PID
    and serial number. Then provide the com port (e.g. `/dev/ttyACM0`) when
    instantiating a PurpleDropDevice.

    NOTE: This class provides low level control of the device. For most uses,
    you should be using PurpleDropControl which provides higher level
    functionality and matches the JSON-RPC methods provided by `pd-server`.
    """
    def __init__(self, port=None):
        super().__init__()
        self._rx_thread = None
        self._ser = None

        if port is not None:
            self.open(port)

    def open(self, port):
        logger.debug(f"PurpleDropDevice: opening {port}")
        self._ser = serial.Serial(port, timeout=0.01, write_timeout=0.5)
        self._rx_thread = PurpleDropRxThread(self._ser, callback=self.on_message_received)
        self._rx_thread.start()
        self.on_connected()

    def close(self):
        logger.debug("Closing PurpleDropDevice")
        if self._rx_thread is not None:
            self._rx_thread.stop()
            self._rx_thread.join()
        if self._ser is not None:
            self._ser.close()
            self.on_disconnected()

    def connected(self):
        return self._ser is not None and \
            self._rx_thread is not None and \
            self._rx_thread.running

    def send_message(self, msg: PurpleDropMessage):
        tx_bytes = serialize(msg.to_bytes())
        with self.lock:
            self._ser.write(tx_bytes)
class PersistentPurpleDropDevice(SerialPurpleDropDevice):
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
        self.__thread = gevent.Greenlet(self.__thread_entry)
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
            gevent.sleep(5.0)

