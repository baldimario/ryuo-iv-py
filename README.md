Ryuo IV Controller - ryuoctl
=================================

Small tools to control an Arturia ROG Ryuo IV device from Python: a daemon, a CLI, a Textual TUI, a PyQt6 GUI and an HTTP API that wrap the device driver logic.

![Ryuo](/assets/ryuoctl.png)

Features
--------
- FastAPI HTTP API for remote control (list/upload/delete/set brightness/media/download)
- `ryuoctl` CLI to script uploads, downloads and device control
- Textual TUI with media browser and double-click actions
- Systemd-friendly install/uninstall scripts that install a venv and a wrapper executable

Requirements
------------
- Linux with Python 3.10+ (or system Python3)
- hidapi and adb available on the system (or installed via `requirements.txt`)

Quick install (local)
---------------------
1. Clone this repository.
2. Create a virtual environment and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run the FastAPI server for local testing:

```bash
python src/main.py --port 55667
# or from the repo root to start the daemon (development)
```

System installation (recommended for a host machine)
---------------------------------------------------
The repository includes `install.sh` and `uninstall.sh` to install a minimal runtime in `/opt/ryuoctl` and create a systemd unit.

To install and start the service (requires root):

```bash
sudo ./install.sh -p 55667
# the installer will attempt to enable and start the service
sudo journalctl -u ryuoctld.service -f
```

If you prefer to manage the service manually:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now ryuoctld.service
sudo journalctl -u ryuoctld.service -f
```

Usage
-----

CLI examples (from project root or system wrapper):

```bash
# list media
python src/main.py --list
# or
ryuoctl --list

# upload a file
python src/main.py --upload path/to/file.mp4
# or
ryuoctl --upload path/to/file.mp4

# set currently playing media (optional brightness)
python src/main.py --set media.mp4 80
# or
ryuoctl --set media.mp4 80

# download media from device
python src/main.py --download media.mp4 path/media.mp4
# or
ryuoctl --download meida.mp4 path/media.mp4

# set brightness
python src/main.py --brightness 200
# or
ryuoctl --brightness 200

# run TUI
python src/main.py --tui
# or
ryuoctl --tui

# run GUI
python src/main.py --gui
# or
ryuoctl --gui

# delete media
python src/main.py --delete media.mp4
# or
ryuoctl --delete media.mp4
```

API endpoints
-------------
- GET  /list               -> list media files
- GET  /info               -> get device config
- POST /upload             -> upload multipart/form-data file
- DELETE /delete/{media}   -> delete a media file
- POST /set/{media}/{b}    -> set media and brightness
- POST /brightness/{b}     -> set brightness only
- GET  /download/{media}   -> stream a download


API Doc (Swagger/OpenAPI)
-----------
http://127.0.0.1:5567/docs

Packaging & Service notes
------------------------
- `install.sh` will copy the repo into `/opt/ryuoctl`, create a venv, write a wrapper to `/usr/local/bin/ryuoctl` and a systemd unit in `/etc/systemd/system/ryuoctld.service`.
- The installer also writes a udev rule to set permissions on the `hidraw` node for the Ryuo device.
- The service runs the wrapper which executes `src/main.py` in the venv.

Privacy & Safety
---------------
- This tool interacts with USB and ADB; use with care. The installer modifies system rules and installs a daemon.

Contributing
------------
- Open issues or PRs for bug fixes and feature requests.
- Tests and CI are welcomed; keep the API contract stable.

![Ryuo](/assets/ryuo.png)

License
-------
MIT License. See LICENSE file for details.

Contact
-------
For questions or help, open an issue in the repository or message the maintainer.

Disclaimer and Liability
------------------------
The use of this software is the sole responsibility of the person running it. The project is provided "as-is" without any explicit or implied warranties. Rights to the protocol, the name, the trademark, and the product belong to Asus (or their respective owners); this repository does not grant any license to those rights.

This project is developed for personal and experimental use: official Linux support for this device is absent and not planned in the near future. Use it knowingly and at your own risk.

