from .hiddevice import HIDDevice
from .adbdevice import ADBDevice
from .keppalive_thread import KeepaliveThread
from .config import Config

class Ryuo():
    VENDOR_ID = 0x1C75
    PRODUCT_ID = 0x1C76

    def __init__(self):
        self.adb_device = ADBDevice()
        self.config = Config("config.json", self.adb_device)
        self.hid_device = HIDDevice(self.VENDOR_ID, self.PRODUCT_ID)
        self.keepalive_thread = KeepaliveThread(
            self.hid_device,
            interval=self.config.settings.get("keepalive_interval", 1),
            send_system_data=self.config.settings.get("send_system_data", True)
        )
        self.keepalive_thread.start()
        self.apply()

    def apply(self):
        self.hid_device.update_display([self.config.settings.get("media")], brightness=self.config.settings["brightness"])

    def upload(self, media_file):
        self.adb_device.upload_media(media_file)

    def delete(self, media_file):
        self.adb_device.delete_media(media_file)

    def download(self, media_file, local_path):
        self.adb_device.download_media(media_file, local_path)

    def set_brightness(self, brightness):
        self.config.settings["brightness"] = brightness
        self.hid_device.update_display([self.config.settings.get("media")], brightness=self.config.settings["brightness"])
        self.config.save_config()

    def set_media(self, media_file):
        self.config.settings["media"] = media_file
        self.hid_device.update_display([self.config.settings.get("media")], brightness=self.config.settings["brightness"])
        self.config.save_config()

    def get_user_media_files(self):
        user_files, _ = self.adb_device.get_mp4_files()
        return user_files
    
    def get_system_media_files(self):
        _, system_files = self.adb_device.get_mp4_files()
        return system_files
    
    def get_media_files(self):
        user_files, system_files = self.adb_device.get_mp4_files()
        return user_files + system_files