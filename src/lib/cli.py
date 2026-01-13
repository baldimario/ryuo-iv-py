from .ryuo import Ryuo
from .api_client import APIClient
from .tui import TUI
from .api import API
import argparse
import sys
import time
from typing import List, Optional


class CLI:
    """Command-line interface wrapper for Ryuo operations using the HTTP API."""

    def __init__(self, host: str = "127.0.0.1", port: int = 55667):
        # APIClient will start the API server if necessary (within a timeout)
        self.client = APIClient(host=host, port=port)

    def list_media(self) -> int:
        try:
            media = self.client.get_media_files()
            cfg = self.client.get_config()
            current = cfg.get("media", "")
            if not media:
                print("No media found on device")
                return 0
            for m in media:
                mark = "*" if m == current else " "
                print(f"{mark} {m}")
            return 0
        except Exception as e:
            print(f"Error listing media: {e}")
            return 2

    def info(self) -> int:
        try:
            cfg = self.client.get_config()
            print("Current configuration:")
            print(f" - Media: {cfg.get('media', '')}")
            print(f" - Brightness: {cfg.get('brightness', '')}")
            print(f" - Keepalive interval: {cfg.get('keepalive_interval', '')}")
            print(f" - Send system data: {cfg.get('send_system_data', '')}")
            return 0
        except Exception as e:
            print(f"Error reading config: {e}")
            return 2

    def upload(self, path: str) -> int:
        if not path:
            print("No path provided for upload")
            return 2
        if not path.lower().endswith(".mp4"):
            print("Only .mp4 files are supported for upload")
            return 2
        try:
            self.client.upload(path)
            print(f"Uploaded: {path}")
            return 0
        except Exception as e:
            print(f"Upload failed: {e}")
            return 3

    def delete_media(self, media: str) -> int:
        if not media:
            print("No media specified for deletion")
            return 2
        try:
            media_files = self.client.get_media_files()
            if media not in media_files:
                print(f"Media '{media}' not found on device")
                return 2
            self.client.delete(media)
            print(f"Deleted: {media}")
            try:
                cfg = self.client.get_config()
                if cfg.get("media") == media:
                    # clear active media if it was the deleted one
                    self.client.set_media_and_brightness("", cfg.get("brightness", 200))
            except Exception:
                pass
            return 0
        except Exception as e:
            print(f"Delete failed: {e}")
            return 3

    def set_media_and_brightness(self, media: str, brightness: int) -> int:
        time.sleep(1)
        try:
            brightness = int(brightness)
        except Exception:
            print("Brightness must be an integer (0-255)")
            return 2
        if brightness < 0 or brightness > 255:
            print("Brightness must be between 0 and 255")
            return 2

        try:
            media_files = self.client.get_media_files()
            if media not in media_files:
                print(f"Media '{media}' not found on device. Available files:")
                for m in media_files:
                    print(f" - {m}")
                return 2

            self.client.set_media_and_brightness(media, brightness)
            print(f"Set media: {media} and brightness: {brightness}")
            return 0
        except Exception as e:
            print(f"Failed to set media/brightness: {e}")
            return 3

    def download_media(self, media: str, out_path: Optional[str] = None) -> int:
        if not media:
            print("No media specified for download")
            return 2
        try:
            dest = self.client.download(media, dest_path=out_path)
            print(f"Downloaded: {dest}")
            return 0
        except Exception as e:
            print(f"Download failed: {e}")
            return 3

    def set_brightness(self, brightness: int) -> int:
        try:
            brightness = int(brightness)
        except Exception:
            print("Brightness must be an integer (0-255)")
            return 2
        if brightness < 0 or brightness > 255:
            print("Brightness must be between 0 and 255")
            return 2
        try:
            self.client.set_brightness(brightness)
            print(f"Set brightness: {brightness}")
            return 0
        except Exception as e:
            print(f"Failed to set brightness: {e}")
            return 3

    def loop_keepalive(self) -> int:
        print("Entering keepalive loop. Ctrl-C to exit.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("Exiting keepalive loop")
            return 0
        except Exception as e:
            print(f"Keepalive loop error: {e}")
            return 3

    def api_server(self) -> int:
        host = self.client.host
        port = self.client.port

        try:
            if self.client._port_open():
                print(f"API already running at {host}:{port}; entering monitor mode (Ctrl-C to exit)")
                try:
                    while True:
                        time.sleep(1)
                        if not self.client._port_open():
                            print("API server appears down — attempting to start it now")
                            try:
                                api = API(host=host, port=port)
                                api.run()
                            except Exception as e:
                                print(f"Failed to start API: {e}; retrying in 2s")
                                time.sleep(2)
                except KeyboardInterrupt:
                    print("Exiting monitor mode")
                    return 0
            else:
                print("Starting API server (blocking)")
                api = API(host=host, port=port)
                api.run()
                return 0
        except KeyboardInterrupt:
            print("Stopping API server")
            return 0
        except Exception as e:
            print(f"API server error: {e}")
            return 3

    def run(self, argv: Optional[List[str]] = None) -> int:
        argv = argv if argv is not None else sys.argv[1:]
        parser = argparse.ArgumentParser(prog="ryuo-cli", description="Ryuo device automation CLI")

        parser.add_argument("-u", "--upload", metavar="LOCAL_PATH", help="Upload local .mp4 file to device")
        parser.add_argument("-l", "--list", action="store_true", help="List media on device")
        parser.add_argument("-i", "--info", action="store_true", help="Show current configuration info")
        parser.add_argument("-s", "--set", nargs='+', metavar=("MEDIA", "BRIGHTNESS"), help="Set media on device and optional brightness (0-255)")
        parser.add_argument("-L", "--loop", action="store_true", help="Run an infinite keepalive loop")
        parser.add_argument("-b", "--brightness", type=int, metavar="BRIGHTNESS", help="Set brightness only (0-255)")
        parser.add_argument("-d", "--daemon", action="store_true", help="Start daemon (API server, blocking)")
        parser.add_argument("-t", "--tui", action="store_true", help="Start the textual TUI")
        parser.add_argument("-D", "--delete", metavar="MEDIA", help="Delete media from device")
        parser.add_argument("-g", "--download", nargs='+', metavar=("MEDIA", "OUT_PATH"), help="Download media from device; optional OUT_PATH to save to")

        args = parser.parse_args(argv)

        cli = CLI()

        if args.list:
            return cli.list_media()

        if args.info:
            return cli.info()

        if args.upload:
            return cli.upload(args.upload)

        if args.set:
            media = args.set[0]
            brightness = args.set[1] if len(args.set) > 1 else None
            if brightness is None:
                # apply media using existing/config brightness
                try:
                    cli.client.set_media(media)
                    print(f"Set media: {media}")
                    return 0
                except Exception as e:
                    print(f"Failed to set media: {e}")
                    return 3
            else:
                return cli.set_media_and_brightness(media, brightness)

        if args.loop:
            return cli.loop_keepalive()

        if args.daemon:
            return cli.api_server()

        if args.delete:
            return cli.delete_media(args.delete)

        if args.brightness is not None:
            return cli.set_brightness(args.brightness)

        if args.download:
            # args.download may be ['media.mp4'] or ['media.mp4', 'out/path.mp4']
            if isinstance(args.download, list):
                media = args.download[0]
                out = args.download[1] if len(args.download) > 1 else None
            else:
                media = args.download
                out = None
            return cli.download_media(media, out)

        if args.tui:
            try:
                tui = TUI()
                tui.run()
                return 0
            except Exception as e:
                print(f"TUI failed: {e}")
                return 3

        parser.print_help()
        return 0


def main(argv: Optional[List[str]] = None) -> int:
    return CLI().run(argv)


if __name__ == "__main__":
    raise SystemExit(main())

