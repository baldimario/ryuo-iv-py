from .api_client import APIClient
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, ListView, ListItem, Input, Button
from textual.containers import HorizontalGroup, VerticalScroll, VerticalGroup
from textual import events
import os
import time

class TUI(App):
    CSS_PATH = None # os.path.join(os.path.dirname(__file__), "tui.css")
    
    def __init__(self):
        super().__init__()
        # create API client which will start the API server if missing
        try:
            self.client = APIClient()
            cfg = self.client.get_config()
            self.brightness = int(cfg.get("brightness", 200))
            self.media_file = str(cfg.get("media", ""))
        except Exception:
            # fallback to safe defaults if API not available
            self.client = APIClient(start_if_missing=False)
            self.brightness = 200
            self.media_file = ""
        self._message = ""
        # file picker state
        self._picker_widget = None
        self._picker_dir = None
        # double-click detection
        self._last_click_time = 0.0
        self._last_click_target = None
        # debug flag to print mouse event info
        self._debug_clicks = True

    def compose(self) -> ComposeResult:
        yield Header()
        yield VerticalScroll(VerticalGroup(
            Static("Ryuo IV TUI", id="title"),
            Static(self._status_text(), id="status"),
            Static("Commands: R=Refresh, U=Upload (enter path then press U), D=Delete selected, Enter=Set selected, S=Set brightness, ←/→ = +/-10", id="legend"),
            Static("[ REFRESH ]   [ UPLOAD ]   [ DELETE ]   [ SET SELECTED ]   [ SET BRIGHTNESS ]", id="actions"),
            VerticalGroup(
                HorizontalGroup(
                    Static(self._brightness_bar(), id="brightness_bar"),
                ),
                HorizontalGroup(
                    Button("-10", id="brightness_decr"),
                    Button("+10", id="brightness_incr"),
                    Button("Set Brightness", id="set_brightness_btn"),
                ),
            ),
            ListView(id="media_list"),
            VerticalGroup(
                HorizontalGroup(
                    Button("Set", id="set_selected_media_btn"),
                    Button("Delete", id="delete_selected_media_btn"),
                    Button("Refresh", id="refresh_media_btn"),
                ),
                HorizontalGroup(
                    Button("Upload", id="upload_btn"),
                ),
            ),
        ), id="main_scroll")
        yield Footer()

    def perform_action(self, action_id: str) -> None:
        if action_id == "set_brightness_btn":
            # apply current brightness value to device
            brightness = int(self.brightness)
            try:
                self.client.set_brightness(brightness)
            except Exception:
                pass
            self.update_status()
            try:
                self.ryuo.config.save_config()
            except Exception:
                pass
        elif action_id == "brightness_incr":
            # increase by 10
            self.set_brightness(self.brightness + 10)
            return
        elif action_id == "brightness_decr":
            # decrease by 10
            self.set_brightness(self.brightness - 10)
            return
        elif action_id == "refresh_media_btn":
            self.refresh_media_list()
        elif action_id == "set_selected_media_btn":
            try:
                media_list = self.query_one("#media_list", ListView)
                idx = getattr(media_list, "index", None)
                if idx is None or idx < 0:
                    return
                # ListView children are ListItem objects; we store media on each ListItem
                item = media_list.children[idx]
                media = getattr(item, "media", None)
                if media:
                    try:
                        self.client.set_media_and_brightness(media, self.brightness)
                        self.media_file = media
                        self.update_status()
                    except Exception:
                        pass
            except Exception:
                pass
        elif action_id == "delete_selected_media_btn":
            try:
                self.delete_selected_media()
            except Exception:
                pass

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        try:
            bid = event.button.id
            if bid == "upload_btn":
                await self.open_file_picker()
                return
            if bid == "file_picker_cancel":
                await self.close_file_picker()
                return
            if bid == "file_picker_select":
                await self._picker_select()
                return


            self.perform_action(bid)
        except Exception:
            pass

    async def on_mouse_down(self, event: events.MouseDown) -> None:
        target = getattr(event, "target", None)
        if target is None:
            return
        if getattr(self, "_debug_clicks", False):
            try:
                tid = getattr(target, "id", None)
                ttypename = type(target).__name__
                print(f"[TUI DEBUG] mouse_down target={ttypename} id={tid} event={event}")
            except Exception:
                pass

        # handling double-clicks on ListItem/file-picker entries regardless of widget id
        node = target
        while node is not None and not any(hasattr(node, attr) for attr in ("media", "path")):
            node = getattr(node, "parent", None)

        now = time.time()
        if node is not None:
            if getattr(self, "_debug_clicks", False):
                try:
                    ntype = type(node).__name__
                    has_media = hasattr(node, "media")
                    has_path = hasattr(node, "path")
                    print(f"[TUI DEBUG] resolved node={ntype} has_media={has_media} has_path={has_path} last_click_time={self._last_click_time}")
                except Exception:
                    pass
            # if same node clicked twice within threshold, treat as double-click
            if self._last_click_target is node and (now - self._last_click_time) <= 0.45:
                if getattr(self, "_debug_clicks", False):
                    print("[TUI DEBUG] detected double-click")
                try:
                    if hasattr(node, "media"):
                        media = getattr(node, "media", None)
                        if media:
                            try:
                                self.client.set_media_and_brightness(media, self.brightness)
                                self.media_file = media
                                self.update_status()
                            except Exception:
                                pass
                    elif hasattr(node, "path"):
                        path = getattr(node, "path", None)
                        isdir = getattr(node, "isdir", False)
                        if isdir:
                            try:
                                self._picker_dir = path
                                self._populate_file_picker()
                            except Exception:
                                pass
                        else:
                            try:
                                if os.path.isfile(path) and path.lower().endswith(".mp4"):
                                    self.upload_path(path)
                                    self.refresh_media_list()
                                    await self.close_file_picker()
                            except Exception:
                                pass
                except Exception:
                    pass
                finally:
                    self._last_click_time = 0.0
                    self._last_click_target = None
                return

            # record this click for potential double-click detection
            self._last_click_time = now
            self._last_click_target = node
            return

        # fallback: if clicked widget has an id, treat as action
        aid = getattr(target, "id", None)
        if aid:
            try:
                self.perform_action(aid)
            except Exception:
                pass

    async def on_click(self, event: events.Click) -> None:
        """Handle textual Click events; use chain==2 for double-clicks."""
        try:
            chain = getattr(event, "chain", 1)
            if chain != 2:
                return
            target = getattr(event, "target", None) or getattr(event, "widget", None)
            if target is None:
                return
            if getattr(self, "_debug_clicks", False):
                try:
                    print(f"[TUI DEBUG] on_click chain={chain} target={type(target).__name__} id={getattr(target,'id',None)}")
                except Exception:
                    pass

            node = target
            while node is not None and not any(hasattr(node, attr) for attr in ("media", "path")):
                node = getattr(node, "parent", None)

            if node is None:
                return

            if hasattr(node, "media"):
                media = getattr(node, "media", None)
                if media:
                    try:
                        self.client.set_media_and_brightness(media, self.brightness)
                        self.media_file = media
                        self.update_status()
                    except Exception:
                        pass
                return

            if hasattr(node, "path"):
                path = getattr(node, "path", None)
                isdir = getattr(node, "isdir", False)
                if isdir:
                    try:
                        self._picker_dir = path
                        self._populate_file_picker()
                    except Exception:
                        pass
                else:
                    try:
                        if os.path.isfile(path) and path.lower().endswith(".mp4"):
                            self.upload_path(path)
                            self.refresh_media_list()
                            await self.close_file_picker()
                    except Exception:
                        pass
        except Exception:
            pass

    async def open_file_picker(self, start_dir: str | None = None) -> None:
        try:
            if self._picker_widget is not None:
                return
            start = start_dir or os.path.expanduser("~")
            if not os.path.isdir(start):
                start = os.getcwd()
            self._picker_dir = start

            panel = VerticalGroup(
                Static(f"Pick file: {self._picker_dir}", id="picker_path"),
                ListView(id="file_picker_list"),
                HorizontalGroup(Button("Open/Select", id="file_picker_select"), Button("Cancel", id="file_picker_cancel")),
                id="file_picker_panel",
            )
            try:
                scroll = self.query_one("#main_scroll", VerticalScroll)
                await scroll.mount(panel)
            except Exception:
                await self.mount(panel)
            self._picker_widget = panel
            self._populate_file_picker()
        except Exception:
            pass

    def _populate_file_picker(self) -> None:
        try:
            lv = self.query_one("#file_picker_list", ListView)
            lv.clear()
            try:
                for name in sorted(os.listdir(self._picker_dir)):
                    full = os.path.join(self._picker_dir, name)
                    isdir = os.path.isdir(full)
                    display = name + ("/" if isdir else "")
                    li = ListItem(Static(display))
                    li.path = full
                    li.isdir = isdir
                    lv.append(li)
            except Exception:
                pass
            try:
                lv.index = 0
            except Exception:
                pass
            try:
                path_widget = self.query_one("#picker_path", Static)
                path_widget.update(f"Pick file: {self._picker_dir}")
            except Exception:
                pass
        except Exception:
            pass

    async def close_file_picker(self) -> None:
        try:
            if self._picker_widget is None:
                return
            await self._picker_widget.remove()
            self._picker_widget = None
            self._picker_dir = None
        except Exception:
            pass

    async def _picker_select(self) -> None:
        try:
            lv = self.query_one("#file_picker_list", ListView)
            idx = getattr(lv, "index", None)
            if idx is None or idx < 0:
                return
            item = lv.children[idx]
            path = getattr(item, "path", None)
            isdir = getattr(item, "isdir", False)
            if isdir:
                # navigate into directory
                self._picker_dir = path
                self._populate_file_picker()
                return

            # selected file: populate upload input, close picker and trigger upload
            try:
                # actually upload selected file from media_list and close picker
                if os.path.isfile(path) and path.lower().endswith(".mp4"):
                    self.upload_path(path)
                    self.refresh_media_list()
                    self.close_file_picker()
            except Exception:
                pass
            await self.close_file_picker()
            # call do_upload action to perform upload from input
            self.perform_action("do_upload")
        except Exception:
            pass

    def set_brightness(self, value: int) -> None:
        # clamp and update UI
        value = max(0, min(255, int(value)))
        self.brightness = value
        try:
            bar = self.query_one("#brightness_bar", Static)
            bar.update(self._brightness_bar())
            self.update_status()
        except Exception:
            pass

    def upload_path(self, path: str) -> None:
        try:
                try:
                    self.client.upload(path)
                except Exception:
                    # attempt to start API and retry once
                    try:
                        self.client.ensure_running()
                        self.client.upload(path)
                    except Exception:
                        pass
        except Exception:
            pass

    def delete_selected_media(self) -> None:
        media_list = self.query_one("#media_list", ListView)
        idx = getattr(media_list, "index", None)
        
        if idx is None or idx < 0:
            return
        
        item = media_list.children[idx]
        media = getattr(item, "media", None)
        
        if not media:
            return
        
        try:
            self.client.delete(media)
        except Exception:
            pass

        # refresh and choose first available media as current (if any)
        self.refresh_media_list()
        media_files = [getattr(c, "media", None) for c in self.query_one("#media_list", ListView).children]
        if media_files:
            new_media = media_files[0]
            try:
                self.client.set_media_and_brightness(new_media, self.brightness)
            except Exception:
                pass
            self.media_file = new_media
        else:
            try:
                self.client.set_media_and_brightness("", self.brightness)
            except Exception:
                pass
            self.media_file = ""
        try:
            self.ryuo.config.save_config()
        except Exception:
            pass
        self.update_status()

    def _brightness_bar(self, length: int = 20) -> str:
        # render a simple textual bar representing the brightness value
        filled = int((self.brightness / 255) * length)
        filled = max(0, min(length, filled))
        bar = "#" * filled + "-" * (length - filled)
        return f"[{bar}] {self.brightness}"

    def refresh_media_list(self):
        media_list = self.query_one("#media_list", ListView)
        media_list.clear()
        try:
            media_files = self.client.get_media_files()
        except Exception:
            media_files = []
        for media in media_files:
            li = ListItem(Static(media))
            # attach media filename for easy retrieval when selected
            li.media = media
            media_list.append(li)
        self.update_status()


    def run(self):
        super().run()

    async def on_mount(self) -> None:
        # populate input widgets and load media list when the app mounts
        try:
            # set initial brightness bar
            bar = self.query_one("#brightness_bar", Static)
            bar.update(self._brightness_bar())
        except Exception:
            pass

        # load media list immediately
        self.refresh_media_list()

    def _status_text(self) -> str:
        msg_line = f"\n{self._message}" if getattr(self, "_message", "") else ""
        return (
            f"Brightness: {self.brightness}  |  Media: {self.media_file or '<none>'}{msg_line}\n"
            "Keys: Left/Right adjust brightness, S = set brightness, R = refresh media list"
        )

    def update_status(self) -> None:
        try:
            status = self.query_one("#status", Static)
            status.update(self._status_text())
        except Exception:
            pass

    def on_key(self, event) -> None:
        # handle simple key bindings
        key = getattr(event, "key", None)
        if key in ("left", "h"):
            # change by 10 with keyboard arrows
            self.set_brightness(self.brightness - 10)
        elif key in ("right", "l"):
            self.set_brightness(self.brightness + 10)
        elif key in ("r", "R"):
            self.refresh_media_list()
        elif key in ("s", "S"):
            # apply current brightness
            try:
                try:
                    self.client.set_brightness(int(self.brightness))
                except Exception:
                    pass
                self.update_status()
            except Exception:
                pass
        elif key in ("u", "U"):
            # trigger upload from upload_input
            try:
                upload_input = self.query_one("#upload_input", Input)
                path = upload_input.value.strip()
                if path:
                    self.upload_path(path)
                    self.refresh_media_list()
            except Exception:
                pass
        elif key in ("d", "D"):
            # delete selected
            try:
                self.delete_selected_media()
            except Exception:
                pass
        elif key in ("enter", "\n"):
            # apply selected media
            try:
                media_list = self.query_one("#media_list", ListView)
                idx = getattr(media_list, "index", None)
                if idx is None or idx < 0:
                    return
                item = media_list.children[idx]
                media = getattr(item, "media", None)
                if media:
                    try:
                        self.client.set_media_and_brightness(media, self.brightness)
                        self.media_file = media
                        self.update_status()
                    except Exception:
                        pass
            except Exception:
                pass
