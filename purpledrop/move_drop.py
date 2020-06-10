import time
from typing import Sequence

import purpledrop.messages as messages
from purpledrop.electrode_board import Layout

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

def move_drop(purpledrop, start, size, direction):
    initial_rect = Rectangle(Location(start), size)
    final_rect = initial_rect.move_one(direction)

    def wait_for(msgtype, timeout):
        start = time.time()
        while time.time() - start < timeout:
            msg = listener.wait(timeout=0.1)
            if msg is not None and isinstance(msg, msgtype):
                return msg
        return None

    def msg_filter(msg):
        if isinstance(msg, messages.ActiveCapacitanceMsg):
            return True
        if isinstance(msg, messages.CommandAckMsg) and \
            msg.acked_id == messages.ElectrodeEnableMsg.ID:
            return True
        return False
    
    def set_pins(pins):
        retries = 8
        while retries > 0:
            purpledrop.set_electrode_pins(pins)
            # Read up to ACK of set pins
            msg = wait_for(messages.CommandAckMsg, 0.2)
            if msg is not None:
                return msg
            retries -= 1
        raise RuntimeError("Timed out waiting for electrode command ACK")

    # Create a listener which will queue all incoming messages that match
    # our filter. We can expect to get all messages in the order they were
    # received
    listener = purpledrop.purpledrop.get_sync_listener(msg_filter)

    layout = Layout(purpledrop.get_board_definition()['layout'])
    pins = [layout.grid_location_to_pin(loc[0], loc[1]) for loc in initial_rect.grid_locations()]
    if None in pins:
        raise ValueError("Invalid move coordinates")
    set_pins(pins)

    msg = wait_for(messages.ActiveCapacitanceMsg, 2.0)
    if msg is None:
        raise RuntimeError("Timed out waiting for first capacitance message")

    pre_capacitance = msg.measurement - msg.baseline

    pins = [layout.grid_location_to_pin(loc[0], loc[1]) for loc in final_rect.grid_locations()]
    if None in pins:
        raise ValueError("Invalid move destination")
    set_pins(pins)

    MOVE_THRESHOLD = 0.8 * pre_capacitance
    MOVE_TIMEOUT = 5.0
    time_series = []
    cap_series = []
    t = 0.0
    start_time = time.time()
    while True:
        msg = wait_for(messages.ActiveCapacitanceMsg, 0.5)
        if msg is None:
            raise RuntimeError("Timed out waiting for capacitance message")
        time_series.append(t)
        x = msg.measurement - msg.baseline
        cap_series.append(x)
        # For now, just assume the samples are periodic at 2ms to create a time vector
        # At some point, they should come with their own timestamps
        t += 2e-3
        if x >= MOVE_THRESHOLD:
            break
        if time.time() - start_time > MOVE_TIMEOUT:
            break

    post_capacitance = cap_series[-1]

    success = post_capacitance > MOVE_THRESHOLD
    closed_loop_result = MoveDropClosedLoopResult(
        pre_capacitance,
        post_capacitance,
        time_series,
        cap_series
    )

    return MoveDropResult(success, True, closed_loop_result)