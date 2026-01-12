from .ryuo import Ryuo
from .tui import TUI
from .api import API
import argparse
import sys
import time



class CLI:
    """Command-line interface wrapper for Ryuo operations."""

    def __init__(self):
        pass

    def list_media(self) -> int:
        self.ryuo = Ryuo()
        try:
            media = self.ryuo.get_media_files()
            current = self.ryuo.config.settings.get("media", "")
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
        """Print current configuration and device info."""
        try:
            cfg = self.ryuo.config.settings
            print("Current configuration:")
            print(f" - Media: {cfg.get('media', '')}")
            print(f" - Brightness: {cfg.get('brightness', '')}")
            print(f" - Keepalive interval: {cfg.get('keepalive_interval', '')}")
            print(f" - Send system data: {cfg.get('send_system_data', '')}")
            print(f" - Vendor ID: {hex(self.ryuo.VENDOR_ID)}")
            print(f" - Product ID: {hex(self.ryuo.PRODUCT_ID)}")
            return 0
        except Exception as e:
            print(f"Error reading config: {e}")
            return 2

    def upload(self, path: str) -> int:
        self.ryuo = Ryuo()
        if not path:
            print("No path provided for upload")
            return 2
        if not path.lower().endswith(".mp4"):
            print("Only .mp4 files are supported for upload")
            return 2
        try:
            self.ryuo.upload(path)
            print(f"Uploaded: {path}")
            return 0
        except Exception as e:
            print(f"Upload failed: {e}")
            return 3

    def delete_media(self, media: str) -> int:
        self.ryuo = Ryuo()
        if not media:
            print("No media specified for deletion")
            return 2
        try:
            media_files = self.ryuo.get_media_files()
            if media not in media_files:
                print(f"Media '{media}' not found on device")
                return 2
            self.ryuo.delete(media)
            print(f"Deleted: {media}")
            # if deleted media was the current one, clear it on device/config
            try:
                if self.ryuo.config.settings.get("media") == media:
                    self.ryuo.set_media("")
            except Exception:
                pass
            return 0
        except Exception as e:
            print(f"Delete failed: {e}")
            return 3

    def set_media_and_brightness(self, media: str, brightness: int) -> int:
        self.ryuo = Ryuo()
        time.sleep(1)  # slight delay to ensure previous operations are settled
        try:
            brightness = int(brightness)
        except Exception:
            print("Brightness must be an integer (0-255)")
            return 2
        if brightness < 0 or brightness > 255:
            print("Brightness must be between 0 and 255")
            return 2

        try:
            media_files = self.ryuo.get_media_files()
            if media not in media_files:
                print(f"Media '{media}' not found on device. Available files:")
                for m in media_files:
                    print(f" - {m}")
                return 2

            self.ryuo.set_media(media)
            self.ryuo.set_brightness(brightness)
            try:
                self.ryuo.config.save_config()
            except Exception:
                pass
            print(f"Set media: {media} and brightness: {brightness}")
            return 0
        except Exception as e:
            print(f"Failed to set media/brightness: {e}")
            return 3

    def loop_keepalive(self) -> int:
        self.ryuo = Ryuo()
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
        print("API server placeholder - not implemented yet")
        try:
            api = API()
            api.run()
            return 0
        except KeyboardInterrupt:
            print("Stopping API placeholder")
            return 0
        except Exception as e:
            print(f"API placeholder error: {e}")
            return 3


    def run(self, argv: list | None = None) -> int:
        argv = argv if argv is not None else sys.argv[1:]
        parser = argparse.ArgumentParser(prog="ryuo-cli", description="Ryuo device automation CLI")

        parser.add_argument("-u", "--upload", metavar="LOCAL_PATH", help="Upload local .mp4 file to device")
        parser.add_argument("-l", "--list", action="store_true", help="List media on device")
        parser.add_argument("-i", "--info", action="store_true", help="Show current configuration info")
        parser.add_argument("-s", "--set", nargs=2, metavar=("MEDIA","BRIGHTNESS"), help="Set media on device and brightness (0-255)")
        parser.add_argument("-L", "--loop", action="store_true", help="Run an infinite keepalive loop")
        parser.add_argument("-d", "--daemon", action="store_true", help="Start daemon (placeholder)")
        parser.add_argument("-t", "--tui", action="store_true", help="Start the textual TUI")
        parser.add_argument("-D", "--delete", metavar="MEDIA", help="Delete media from device")

        args = parser.parse_args(argv)

        cli = CLI()

        # dispatch
        if args.list:
            return cli.list_media()

        if args.info:
            return cli.info()

        if args.upload:
            return cli.upload(args.upload)

        if args.set:
            media, brightness = args.set
            return cli.set_media_and_brightness(media, brightness)

        if args.loop:
            return cli.loop_keepalive()

        if args.daemon:
            return cli.api_server()

        if args.delete:
            return cli.delete_media(args.delete)

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

