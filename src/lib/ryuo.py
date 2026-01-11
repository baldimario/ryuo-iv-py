from .packet import Packet
import time
import threading
from .hiddevice import HIDDevice
from .adbdevice import ADBDevice
from .system import System

class Ryuo():
    VENDOR_ID = 0x1C75
    PRODUCT_ID = 0x1C76

    def __init__(self):
        self.brightness = 200
        self.adb_device = ADBDevice()
        self.hid_device = HIDDevice(self.VENDOR_ID, self.PRODUCT_ID)
        keepalive_thread = KeepaliveThread(self.hid_device, interval=1)
        keepalive_thread.start()

    def run(self):
        user_media_files, system_media_files = self.adb_device.get_mp4_files()
        self.hid_device.update_display([system_media_files[0]], brightness=self.brightness)

        while True:
            time.sleep(5)


class KeepaliveThread(threading.Thread):
    def __init__(self, hid_device, interval=1, send_system_data=True):
        super().__init__()
        self.device = hid_device
        self.interval = interval
        self.running = True
        self.daemon = True
        self.send_system_data = send_system_data
        self.seq_number = 0
    
    def run(self):
        while self.running:
            try:
                time.sleep(self.interval)
                if not self.running:
                    break
                
                self.device.send_keepalive()
                
                if self.send_system_data:
                    time.sleep(0.1)
                    self.device.send_system_state()
                
                self.seq_number += 1
                
            except Exception as e:
                print(f"[Keepalive] Error: {e}")
                break
        print("[Keepalive Thread] Terminated")
    
    def stop(self):
        self.running = False