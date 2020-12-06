import logging
import os
import struct
import threading
import time
from typing import Callable, List, Optional, Sequence

import purpledrop.protobuf.messages_pb2 as messages_pb2

logger = logging.getLogger("purpledrop")

def get_timestamp(event: messages_pb2.PurpleDropEvent) -> Optional[float]:
    """Return a timestamp from a message

    Returns: timstamp in floating point seconds, or None if no timestamp was available
    """
    # A list of attributes to test for (i.e. message types that can contain timestamps)
    for field_name in [field.name for field in event.DESCRIPTOR.fields]:
        if event.HasField(field_name):
            event = getattr(event, field_name)
            if not event.HasField('timestamp'):
                return None
            timestamp = getattr(event, 'timestamp', None)
            event_time = float(timestamp.seconds) + float(timestamp.nanos) / 1e9
            return event_time
    return None

class State(object):
    def __init__(self, **kwargs):
        self.active_capacitance = 0.0
        self.bulk_capacitance = []
        self.electrode_state = []
        self.temperatures = []
        self.voltage = 0.0

        for key, value in kwargs.items():
            self.setattr(key, value)

    def update(self, event: messages_pb2.PurpleDropEvent):
        if event.HasField('active_capacitance'):
            self.active_capacitance = event.active_capacitance.measurement.capacitance
        elif event.HasField('bulk_capacitance'):
            self.bulk_capacitance = [m.capacitance for m in event.bulk_capacitance.measurements]
        elif event.HasField('electrode_state'):
            self.electrode_state = event.electrode_state.electrodes
        elif event.HasField('hv_regulator'):
            self.voltage = event.hv_regulator.voltage
        elif event.HasField('temperature_control'):
            self.temperatures = event.temperature_control.temperatures

class Index(object):
    class Entry(object):
        def __init__(self, timestamp, state, offset):
            self.timestamp = timestamp
            self.state = state
            self.offset = offset

    def __init__(self):
        self.index = []

    def append(self, timestamp: float, state: State, offset: int):
        self.index.append(self.Entry(timestamp, state, offset))

    def __getitem__(self, key: int):
        return self.index[key]

    def lookup(self, timestamp: float) -> 'Index.Entry':
        selected = None
        for i in range(0, len(self.index)):
            if self.index[i].timestamp > timestamp:
                break
            else:
                selected = i

        if selected is None:
            raise ValueError(f"Cannot seek to {timestamp}. It's out of range")

        return self.index[selected]

def index_log(event_reader, segment_size=50*1024*1024):
    """Parse the entire log file, and return an index + end_time

    The index is a list of timestamps, states, and file offsets to allow
    for faster seeking in the file.
    """
    # Try opening as file if it isn't an already opening file
    if not isinstance(event_reader, EventReader):
        event_reader = EventReader(event_reader)
    event_reader.seek(0)
    next_offset = segment_size
    state = State()
    index = Index()
    last_timestamp = 0.0

    # Create an initial index at the beginning of the file
    index.append(event_reader.start_time(), State(), 0)

    while True:
        event = event_reader.next()
        if event is None:
            # Reached end of file
            return (index, last_timestamp)
        state.update(event)
        timestamp = get_timestamp(event)
        # On first event with timestamp after the offset, save an index point
        if event_reader.current_offset() > next_offset and timestamp is not None:
            index.append(timestamp, state, event_reader.current_offset())
            next_offset += segment_size

        if timestamp is not None:
            last_timestamp = timestamp

class EventReader(object):
    def __init__(self, filepath):
        self.filepath = filepath
        self.fd = open(filepath, 'rb')
        self.__end_time = None

    def seek(self, offset):
        """Move to a particular offset in the file

        Note: You cannot just move to an arbitrary offset; you must move to
        the beginning of a protobuf message.
        """
        self.fd.seek(offset, os.SEEK_SET)

    def file_size(self):
        return os.fstat(self.fd.fileno()).st_size

    def current_offset(self):
        return self.fd.tell()

    def __iter__(self):
        return self

    def __next__(self):
        msg = self.next()
        if msg is None:
            raise StopIteration()
        return msg

    def next(self):
        """Consume a message from the stream and return it
        """
        length_bytes = self.fd.read(4)
        if len(length_bytes) != 4:
            return None
        length = struct.unpack("I", length_bytes)[0]
        msg_data = self.fd.read(length)
        if len(msg_data) != length:
            return None
        event = messages_pb2.PurpleDropEvent()
        event.ParseFromString(msg_data)
        return event

    def skip(self, n=1):
        """Consume n messages from the stream, but don't parse them

        Returns: The number of messages skipped
        """
        count = 0
        while count < n:
            length_bytes = self.fd.read(4)
            if len(length_bytes) != 4:
                return count
            length = struct.unpack("I", length_bytes)[0]
            self.fd.seek(length, os.SEEK_CUR)
            count += 1
        return count

    def start_time(self):
        pos = self.fd.tell()
        self.fd.seek(0, os.SEEK_SET)
        timestamp = None

        while True:
            event = self.next()
            if event is None:
                break
            timestamp = get_timestamp(event)
            if timestamp is not None:
                break

        # Restore the file position
        self.fd.seek(pos, os.SEEK_SET)
        return timestamp

    def end_time(self):
        """Find the last timestamp in the file
        """
        # This requires seeking through the entire file, so memoize
        if self.__end_time is None:
            # We don't need to parse all the messages, so we skip up to
            # near the end. PARSE_START_OFFSET needs to be larger than the
            # largest event to guarantee we get a time
            PARSE_START_OFFSET = 3*1024*1024

            pos = self.fd.tell()
            self.fd.seek(0, os.SEEK_SET)

            file_size = self.file_size()
            while True:
                if self.fd.tell() < file_size - PARSE_START_OFFSET:
                    self.skip()
                else:
                    event = self.next()
                    if event is None:
                        break
                    timestamp = get_timestamp(event)
                    if timestamp is not None:
                        self.__end_time = timestamp

            # Restore file positions
            self.fd.seek(pos, os.SEEK_SET)

        return self.__end_time

