from functools import reduce
import numpy as np
import schema
import time
from typing import Dict, List, Sequence, Set

import purpledrop.messages as messages
from purpledrop.electrode_board import Layout

MoveCommandSchema = schema.Schema({
    'start_pins': schema.And([int], len),
    'end_pins': schema.And([int], len),
    schema.Optional('timeout'): schema.Use(float),
    schema.Optional('post_capture_time'): schema.Use(float),
    schema.Optional('low_gain'): bool,
    schema.Optional('threshold'): schema.Use(float)
    })

class MoveDropResult(dict):
    """Inherits from dict for JSON serializability
    """
    def __init__(self, success=False, closed_loop=False, closed_loop_result=None):
        dict.__init__(
            self,
            success=success,
            closed_loop=closed_loop,
            closed_loop_result=closed_loop_result,
        )

class MoveDropClosedLoopResult(dict):
    """Inherits from dict for JSON serializability
    """
    def __init__(self,
                    pre_capacitance: float,
                    post_capacitance: float,
                    time_series: Sequence[float],
                    capacitance_series: Sequence[float]):
        dict.__init__(
            self,
            pre_capacitance=pre_capacitance,
            post_capacitance=post_capacitance,
            time_series=time_series,
            capacitance_series=capacitance_series
        )

class Location(object):
    def __init__(self, coords: Sequence[int]):
        self.x = coords[0]
        self.y = coords[1]

    def __getattr__(self, idx):
        if idx == 0:
            return x
        elif idx == 1:
            return y
        else:
            raise IndexError(f"Location index {idx} is out of range")

    def move_one(self, dir):
        dir = dir.lower()
        if dir == "up":
            return Location([self.x, self.y-1])
        elif dir == "down":
            return Location([self.x, self.y+1])
        elif dir == "left":
            return Location([self.x-1, self.y])
        elif dir == "right":
            return Location([self.x+1, self.y])
        else:
            raise ValueError(f"Invalid move direction: {dir}")

class Rectangle(object):
    def __init__(self, location: Location, dimensions: Sequence[int]):
        if not isinstance(location, Location):
            raise ValueError("location must be a Location object")
        if len(dimensions) != 2:
            raise ValueError("dimensions must be a sequence of 2 floats")

        self.location = location
        self.dimensions = dimensions

    def move_one(self, dir):
        return Rectangle(self.location.move_one(dir), self.dimensions)

    def grid_locations(self):
        locs = []
        for x in range(self.dimensions[0]):
            for y in range(self.dimensions[1]):
                locs.append((x + self.location.x, y + self.location.y))
        return locs

def _set_pins_with_ack(purpledrop, pins):
    def msg_filter(msg):
        if isinstance(msg, messages.CommandAckMsg) and \
            msg.acked_id == messages.ElectrodeEnableMsg.ID:
            return True
        return False

    with purpledrop.purpledrop.get_sync_listener(msg_filter) as listener:
        retries = 8
        while retries > 0:
            purpledrop.set_electrode_pins(pins)
            # Read up to ACK of set pins
            msg = listener.next(timeout=0.25)
            if msg is not None:
                return msg
            retries -= 1
    raise RuntimeError("Timed out waiting for electrode command ACK")

def move_drop(purpledrop, start, size, direction, post_capture_time=0.25):
    initial_rect = Rectangle(Location(start), size)
    final_rect = initial_rect.move_one(direction)

    layout = Layout(purpledrop.get_board_definition()['layout'])
    pins = [layout.grid_location_to_pin(loc[0], loc[1]) for loc in initial_rect.grid_locations()]
    if None in pins:
        raise ValueError("Invalid move coordinates")

    # Ensure drive group B is off
    purpledrop.set_electrode_pins([], 1)

    _set_pins_with_ack(purpledrop, pins)

    # Create a listener which will queue all incoming messages that match
    # our filter. We can expect to get all messages in the order they were
    # received
    with purpledrop.active_capacitance_collector() as collector:
        _raw, calibrated = purpledrop.wait_for_active_capacitance(timeout=2.0)
        pre_capacitance = calibrated

        pins = [layout.grid_location_to_pin(loc[0], loc[1]) for loc in final_rect.grid_locations()]
        if None in pins:
            raise ValueError("Invalid move destination")
        _set_pins_with_ack(purpledrop, pins)

        MOVE_THRESHOLD = 0.8 * pre_capacitance
        MOVE_TIMEOUT = 5.0
        time_series = []
        cap_series = []
        t = 0.0
        start_time = time.time()
        end_time = start_time + MOVE_TIMEOUT
        detected = False

        # Flush received samples so we know we've consumed all samples from the
        # starting pins
        while not collector.empty():
            measurement = collector.next(timeout=1.0)
            if measurement is None:
                raise TimeoutError("Timeout waiting for capacitance report")
            _raw, calibrated = measurement
            time_series.append(t)
            cap_series.append(calibrated)
            t += 2e-3

        while time.time() < end_time:
            measurement = collector.next(timeout=1.0)
            if measurement is None:
                raise RuntimeError("Timed out waiting for capacitance message")
            _raw, calibrated = measurement
            time_series.append(t)
            cap_series.append(calibrated)
            # For now, assume the samples are periodic at 2ms to create a time vector
            # At some point, they should come with their own timestamps
            t += 2e-3
            if calibrated >= MOVE_THRESHOLD and not detected:
                # keep capturing for a while longer after hitting the target threshold
                end_time = time.time() + post_capture_time
                detected = True

        post_capacitance = cap_series[-1]

        closed_loop_result = MoveDropClosedLoopResult(
            pre_capacitance,
            post_capacitance,
            time_series,
            cap_series
        )

        return MoveDropResult(detected, True, closed_loop_result)

