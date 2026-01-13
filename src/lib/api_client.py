import socket
import time
import threading
import requests
from .api import API
import os


class APIClient:
    def __init__(self, host: str = "127.0.0.1", port: int = 55667, start_if_missing: bool = True, timeout: float = 5.0):
        self.host = host
        self.port = port
        self.base = f"http://{host}:{port}"
        self._started_api = False
        if start_if_missing:
            self.ensure_running(timeout=timeout)

    def _port_open(self) -> bool:
        try:
            with socket.create_connection((self.host, self.port), timeout=0.5):
                return True
        except Exception:
            return False

    def ensure_running(self, timeout: float = 5.0) -> None:
        if self._port_open():
            return
        # start API in background thread
        def run_api():
            api = API(host=self.host, port=self.port)
            api.run()

        t = threading.Thread(target=run_api, daemon=True)
        t.start()
        # wait for port
        start = time.time()
        while time.time() - start < timeout:
            if self._port_open():
                self._started_api = True
                return
            time.sleep(0.1)
        raise RuntimeError(f"API did not become available on {self.host}:{self.port} within {timeout}s")

    def is_running(self) -> bool:
        return self._port_open()

    def get_media_files(self):
        r = requests.get(f"{self.base}/list")
        r.raise_for_status()
        return r.json().get("media", [])

    def get_config(self):
        r = requests.get(f"{self.base}/info")
        r.raise_for_status()
        return r.json().get("config", {})

    def upload(self, path: str):
        with open(path, "rb") as fh:
            files = {"file": (path.split(os.sep)[-1], fh, "video/mp4")}
            r = requests.post(f"{self.base}/upload", files=files)
            r.raise_for_status()
            return r.json()

    def download(self, media: str, dest_path: str | None = None, timeout: float = 30.0) -> str:
        # ensure API running
        try:
            self.ensure_running()
        except Exception:
            pass

        url = f"{self.base}/download/{media}"
        r = requests.get(url, stream=True, timeout=timeout)
        r.raise_for_status()

        if dest_path is None:
            dest_path = os.path.join(os.getcwd(), os.path.basename(media))

        with open(dest_path, "wb") as fh:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    fh.write(chunk)

        return dest_path

    def delete(self, media: str):
        r = requests.delete(f"{self.base}/delete/{media}")
        r.raise_for_status()
        return r.json()

    def set_media_and_brightness(self, media: str, brightness: int):
        r = requests.post(f"{self.base}/set/{media}/{brightness}")
        r.raise_for_status()
        return r.json()

    def set_media(self, media: str):
        cfg = self.get_config()
        brightness = cfg.get("brightness", 200)
        return self.set_media_and_brightness(media, brightness)

    def set_brightness(self, brightness: int):
        # prefer direct brightness endpoint
        try:
            r = requests.post(f"{self.base}/brightness/{int(brightness)}")
            r.raise_for_status()
            return r.json()
        except Exception:
            # fallback to set endpoint behavior
            cfg = self.get_config()
            media = cfg.get("media", "") or ""
            if not media:
                return self.set_media_and_brightness("", brightness)
            return self.set_media_and_brightness(media, brightness)
