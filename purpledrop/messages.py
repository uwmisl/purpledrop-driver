import struct
from typing import Optional, Sequence, Type

class PurpleDropMessage(object):
    @classmethod
    def predictSize(cls, buf: bytearray) -> int:
        if len(buf) == 0:
            return 0
        msg_class = cls.findClassById(buf[0])
        if msg_class is None:
            return -1
        return msg_class.predictSize(buf)

    @classmethod
    def findClassById(cls, id: int) -> Optional[Type]:
        for sub_type in cls.__subclasses__():
            if getattr(sub_type, 'ID') == id:
                return sub_type
        return None

    @classmethod
    def from_bytes(cls, buf: bytearray) -> object:
        if len(buf) == 0:
            return None
        msg_class = cls.findClassById(buf[0])
        if msg_class is None:
            return None
        # TODO: Handle errors here. There's no guarantee that the frame we receive
        # is proper.
        return msg_class(buf)

class ActiveCapacitanceMsg(PurpleDropMessage):
    ID = 3

    def __init__(self, fill_data: Optional[bytearray]=None):
        if fill_data is not None:
            self.fill(fill_data)
        else:
            self.baseline = 0
            self.measurement = 0

    @staticmethod
    def predictSize(buf: bytearray) -> int:
        return 5

    def fill(self, fill_data):
        self.baseline, self.measurement = struct.unpack_from("<HH", fill_data, 1)

class BulkCapacitanceMsg(PurpleDropMessage):
    ID = 2

    def __init__(self, fill_data: Optional[bytearray]=None):
        if fill_data is not None:
            self.fill(fill_data)
        else:
            self.start_index = 0
            self.count = 0
            self.measurements: Sequence[int] = []

    @staticmethod
    def predictSize(buf: bytearray) -> int:
        if len(buf) < 3:
            return 0
        else:
            return buf[2] * 2 + 3

    def fill(self, buf):
        if len(buf) < 3:
            raise ValueError("Need at least 3 bytes to parse a BulkCapacitanceMsg")
        self.start_index, self.count = struct.unpack_from("<BB", buf, 1)
        if len(buf) < self.count * 2 + 3:
            raise ValueError(f"Not enough data for BulkCapacitanceMsg with count {self.count}")
        self.measurements = struct.unpack_from("<" + "H" * self.count, buf, 3)

class CommandAckMsg(PurpleDropMessage):
    ID = 4

    def __init__(self, fill_data: Optional[bytearray]=None):
        if fill_data is not None:
            self.fill(fill_data)
        else:
            self.acked_id = 0

    @staticmethod
    def predictSize(buf: bytearray) -> int:
        return 2

    def fill(self, buf):
        if len(buf) < 2:
            raise ValueError("Require at least 2 bytes to parse a CommandAckMsg")
        self.acked_id = buf[1]

class ElectrodeEnableMsg(PurpleDropMessage):
    ID = 0

    def __init__(self, fill_data: Optional[bytearray]=None):
        self.values = [0] * 16

    @staticmethod
    def predictSize(buf: bytearray) -> int:
        return 16

    def to_bytes(self):
        return struct.pack("<B" + "B" * len(self.values),
            *([self.ID] + self.values))

class SetParameterMsg(PurpleDropMessage):
    ID = 6

    def __init__(self, fill_data: Optional[bytearray]=None):
        if fill_data is not None:
            if len(fill_data) < 10:
                raise RuntimeError("Need at least 10 bytes to fill a SetParameterMsg")
            self._buf = fill_data
        else:
            self._buf = bytearray([self.ID] + [0]*9)

    @staticmethod
    def predictSize(buf: bytearray) -> int:
        return 10

    def param_idx(self) -> int:
        return struct.unpack_from("<I", self._buf, 1)[0]

    def set_param_idx(self, value: int):
        struct.pack_into("<I", self._buf, 1, value)

    def param_value_float(self) -> float:
        return struct.unpack_from("<f", self._buf, 5)[0]

    def set_param_value_float(self, value: float):
        struct.pack_into("<f", self._buf, 5, value)

    def param_value_int(self) -> int:
        return struct.unpack_from("<i", self._buf, 5)[0]

    def set_param_value_int(self, value: int):
        struct.pack_into("<i", self._buf, 5, value)

    def write_flag(self) -> bool:
        if self._buf[9] == 0:
            return False
        else:
            return True

    def set_write_flag(self, flag: bool):
        if flag:
            self._buf[9] = 1
        else:
            self._buf[9] = 0

    def fill(self, fill_data: bytearray):
        self._buf = fill_data

    def to_bytes(self) -> bytearray:
        return self._buf

    def __str__(self):
        return "SetParameterMsg(param_idx=%d, param_value=%d, write_flag=%d)" % \
            (self.param_idx(), self.param_value_int(), self.write_flag())

class SetPwmMsg(PurpleDropMessage):
    ID = 9

    def __init__(self, fill_data: Optional[bytearray]=None):
        if fill_data is not None:
            self.fill(fill_data)
        else:
            self.chan = 0
            self.duty_cycle = 0.0

    def fill(self, buf: bytes):
        raise RuntimeError("Not implemented")

    def to_bytes(self) -> bytes:
        return struct.pack("<BBH", self.ID, self.chan, int(self.duty_cycle * 4096))

class TemperatureMsg(PurpleDropMessage):
    ID = 7

    def __init__(self, fill_data: Optional[bytearray]=None):
        if fill_data is not None:
            self.fill(fill_data)
        else:
            self.measurements: Sequence[int] = []

    @staticmethod
    def predictSize(buf: bytearray) -> int:
        if(len(buf) < 2):
            return 0
        else:
            return buf[1]*2 + 2

    def fill(self, buf: bytearray):
        if len(buf) < 2:
            raise ValueError("Insufficient bytes for TemperatureMsg")
        count = buf[1]
        if len(buf) < count * 2 + 2:
            raise ValueError("Insufficient bytes for TemperatureMsg")

        self.measurements = struct.unpack_from("<" + "h"*count, buf, 2)

    def to_bytes(self) -> bytes:
        count = len(self.measurements)
        return struct.pack("<BB"+"h"*count, [self.ID, count] + self.measurements)

    def __str__(self):
        return "TemperatureMsg(measurements=%s)" % str(self.measurements)

class HvRegulatorMsg(PurpleDropMessage):
    ID = 8

    def __init__(self, fill_data: Optional[bytearray]=None):
        if fill_data is not None:
            self.fill(fill_data)
        else:
            self.voltage = 0.0
            self.v_target_out = 0

    @staticmethod
    def predictSize(buf: bytearray) -> int:
        return 7
        if(len(buf) < 2):
            return 0
        else:
            return buf[1]*2 + 2

    def fill(self, buf: bytearray):
        if len(buf) < 7:
            raise ValueError("Insufficient bytes for HvRegulatorMsg")

        self.voltage = struct.unpack_from("<f" , buf, 1)[0]
        self.v_target_out = struct.unpack_from("<h", buf, 5)[0]

    def to_bytes(self) -> bytearray:
        return struct.pack("<Bfh", [self.ID, self.voltage, self.v_target_out])

    def __str__(self):
        return "HvRegulatorMsg(voltage=%0.1f, v_target_out=%d)" % \
            (self.voltage, self.v_target_out)