class PlaybackPurpleDrop(object):
    """Emulates a PurpleDropController with recorded data

    Provides register_event_listener, a subset of the normal RPC calls, as well
    as some extra RPC calls for controlling playback.
    """

    RPC_METHODS = [
        'get_board_definition',
        'get_bulk_capacitance',
        'get_active_capacitance',
        'get_parameter_definitions',
        'get_electrode_pins',
        'get_temperatures',
        'get_hv_supply_voltage',
        'playback_seek',
        'playback_enable',
    ]

    class MockVideoClient(object):
        def __init__(self):
            self.callback = None

        def register_callback(self, callback):
            self.callback = callback

    def __init__(self, filepath: str, index: Index, board_definition):
        self.event_reader = EventReader(filepath)
        self.index = index
        self.board_definition = board_definition
        self.time_origin = self.event_reader.start_time()

        self.command = None
        self.state = State()
        self.playing = True
        self.event_listeners: List[Callable] = []
        self.playback_time = 0.0
        self.listener_lock = threading.Lock()
        self.reader_lock = threading.Lock()
        self.mock_video_client = self.MockVideoClient()
        self.thread = threading.Thread(target=self.__thread_entry, name="Playback reader", daemon=True)
        self.thread.start()

    def register_event_listener(self, func):
        """Register a callback for state update events
        """
        with self.listener_lock:
            self.event_listeners.append(func)

    def get_board_definition(self):
        """Get electrode board configuratin object

        Arguments: None
        """
        logger.debug(f"Received get_board_definition")
        return self.board_definition.as_dict()

    def get_parameter_definitions(self):
        return {"parameters": []}

    def get_bulk_capacitance(self) -> List[float]:
        """Get the most recent capacitance scan results

        Arguments: None
        """
        logger.debug("Received get_bulk_capacitance")
        return self.state.bulk_capacitance

    def get_active_capacitance(self) -> float:
        """Get the most recent active electrode capacitance

        Arguments: None
        """
        logger.debug("Received get_active_capacitance")
        return self.state.active_capacitance

    def get_electrode_pins(self):
        """Get the current state of all electrodes

        Arguments: None

        Returns: List of booleans
        """
        logging.debug("Received get_electrode_pins")
        return self.state.electrode_state

    def get_temperatures(self) -> Sequence[float]:
        """Returns an array of all temperature sensor measurements in degrees C

        Arguments: None
        """
        logging.debug("Received get_temperatures")
        return self.state.temperatures

    def get_hv_supply_voltage(self):
        """Return the latest high voltage rail measurement

        Arguments: None

        Returns: A float, in volts
        """
        logging.debug("Received get_hv_supply_voltage")
        return self.state.voltage

    def playback_seek(self, seek_time):
        logging.debug("Received playback_seek")
        with self.reader_lock:
            self.command = {'type': 'seek', 'time': seek_time}
        return True

    def playback_enable(self, enable):
        with self.reader_lock:
            self.playing = enable
        return True

    def __seek_to_time(self, time):
        """Position the playback to a given offset in the stream

        time is the offset in seconds *from the beginning of the file*.
        """

        # Get the nearest index point and seek to that
        start_point = self.index.lookup(time + self.time_origin)
        self.state = start_point.state
        self.event_reader.seek(start_point.offset)
        print(f"Seeking to {start_point.offset}")

        # Read (and discard) up to the seek time
        print(f"Advancing to {time}")
        for _ in self.__advance_to_time(time):
            pass
        self.playback_time = time

    def __advance_to_time(self, time):
        """Consume and yield messages until a timestamp greater than time is encountered
        """
        while True:
            event = self.event_reader.next()
            if event is not None:
                yield event
            timestamp = get_timestamp(event) - self.time_origin
            if timestamp is not None and timestamp > time:
                break

    def __fire_event(self, event):
        with self.listener_lock:
            for listener in self.event_listeners:
                listener(event)

    def __thread_entry(self):
        last_time = None
        while True:
            update_time = time.monotonic()
            with self.reader_lock:
                if self.command is not None:
                    if(self.command['type'] == 'seek'):
                        self.__seek_to_time(self.command['time'])
                    else:
                        raise RuntimeError(f"Unrecognized command: {command}")
                self.command = None

                if self.playing:
                    event_count = 0
                    for event in self.__advance_to_time(self.playback_time):
                        self.state.update(event)
                        self.__fire_event(event)
                        event_count += 1
                    if last_time is not None:
                        self.playback_time += update_time - last_time
                    last_time = update_time
                else:
                    last_time = None

            time.sleep(0.05)

