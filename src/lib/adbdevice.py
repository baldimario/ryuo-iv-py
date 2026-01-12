from datetime import datetime
import subprocess
import os

class ADBDevice():
    ADB_PATH = "adb"  # Assumes adb is in PATH
    USER_FILE_PATH = "/sdcard/pcMedia"
    SYSTEM_FILE_PATH = "/sdcard/pcMediaPreset"

    def __init__(self):
        self.check_adb_availability()
        self.check_android_app_running()

    def check_adb_availability(self):
        result = subprocess.run([self.ADB_PATH, "version"], capture_output=True, text=True)
        if result.returncode != 0:
            raise EnvironmentError("ADB not found or not working properly.")
        
    def check_android_app_running(self):
        cmd = [self.ADB_PATH, "shell", "pidof com.baiyi.homeui.hshomeui"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        
        if not result.stdout.strip():
            raise RuntimeError("Target Android app is not running.")

    def get_mp4_files(self):
        try:
            user_files = []
            preset_files = []
            
            # User directory mp4 list (/sdcard/pcMedia)
            cmd = [self.ADB_PATH, "shell", f"find {self.USER_FILE_PATH} -type f -name '*.mp4' 2>/dev/null"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0 and result.stdout.strip():
                files = [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
                user_files = [os.path.basename(f) for f in files]
            
            # Preset directory mp4 list (/sdcard/pcMediaPreset - read-only)
            preset_path = "/sdcard/pcMediaPreset"
            cmd = [self.ADB_PATH, "shell", f"find {self.SYSTEM_FILE_PATH} -type f -name '*.mp4' 2>/dev/null"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0 and result.stdout.strip():
                files = [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
                preset_files = [os.path.basename(f) for f in files]
            
            return user_files, preset_files
        
        except subprocess.TimeoutExpired:
            print("Timeout executing adb command")
            return [], []
        except Exception as e:
            print(f"Error: {e}")
            return [], []
            
    def upload_media(self, local_path, remote_filename=None):
        try:
            if not os.path.exists(local_path):
                print(f"Error: local file not found: {local_path}")
                return False
            
            if remote_filename is None:
                now = datetime.now()
                remote_filename = now.strftime("%Y-%m-%d_%H-%M-%S-") + f"{now.microsecond // 1000:03d}.mp4"
            
            remote_path = f"{self.USER_FILE_PATH}/{remote_filename}"
            
            cmd = [self.ADB_PATH, "push", local_path, remote_path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0:
                return remote_filename
            else:
                print(result.stderr)
                return None
        except subprocess.TimeoutExpired:
            print("Timeout executing adb command")
            return None
        except Exception as e:
            print(f"Error: {e}")
            return None
            
    def download_media(self, media_file, local_path):
        # download media from user or preset directory
        user_files, preset_files = self.get_mp4_files()

        if media_file in user_files:
            remote_path = f"{self.USER_FILE_PATH}/{media_file}"
        elif media_file in preset_files:
            remote_path = f"{self.SYSTEM_FILE_PATH}/{media_file}"
        else:
            print("File not found on device.")
            return False
        
        try:
            cmd = [self.ADB_PATH, "pull", remote_path, local_path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0:
                return True
            else:
                print(result.stderr)
                return False
        except subprocess.TimeoutExpired:
            print("Timeout executing adb command")
            return None
        except Exception as e:
            raise e
        
    def delete_media(self, media_file):
        # Only user files can be deleted, preset files are read-only
        user_files, preset_files = self.get_mp4_files()
        
        if not user_files:
            print("No user media files found to delete.")
            return False
        
        if media_file not in user_files:
            print("File not found in user media files.")
            return False
        

        remote_path = f"{self.USER_FILE_PATH}/{media_file}"
            
        try:
            cmd = [self.ADB_PATH, "shell", f"rm {remote_path}"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                return True
            else:
                return False
        except subprocess.TimeoutExpired:
            print("Timeout executing adb command")
            return None
        except Exception as e:
            raise e
    