def move_drops(purpledrop, moves: List[Dict]) -> List[MoveDropResult]:
    """Moves multiple drops concurrently

    This method can move up to 5 concurrent drops. This limits is set by the
    number of capacitance scan groups supported by the Purpledrop.

    Args:
        moves: A list of move command argument dicts, of the form shown below

    Returns:
        A list of MoveDropResult objects, one for each move argument

    A move argument object has four fields:
        "start_pins": List of electrode pins on which the drop currently reside.
                      These are used to measure the initial capacitance.
        "end_pins": List of electrode pins onto which the drop is to be moved.
        "timeout": Optional. Move timeout in seconds. If not provided, a default is used.
        "post_capture_time": Optional. Amount of time to capture capacitance data after
                             move is completed. If not provided, a default is used.
        "low_gain": Optional. If set true, low gain will be used for capacitance
                    measurement.
        "threshold": Optional. Sets the capacitance required for move to be complete,
                     as fraction of initial capacitance. If not provided, a default
                     is used.

    Example move object:

        {
            "start_pins": [3, 4, 5, 6],
            "end_pins": [5, 6, 7, 8],
            "timeout": 5.0,
            "post_capture_time": 0.25,
            "low_gain": False,
        }

    """

    MAX_DROPS = 5
    DEFAULT_TIMEOUT = 10.0
    DEFAULT_THRESHOLD = 0.8
    DEFAULT_POST_CAPTURE_TIME = 0.25

    # Validate input arguments: must be a list of objects matching MoveCommandSchema
    # Will raise on failure
    moves = schema.Schema([MoveCommandSchema]).validate(moves)

    if len(moves) > MAX_DROPS:
        raise ValueError(f"Cannot move more than {MAX_DROPS} concurrently")

    def group_scan_filter(msg):
        if isinstance(msg, messages.BulkCapacitanceMsg) and msg.group_scan != 0:
            return True
        return False

    # Collect all of the pins together from all drops
    start_pins: List[int] = list(reduce(lambda a,b: set(a).union(b), [m['start_pins'] for m in moves], set()))
    end_pins: List[int] = list(reduce(lambda a,b: set(a).union(b), [m['end_pins'] for m in moves], set()))

    # Ensure drive group B is off
    purpledrop.set_electrode_pins([], 1)

    # Setup capacitance groups
    for i, m in enumerate(moves):
        time.sleep(0.02) # hack to avoid overflowing receive buffer
        # The delay can be removed embedded software supports acking and/or
        # gets a longer rx buffer
        gain_setting = int(m.get('low_gain', False))
        purpledrop.set_capacitance_group(m['start_pins'], i, gain_setting)

    # Enable the start pins
    # This makes sure drops are properly located, and allows for most reliable
    # initial capacitance measurement
    _set_pins_with_ack(purpledrop, start_pins)

    n_drops = len(moves)
    cap_series: List[List[float]] = []

    # Begin collecting samples of group capacitance
    with purpledrop.group_capacitance_collector() as collector:

        # Read group capacitance to get initial values
        _raw, initial_cap = purpledrop.wait_for_group_capacitance(timeout=2.0)

        # Change capacitance groups to measure destination electrodes
        for i, m in enumerate(moves):
            time.sleep(0.02) # hack to avoid overflowing receive buffer
            gain_setting = int(m.get('low_gain', False))
            purpledrop.set_capacitance_group(m['end_pins'], i, gain_setting)

        # Enable the destination electrodes
        _set_pins_with_ack(purpledrop, end_pins)

        # Flush received samples so we know we've consumed all samples from the
        # starting pins
        while not collector.empty():
            measurement = collector.next(timeout=2.0)
            if measurement is None:
                raise TimeoutError("Timeout waiting for group capacitance report")
            _raw, calibrated = measurement
            cap_series.append(calibrated)

        start_time = time.time()
        end_times = [start_time + m.get('timeout', DEFAULT_TIMEOUT) for m in moves]
        last_sample_index = [0] * n_drops
        finish_thresholds = [m.get('threshold', DEFAULT_THRESHOLD) * initial_cap[i] for i, m in enumerate(moves)]
        success_flags = [False] * n_drops
        n_running = n_drops

        while n_running > 0:
            measurement = collector.next(timeout=2.0)
            if measurement is None:
                raise TimeoutError("Timeout waiting for group capacitance report")
            _raw, calibrated = measurement
            cap_series.append(calibrated)
            if collector.empty():
                curtime = time.time()
                for i in range(n_drops):
                    if last_sample_index[i] != 0:
                        # Drop previously finished
                        continue
                    if not success_flags[i] and calibrated[i] >= finish_thresholds[i]:
                        success_flags[i] = True
                        # keep capturing for a while longer after hitting the target threshold
                        end_times[i] = curtime + moves[i].get('post_capture_time', DEFAULT_POST_CAPTURE_TIME)
                    if curtime > end_times[i]:
                        # This drop is now finished
                        last_sample_index[i] = len(cap_series)
                        n_running -= 1

        results = []
        for i in range(n_drops):
            cap_data = [x[i] for x in cap_series[:last_sample_index[i]]]
            final_cap = 0.0
            if len(cap_data) > 0:
                final_cap = cap_data[-1]
            # Assuming known sample period of 2ms
            time_series = np.arange(0, len(cap_data) * 2e-3, 2e-3).tolist()
            closed_loop_result = MoveDropClosedLoopResult(
                initial_cap[i],
                final_cap,
                time_series,
                cap_data)
            results.append(MoveDropResult(success_flags[i], True, closed_loop_result))

        return results

