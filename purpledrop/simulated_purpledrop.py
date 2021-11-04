import threading
import time
import queue

import purpledrop.messages as messages
from .purpledrop import PurpleDropDevice

def pinmask2list(mask):
    assert len(mask) == 16
    pins = []
    for p in range(128):
        bit = p % 8
        offset = int(p / 8)
        if (mask[offset] & (1<<bit)) != 0:
            pins.append(p)
    return pins

class ElectrodeNode(object):
    def __init__(self, state=False):
        self.state = state
        self.volume = 0.0
        self.just_moved = False
        self.recurse_flag = False
        self.__connections = []

    def add_connection(self, neighbor):
        if neighbor in self.__connections:
            return
        self.__connections.append(neighbor)
        neighbor.add_connection(self)

    def connections(self):
        return self.__connections

def is_pullable(e: ElectrodeNode, dst: ElectrodeNode):
    if e.volume == 0 or e.just_moved:
        return False
    if not e.state:
        return True
    for c in e.connections():
        # Don't recurse back through a node we already traversed, lest we get
        # stuck in a loop
        if c == dst or c.recurse_flag:
            continue
        try:
            e.recurse_flag = True
            if is_pullable(c, e):
                return True
        finally:
            e.recurse_flag = False

    return False

def pull_drop(cur: ElectrodeNode, dst: ElectrodeNode):
    """Pull drop on cur onto dst

    Recursively
    """
    assert dst.volume == 0.0
    assert cur.volume == 1.0
    dst.volume = 1.0
    cur.volume = 0.0
    dst.just_moved = True
    for c in cur.connections():
        if is_pullable(c, cur):
            pull_drop(c, cur)
            break

