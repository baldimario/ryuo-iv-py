
import threading
import time

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
                    self.device.send_system_state()
                
                self.seq_number += 1
                
            except Exception as e:
                print(f"[Keepalive] Error: {e}")
                break
        print("[Keepalive Thread] Terminated")
    
    def stop(self):
        self.running = False