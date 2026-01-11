import hid
import time
from .packet import Packet
from .system import System
import json

class HIDDevice():
    def __init__(self, vendor_id: int, product_id: int, keepalive_interval: int = 1):
        self.vendor_id = vendor_id
        self.product_id = product_id
        self.keepalive_interval = keepalive_interval
        self.sequence_number = 0
        self.connect()

    def connect(self):
        try:
            self.device = hid.device()
            self.device.open(self.vendor_id, self.product_id)
            return self.device
        except Exception as e:
            print(f"Error connecting to device VID={hex(self.vendor_id)}, PID={hex(self.product_id)}: {e}")
            return None
        
    def read(self, size: int = 1024, timeout: int = 1000) -> bytes:
        try:
            data = self.device.read(size, timeout)
            return bytes(data)
        except Exception as e:
            print(f"Error reading from device: {e}")
            return bytes()
        
    def write(self, data: bytes) -> int:
        try:
            bytes_written = self.device.write(data)
            self.sequence_number += 1
            return bytes_written
        except Exception as e:
            print(f"Error writing to device: {e}")
            return 0
        
    def send_and_receive(self, packet: bytes) -> bytes:
        try:
            self.write(packet)
            time.sleep(0.1)
            response = self.read()
            return response
        except Exception as e:
            print(f"Error in send_and_receive: {e}")
            return bytes()
        
    def send_keepalive(self):
        packet = Packet.build_from_string("POST conn", "", self.sequence_number).get_bytes()

        try:
            self.write(packet)

            time.sleep(self.keepalive_interval)
            
            for attempt in range(2):
                response = self.read()
                
                if response:
                    response_bytes = bytes(response)
                    
                    try:
                        parsed = Packet.from_bytes(response_bytes)
                        return parsed
                    except Exception as e:
                        print(f"[Keepalive] Received response but failed to parse: {e}")
                        print(f"[Keepalive] Raw content: {response_bytes[:100]}")
                        return response_bytes
                else:
                    if attempt == 0:
                        print(f"[Keepalive] No response on attempt {attempt + 1}, retrying...")
            
            print("[Keepalive] No response received, but packet sent successfully")
            print("[Keepalive] The device may send status asynchronously")
            return None
            
        except Exception as e:
            print(f"[Keepalive] Error: {e}")
            return None

    def send_system_state(self):
        try:
            system_data = System.get_system_data()
            if not system_data:
                return False
            
            json_payload = json.dumps(system_data, separators=(',', ':'))

            packet = Packet.build_from_string("STATE all", json_payload, self.sequence_number).get_bytes()
            self.write(packet)
            return True
            
        except Exception as e:
            print(f"[System State] Error: {e}")
            return False
        
    def update_display(self, media_files, brightness=200):
        config_data = {
            "temperature": "Celsius",
            "waterBlockScreen": {
                "enable": True,
                "displayInSleep": True,
                "brightness": brightness,
                "id": {
                    "id": "Customization",
                    "screenMode": "Full Screen",
                    "playMode": "Single",
                    "media": media_files,
                    "settings": {
                        "titleColor": "#E5252B",
                        "contentColor": "#FFFFFF",
                        "filter": {
                            "value": None,
                            "opacity": 100
                        },
                        "badges": []
                    },
                    "sysinfoDisplay": [
                        "CPU Temperature",
                        "GPU Temperature",
                        "CPU Usage",
                        "Date&Time",
                        "GPU Usage",
                        "Motherboard Temperature"
                    ],
                    "timeZone": "Europe/Rome"
                }
            },
            "spec": {
                "cpu": "Custom PC",
                "gpu": "Custom GPU"
            }
        }
        
        json_payload = json.dumps(config_data, separators=(',', ':'))
        packet = Packet.build_from_string("POST config", json_payload, self.sequence_number).get_bytes()
        return self.send_and_receive(packet)
    