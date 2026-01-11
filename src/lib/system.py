import psutil
import time

class System:
    @staticmethod
    def get_system_data():
        """Raccoglie i dati di sistema da inviare al display"""
        try:
            # cpu
            cpu_percent = psutil.cpu_percent(interval=0.1)
            cpu_freq = psutil.cpu_freq()
            cpu_temp = 0
            try:
                temps = psutil.sensors_temperatures()
                if 'coretemp' in temps:
                    cpu_temp = int(temps['coretemp'][0].current)
            except:
                cpu_temp = 33  # Default
            
            # memory
            mem = psutil.virtual_memory()
            
            # gpu (mock for now)
            gpu_data = {
                "hasDedicated": True,
                "load": 5,
                "temperature": 40,
                "fan": 0,
                "speed": 892,
                "power": 18,
                "voltage": 0.745
            }
            
            # disk
            disk = psutil.disk_usage('/')
            
            # network
            net = psutil.net_io_counters()
            
            # fans (mock for now)
            fans = [
                {"onBoard": True, "name": "CPU", "value": 2149},
                {"onBoard": True, "name": "CPU_OPT", "value": 964},
                {"onBoard": True, "name": "System 1", "value": 581},
                {"onBoard": True, "name": "System 2", "value": 835},
                {"onBoard": True, "name": "System 3", "value": 747}
            ]
            
            data = {
                "network": {
                    "upload": int(net.bytes_sent / 1024 / 1024),  # MB
                    "download": int(net.bytes_recv / 1024 / 1024)  # MB
                },
                "memory": {
                    "total": int(mem.total / 1024 / 1024),  # MB
                    "used": int(mem.used / 1024 / 1024),  # MB
                    "load": int(mem.percent),
                    "temperature": 0,
                    "speed": 2266
                },
                "cpu": {
                    "load": int(cpu_percent),
                    "temperature": cpu_temp,
                    "temperaturePackage": 0,
                    "speedAverage": int(cpu_freq.current) if cpu_freq else 2875,
                    "power": 9,
                    "voltage": 0.886,
                    "usage": int(cpu_percent)
                },
                "gpu": gpu_data,
                "disk": {
                    "total": int(disk.total / 1024 / 1024 / 1024),  # GB
                    "used": int(disk.used / 1024 / 1024 / 1024),  # GB
                    "load": int(disk.percent),
                    "activity": 0,
                    "temperature": 0,
                    "readSpeed": 0,
                    "writeSpeed": 0
                },
                "fans": fans,
                "motherboard": {
                    "temperature": 32,
                    "chipsetTemperature": 44
                },
                "timestamp": int(time.time() * 1000)
            }
            
            return data
        except Exception as e:
            print(f"Errore nella raccolta dati di sistema: {e}")
            return None