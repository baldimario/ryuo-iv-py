import time
import json
import struct
from dataclasses import dataclass

@dataclass
class Packet():
    MAGIC: bytes = b'\x5A'
    ESCAPE: bytes = b'\x5B'
    ESCAPED_MAGIC: bytes = b'\x01'
    ESCAPED_ESCAPE: bytes = b'\x02'
    RAW: bytes = bytes()
    LENGTH: bytes = bytes([0x00, 0x00])
    PAYLOAD: bytes = bytes()
    CHECKSUM: bytes = bytes([0x00])
    HID_REPORT_ID: bytes = bytes([0x00])

    def __init__(self, raw: bytes = bytes()):
        if raw:
            self.parse_packet(raw)

    @staticmethod
    def from_bytes(raw: bytes):
        # remove from raw all the \x00 leading bytes after the last MAGIC byte
        last_magic_index = raw.rfind(Packet.MAGIC)
        if last_magic_index != -1:
            raw = raw[:last_magic_index+1]

        packet = Packet()
        packet.parse_packet(raw)
        return packet
    
    def to_bytes(self):
        return self.build_packet(self.PAYLOAD)
        
    def checksum(self, data: bytes):
        s = 0
        for b in data:
            s = (s + b) & 0xFF
        return bytes([s])

    def escape(self, data: bytes):
        out = bytearray()
        for b in data:
            if b == self.MAGIC[0]:
                out += bytes([self.ESCAPE[0], self.ESCAPED_MAGIC[0]])
            elif b == self.ESCAPE[0]:
                out += bytes([self.ESCAPE[0], self.ESCAPED_ESCAPE[0]])
            else:
                out.append(b)
        return bytes(out)

    def unescape(self, data: bytes):
        out = bytearray()
        i = 0
        while i < len(data):
            b = data[i]
            if b == self.ESCAPE[0]:
                i += 1
                b2 = data[i]
                if b2 == self.ESCAPED_MAGIC[0]:
                    out.append(self.MAGIC[0])
                elif b2 == self.ESCAPED_ESCAPE[0]:
                    out.append(self.ESCAPE[0])
                else:
                    print(f"Invalid escape sequence: {b2}")
                    raise ValueError("Invalid escape sequence")
            else:
                out.append(b)
            i += 1
        return bytes(out)

    def parse_packet(self, raw: bytes):
        if raw[0] != self.MAGIC[0] or raw[-1] != self.MAGIC[0]:
            raise ValueError("Invalid packet framing")
        
        unescaped = self.unescape(raw[1:-1])
        body = unescaped[:-1]
        received_checksum = unescaped[-1:]
        
        calculated_checksum = self.checksum(body)
        
        if received_checksum != calculated_checksum:
            raise ValueError("CRC mismatch")
        
        length = struct.unpack(">H", body[:2])[0]
        payload = body[2:length]

        self.RAW = raw
        self.LENGTH = body[:2]
        self.PAYLOAD = payload
        self.CHECKSUM = received_checksum

        return self
    
    @staticmethod
    def create_http_header(packet_method: str,sequence_number: int, content_length: int):
        timestamp = int(time.time() * 1000)
        return (
            f"{packet_method} 1\r\n"
            f"SeqNumber={sequence_number}\r\n"
            f"Date={timestamp}\r\n"
            f"ContentType=json\r\n"
            f"ContentLength={content_length}\r\n"
            f"\r\n"
        )
    
    def get_payload_header(self):
        return self.PAYLOAD.split(b'\r\n\r\n', maxsplit=1)[0]
    
    def get_payload_body(self):
        parts = self.PAYLOAD.split(b'\r\n\r\n', maxsplit=1)
        if len(parts) > 1:
            return parts[1]
        return b''
    
    def build_from_dict(self, data: dict):
        json_str = json.dumps(data)
        return self.build_from_string(json_str)
    
    @staticmethod
    def build_from_string(packet_method: str, json_str: str, sequence_number: int = 0):
        packet = Packet()
        payload = json_str.encode('utf-8')
        header = Packet.create_http_header(packet_method, sequence_number=sequence_number, content_length=len(payload))
        payload = header.encode('utf-8') + payload
        packet.PAYLOAD = payload
        packet.LENGTH = struct.pack(">H", len(payload) + 2)
        packet.CHECKSUM = packet.checksum(packet.LENGTH + payload)
        packet.RAW = packet.build_packet()
        return packet
    
    @staticmethod
    def build_from_payload(payload: bytes):
        packet = Packet()
        packet.PAYLOAD = payload
        packet.LENGTH = struct.pack(">H", len(payload) + 2)
        packet.CHECKSUM = packet.checksum(packet.LENGTH + payload)
        packet.RAW = packet.build_packet(payload)
        return packet
    
    def build_packet(self):
        body = self.LENGTH + self.PAYLOAD
        unframed = body + self.CHECKSUM
        escaped = self.escape(unframed)
        framed = self.MAGIC + escaped + self.MAGIC
        return self.HID_REPORT_ID + framed

    def get_bytes(self):
        return self.RAW