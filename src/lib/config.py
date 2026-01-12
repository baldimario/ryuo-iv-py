class Config():
    def __init__(self, file_path, adb_device=None):
        self.file_path = file_path or "config.json"
        self.adb_device = adb_device
        self.settings = {}
        self.load_config()

    def default_config(self):
        media = 'RYUO_IV_HW_Info_01.mp4'
        if self.adb_device:
            user_media_files, system_media_files = self.adb_device.get_mp4_files()
            if system_media_files:
                media = system_media_files[0]

        return {
            "brightness": 200,
            "media": media,
            "keepalive_interval": 1,
            "send_system_data": True
        }
    
    def load_config(self):
        default_settings = self.default_config()

        try:
            with open(self.file_path, 'r') as f:
                import json
                self.settings = json.load(f)
        except FileNotFoundError:
            self.settings = default_settings
        except json.JSONDecodeError:
            print("Error: Invalid JSON format in config file.")
            self.settings = default_settings

        self.settings = {**default_settings, **self.settings}

        self.save_config()

    def save_config(self):
        try:
            with open(self.file_path, 'w') as f:
                import json
                json.dump(self.settings, f, indent=4)
        except Exception as e:
            print(f"Error saving config: {e}")