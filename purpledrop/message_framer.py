"""Purple drop messages are transmitted using an encoding similar to that used
by HDLC for asynchronous framing. 

The framing serves to divide a stream of bytes into packets (messages).

The framing doesn't care about the content of the messages, however in order
to minimize the amount of bytes lost in the event of an error, the framer
depends on knowledge of the packet lengths, which is provided in the form of 
the `size_predictor` function provided when creating a MessageFramer. This
function will inspect partial contents of a message and determine if its valid
and how many bytes are required to complete it -- i.e. the size_predictor
knows where to find a message ID, which message IDs are valid ones, and how to 
determine the length of a packet (which may be a function of the packet contents, 
for variable length messages).
"""
from typing import Callable, Iterator, Optional, Tuple

def calc_checksum(data: bytes) -> Tuple[int, int]:
    a = 0
    b = 0
    for x in data:
        a = (a + x) % 256
        b = (b + a) % 256

    return (a, b)

def serialize(input: bytes) -> bytes:
    """Convert a message into a framed message ready to be sent with packet 
    start, control code escaping, and checksum.
    """
    chk_a, chk_b = calc_checksum(input)
    out = [0x7e]
    for b in input:
        if b == 0x7d or b == 0x7e:
            out.append(0x7d)
            out.append(b ^ 0x20)
        else:
            out.append(b)
    
    out.append(chk_a)
    out.append(chk_b)
    return bytes(out)

class MessageFramer(object):
    """Class for framing an incoming stream of bytes into messages
    """
    def __init__(self, size_predictor: Callable[[bytes], int]):
        self._buffer = b""
        self._size_predictor = size_predictor
        self._escaping = False
        self._parsing = False

    def parse(self, bytes: bytearray) -> Iterator[bytes]:
        """Parse an array of bytes, and yield any messages completed

        Example:
            newdata = read_data_from_somewhere() 
            for packet in parser.parse(newdata):
                HandleNewMessage(packet)
        """
        for b in bytes:
            msg = self.parse_byte(b)
            if msg is not None:
                yield msg

    def parse_byte(self, b: int) -> Optional[bytes]:
        """Parse a single new byte of data

        If the new byte completes a packet, the unserialized packet is returned.
        Otherwise, None is returned.
        """
        if self._escaping:
            b = b ^ 0x20
            self._escaping = False
        elif b == 0x7d:
            # Escape control character
            self._escaping = True
            return None
        elif b == 0x7e:
            # start of frame
            self.reset()
            self._parsing = True
            return None

        if not self._parsing: 
            return None

        self._buffer += bytes([b])

        expected_size = self._size_predictor(self._buffer)
        if expected_size == -1:
            print("Got invalid message size")
            # Not a valid message
            self.reset()
        elif expected_size > 0 and len(self._buffer) >= expected_size + 2:
            msg_without_checksum = self._buffer[:-2]
            calc_a, calc_b = calc_checksum(msg_without_checksum)
            if calc_a == self._buffer[-2] and calc_b == self._buffer[-1]:
                self.reset()
                return msg_without_checksum
            else:
                print(f"Checksum mismatch (id: {self._buffer[0]})")
                print(f"buf: {[hex(a) for a in self._buffer]}")
                self.reset()
        
        return None

    def reset(self):
        self._escaping = False
        self._parsing = False
        self._buffer = b""