class SimulatedPurpleDropDevice(PurpleDropDevice):
    """Acts like a purpledrop device, sending and receiving messages

    Includes a simple drop movement model, which supports drop movement within
    electrode grid only.
    """
    # Capacitance (counts) for each covered electrode
    UNIT_CAPACITANCE = 1000
    GAIN_RATIO = 7

    N_CGROUPS = 5

    def __init__(self, board, drop_locations):
        super().__init__()
        self.electrodes = [ElectrodeNode() for _ in range(128)]
        self.msg_queue = queue.Queue()
        self.drive_a_values = [0] * 16
        self.drive_b_values = [0] * 16
        self.scan_groups = [{'pins': [], 'setting': 0} for _ in range(self.N_CGROUPS)]
        self.__connected = False

        # Populate initial drops
        for pin in drop_locations:
            self.electrodes[pin].volume = 1.0

        self.__load_board(board)

        self.__thread = threading.Thread(target=self.__thread_entry, name="Simulated PurpleDrop", daemon=True)
        self.__thread.start()

    def open(self):
        self.__connected = True
        self.on_connected()

    def close(self):
        self.__connected = False
        self.on_disconnected()

    def connected(self):
        return self.__connected

    def send_message(self, msg):
        """Override the PurpleDropDevice send method to receive messages"""
        # Put message into queue for background thread to handle
        self.msg_queue.put(msg)

    def __thread_entry(self):
        cycle_counter = 0
        while True:
            # Process incoming messages
            while True:
                try:
                    msg = self.msg_queue.get(block=False)

                    if isinstance(msg, messages.ElectrodeEnableMsg):
                        self.__handle_set_electrode(msg)
                    if isinstance(msg, messages.DataBlobMsg):
                        self.__handle_data_blob(msg)

                except queue.Empty:
                    break

            # Send messages
            if (cycle_counter % 5) == 0:
                self.__send_hv_supply_voltage()
            self.__send_active_capacitance()
            self.__send_group_capacitance()
            if (cycle_counter % 5) == 0:
                self.__send_capacitance_scan()

            # Update state
            self.__update_drop_positions()

            cycle_counter += 1
            time.sleep(0.05)

    def __handle_data_blob(self, msg: messages.DataBlobMsg):
        if msg.blob_id == messages.DataBlobMsg.SOFTWARE_VERSION_ID:
            resp = messages.DataBlobMsg()

            resp.payload = b"Simulated"
            resp.payload_size = len(resp.payload)
            resp.blob_id = messages.DataBlobMsg.SOFTWARE_VERSION_ID;
            resp.chunk_index = 0
            self.on_message_received(resp)

    def __handle_set_electrode(self, msg: messages.ElectrodeEnableMsg):
        if msg.group_id >= 100:
            scan_group_id = msg.group_id - 100
            self.scan_groups[scan_group_id] = {
                'pins': pinmask2list(msg.values),
                'setting': msg.setting
            }
        else:
            if msg.group_id == 1:
                self.drive_b_values = msg.values
            else:
                self.drive_a_values = msg.values

            def is_enabled(pin, values):
                assert(pin < 128)
                bit = pin % 8
                offset = int(pin / 8)
                return (values[offset] & (1<<bit)) != 0

            for pin in range(128):
                if is_enabled(pin, self.drive_b_values) or is_enabled(pin, self.drive_a_values):
                    self.electrodes[pin].state = True
                else:
                    self.electrodes[pin].state = False

        ack = messages.CommandAckMsg()
        ack.acked_id = messages.ElectrodeEnableMsg.ID
        self.on_message_received(ack)

    def __send_hv_supply_voltage(self):
        msg = messages.HvRegulatorMsg()
        msg.voltage = 100.0
        msg.v_target_out = 0
        self.on_message_received(msg)

    def __send_active_capacitance(self):
        capacitance = 0.0
        for pin in range(128):
            e = self.electrodes[pin]
            if e.state and e.volume > 0.0:
                capacitance += self.UNIT_CAPACITANCE
        capacitance = min(capacitance, 4095)
        active_cap_msg = messages.ActiveCapacitanceMsg()
        active_cap_msg.settings = 0
        active_cap_msg.baseline = 0
        active_cap_msg.measurement = int(capacitance)

    def __send_group_capacitance(self):
        capacitance = [0.0] * self.N_CGROUPS
        for i in range(self.N_CGROUPS):
            cgroup = self.scan_groups[i]
            for pin in cgroup['pins']:
                e = self.electrodes[pin]
                if cgroup['setting'] != 0:
                    capacitance[i] += e.volume * self.UNIT_CAPACITANCE / self.GAIN_RATIO
                else:
                    capacitance[i] += e.volume * self.UNIT_CAPACITANCE

        bulk_msg = messages.BulkCapacitanceMsg()
        bulk_msg.start_index = 0
        bulk_msg.group_scan = 1
        bulk_msg.count = self.N_CGROUPS
        bulk_msg.measurements = list([int(c) for c in capacitance])

        self.on_message_received(bulk_msg)

    def __send_capacitance_scan(self):
        values = [0] * 128
        for pin in range(128):
            if self.electrodes[pin].volume > 0.0:
                values[pin] = self.UNIT_CAPACITANCE
        # The actual device splits the capacitances over many messages
        # Here, we just make one long message.
        msg = messages.BulkCapacitanceMsg()
        msg.start_index = 0
        msg.group_scan = 0
        msg.count = 128
        msg.measurements = values
        self.on_message_received(msg)

    def __update_drop_positions(self):
        for e in self.electrodes:
            e.just_moved = False
        for i, e in enumerate(self.electrodes):
            if e.state and e.volume == 0.0:
                for c in e.connections():
                    if is_pullable(c, e):
                        pull_drop(c, e)
                        break

    def __load_board(self, board):
        """Create map of electrode connections from board layout

        Currently this only supports grid electrodes, because it's easier.
        This means other electrodes, such as reservoirs, will be left unconnected
        and unable to move drops on or off. We could infer connections from
        electrodes which are close, although this also raises issues of volume
        because drops can then move between electrodes of different sizes.
        """
        for g in board.layout.grids:
            pins = g['pins']
            for y in range(len(pins)):
                row = pins[y]
                for x in range(len(row)):
                    pin = row[x]
                    if pin is None:
                        continue
                    if x < len(row) - 1:
                        right_pin = row[x+1]
                        if right_pin is None:
                            continue
                        self.electrodes[pin].add_connection(self.electrodes[right_pin])
                    if y < len(pins) - 1:
                        next_row = pins[y+1]
                        if x < len(next_row):
                            below_pin = next_row[x]
                            if below_pin is None:
                                continue
                            self.electrodes[pin].add_connection(self.electrodes[below_pin])

