from .api_client import APIClient
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QPushButton, QLabel, QSlider, QGroupBox,
    QFileDialog, QMessageBox, QStatusBar, QListWidgetItem, QGridLayout
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QUrl
from PyQt6.QtGui import QIcon, QFont
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget
import os
import sys
from typing import Optional


class CacheWorkerThread(QThread):
    progress = pyqtSignal(str, str)
    finished_all = pyqtSignal()

    def __init__(self, client, media_files, cache_dir):
        super().__init__()
        self.client = client
        self.media_files = media_files
        self.cache_dir = cache_dir
        self._stop_requested = False

    def stop(self):
        self._stop_requested = True

    def run(self):
        os.makedirs(self.cache_dir, exist_ok=True)
        for media in self.media_files:
            if self._stop_requested:
                break
            cache_path = os.path.join(self.cache_dir, media)
            if os.path.exists(cache_path):
                self.progress.emit(media, "cached")
                continue
            try:
                self.client.download(media, cache_path)
                self.progress.emit(media, "downloaded")
            except Exception as e:
                self.progress.emit(media, f"error: {e}")
        self.finished_all.emit()


class WorkerThread(QThread):
    finished = pyqtSignal(object, object)

    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            result = self.func(*self.args, **self.kwargs)
            self.finished.emit(True, result)
        except Exception as e:
            self.finished.emit(False, str(e))


class GUI(QMainWindow):

    def __init__(self, host: str = "127.0.0.1", port: int = 55667):
        super().__init__()
        self.client = APIClient(host=host, port=port)
        self.current_media = ""
        self.current_brightness = 200
        self.worker: Optional[WorkerThread] = None
        self.cache_worker: Optional[CacheWorkerThread] = None
        self.cache_dir = os.path.join(os.getcwd(), "cache")

        self.init_ui()
        self.load_initial_config()

    def init_ui(self):
        self.setWindowTitle("Ryuo IV Controller")
        self.setGeometry(100, 100, 1200, 700)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)

        left_panel = QVBoxLayout()

        title_label = QLabel("Ryuo IV Controller")
        title_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_panel.addWidget(title_label)

        info_group = QGroupBox("Device Info")
        info_layout = QGridLayout()
        self.info_media_label = QLabel("Media: Loading...")
        self.info_brightness_label = QLabel("Brightness: Loading...")
        self.info_keepalive_label = QLabel("Keepalive: Loading...")
        self.info_system_data_label = QLabel("Send System Data: Loading...")
        info_layout.addWidget(self.info_media_label, 0, 0)
        info_layout.addWidget(self.info_brightness_label, 0, 1)
        info_layout.addWidget(self.info_keepalive_label, 1, 0)
        info_layout.addWidget(self.info_system_data_label, 1, 1)
        info_group.setLayout(info_layout)
        left_panel.addWidget(info_group)

        brightness_group = QGroupBox("Brightness Control")
        brightness_layout = QVBoxLayout()
        self.brightness_slider = QSlider(Qt.Orientation.Horizontal)
        self.brightness_slider.setMinimum(0)
        self.brightness_slider.setMaximum(255)
        self.brightness_slider.setValue(200)
        self.brightness_slider.valueChanged.connect(self.on_brightness_slider_changed)
        self.brightness_label = QLabel("Brightness: 200")
        self.brightness_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        btn_layout = QHBoxLayout()
        self.set_brightness_btn = QPushButton("Set Brightness")
        self.set_brightness_btn.clicked.connect(self.set_brightness)
        btn_layout.addWidget(self.set_brightness_btn)

        brightness_layout.addWidget(self.brightness_label)
        brightness_layout.addWidget(self.brightness_slider)
        brightness_layout.addLayout(btn_layout)
        brightness_group.setLayout(brightness_layout)
        left_panel.addWidget(brightness_group)

        media_group = QGroupBox("Media Files")
        media_layout = QVBoxLayout()

        self.media_list = QListWidget()
        self.media_list.itemDoubleClicked.connect(self.on_media_double_clicked)
        self.media_list.currentItemChanged.connect(self.on_media_selection_changed)
        media_layout.addWidget(self.media_list)

        media_btn_layout = QHBoxLayout()
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refresh_media_list)
        self.upload_btn = QPushButton("Upload")
        self.upload_btn.clicked.connect(self.upload_media)
        self.download_btn = QPushButton("Download")
        self.download_btn.clicked.connect(self.download_media)
        self.delete_btn = QPushButton("Delete")
        self.delete_btn.clicked.connect(self.delete_media)
        self.set_media_btn = QPushButton("Set Selected")
        self.set_media_btn.clicked.connect(self.set_selected_media)

        media_btn_layout.addWidget(self.refresh_btn)
        media_btn_layout.addWidget(self.upload_btn)
        media_btn_layout.addWidget(self.download_btn)
        media_btn_layout.addWidget(self.delete_btn)
        media_btn_layout.addWidget(self.set_media_btn)

        media_layout.addLayout(media_btn_layout)
        media_group.setLayout(media_layout)
        left_panel.addWidget(media_group)

        main_layout.addLayout(left_panel, 1)

        right_panel = QVBoxLayout()
        preview_group = QGroupBox("Video Preview")
        preview_layout = QVBoxLayout()

        self.video_widget = QVideoWidget()
        self.video_widget.setMinimumSize(400, 300)
        preview_layout.addWidget(self.video_widget)

        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)
        self.media_player.setVideoOutput(self.video_widget)

        video_control_layout = QHBoxLayout()
        self.play_btn = QPushButton("Play")
        self.play_btn.clicked.connect(self.toggle_playback)
        self.pause_btn = QPushButton("Pause")
        self.pause_btn.clicked.connect(self.pause_playback)
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(self.stop_playback)

        video_control_layout.addWidget(self.play_btn)
        video_control_layout.addWidget(self.pause_btn)
        video_control_layout.addWidget(self.stop_btn)
        preview_layout.addLayout(video_control_layout)

        self.preview_status_label = QLabel("No preview loaded")
        self.preview_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview_layout.addWidget(self.preview_status_label)

        preview_group.setLayout(preview_layout)
        right_panel.addWidget(preview_group)

        main_layout.addLayout(right_panel, 1)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.show_message("Ready")

    def load_initial_config(self):
        self.run_async(self.client.get_config, self.on_config_loaded)

    def on_config_loaded(self, success: bool, result):
        if success:
            config = result
            self.current_media = config.get("media", "")
            self.current_brightness = config.get("brightness", 200)

            self.info_media_label.setText(f"Media: {self.current_media or '<none>'}")
            self.info_brightness_label.setText(f"Brightness: {self.current_brightness}")
            self.info_keepalive_label.setText(f"Keepalive: {config.get('keepalive_interval', 'N/A')}s")
            self.info_system_data_label.setText(f"Send System Data: {config.get('send_system_data', 'N/A')}")

            self.brightness_slider.setValue(self.current_brightness)
            self.brightness_label.setText(f"Brightness: {self.current_brightness}")

            self.refresh_media_list()
            self.show_message("Connected to device")

            if self.current_media:
                self.load_preview(self.current_media)
        else:
            self.show_error(f"Failed to load config: {result}")
            self.info_media_label.setText("Media: Error")
            self.info_brightness_label.setText("Brightness: Error")

    def refresh_media_list(self):
        self.run_async(self.client.get_media_files, self.on_media_list_loaded)

    def on_media_list_loaded(self, success: bool, result):
        self.media_list.clear()
        if success:
            media_files = result
            if not media_files:
                self.show_message("No media files found on device")
                return

            for media in media_files:
                item = QListWidgetItem(media)
                if media == self.current_media:
                    item.setText(f"* {media}")
                    item.setForeground(Qt.GlobalColor.darkGreen)
                self.media_list.addItem(item)
            self.show_message(f"Loaded {len(media_files)} media file(s)")

            self.start_cache_worker(media_files)
        else:
            self.show_error(f"Failed to load media list: {result}")

    def start_cache_worker(self, media_files):
        if self.cache_worker and self.cache_worker.isRunning():
            return

        self.cache_worker = CacheWorkerThread(self.client, media_files, self.cache_dir)
        self.cache_worker.progress.connect(self.on_cache_progress)
        self.cache_worker.finished_all.connect(self.on_cache_finished)
        self.cache_worker.start()

    def on_cache_progress(self, media: str, status: str):
        if status == "downloaded":
            self.show_message(f"Cached: {media}")

    def on_cache_finished(self):
        self.show_message("All media cached")

    def on_media_selection_changed(self, current: QListWidgetItem, previous: QListWidgetItem):
        if not current:
            return
        media_name = current.text().lstrip("* ").strip()
        self.load_preview(media_name)

    def load_preview(self, media_name: str):
        cache_path = os.path.join(self.cache_dir, media_name)

        if os.path.exists(cache_path):
            self.media_player.setSource(QUrl.fromLocalFile(cache_path))
            self.preview_status_label.setText(f"Preview: {media_name}")
            self.media_player.play()
        else:
            self.preview_status_label.setText(f"Downloading preview: {media_name}...")
            self.run_async(self.client.download, self.on_preview_downloaded, media_name, cache_path)

    def on_preview_downloaded(self, success: bool, result):
        if success:
            cache_path = result
            media_name = os.path.basename(cache_path)
            self.media_player.setSource(QUrl.fromLocalFile(cache_path))
            self.preview_status_label.setText(f"Preview: {media_name}")
            self.media_player.play()
        else:
            self.preview_status_label.setText("Failed to load preview")

    def toggle_playback(self):
        if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.media_player.pause()
        else:
            self.media_player.play()

    def pause_playback(self):
        self.media_player.pause()

    def stop_playback(self):
        self.media_player.stop()

    def upload_media(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select MP4 file to upload",
            os.path.expanduser("~"),
            "MP4 Files (*.mp4);;All Files (*)"
        )

        if file_path:
            if not file_path.lower().endswith(".mp4"):
                QMessageBox.warning(self, "Invalid File", "Only .mp4 files are supported")
                return

            self.show_message(f"Uploading {os.path.basename(file_path)}...")
            self.run_async(self.client.upload, self.on_upload_finished, file_path)

    def on_upload_finished(self, success: bool, result):
        if success:
            self.show_message("Upload completed successfully")
            self.refresh_media_list()
        else:
            self.show_error(f"Upload failed: {result}")

    def download_media(self):
        current_item = self.media_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "No Selection", "Please select a media file to download")
            return

        media_name = current_item.text().lstrip("* ").strip()

        dest_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save downloaded file",
            os.path.join(os.path.expanduser("~"), media_name),
            "MP4 Files (*.mp4);;All Files (*)"
        )

        if dest_path:
            self.show_message(f"Downloading {media_name}...")
            self.run_async(self.client.download, self.on_download_finished, media_name, dest_path)

    def on_download_finished(self, success: bool, result):
        if success:
            self.show_message(f"Downloaded to: {result}")
        else:
            self.show_error(f"Download failed: {result}")

    def delete_media(self):
        current_item = self.media_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "No Selection", "Please select a media file to delete")
            return

        media_name = current_item.text().lstrip("* ").strip()

        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete '{media_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.show_message(f"Deleting {media_name}...")
            self.run_async(self.client.delete, self.on_delete_finished, media_name)

    def on_delete_finished(self, success: bool, result):
        if success:
            self.show_message("Media deleted successfully")
            current_item = self.media_list.currentItem()
            if current_item:
                media_name = current_item.text().lstrip("* ").strip()
                if media_name == self.current_media:
                    self.current_media = ""
                    self.info_media_label.setText("Media: <none>")
            self.refresh_media_list()
        else:
            self.show_error(f"Delete failed: {result}")

    def set_selected_media(self):
        current_item = self.media_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "No Selection", "Please select a media file to set")
            return

        media_name = current_item.text().lstrip("* ").strip()

        self.show_message(f"Setting media: {media_name}...")
        self.run_async(
            self.client.set_media_and_brightness,
            self.on_set_media_finished,
            media_name,
            self.current_brightness
        )

    def on_set_media_finished(self, success: bool, result):
        if success:
            self.current_media = result.get("media", "")
            self.info_media_label.setText(f"Media: {self.current_media or '<none>'}")
            self.refresh_media_list()
            self.show_message(f"Media set to: {self.current_media}")
        else:
            self.show_error(f"Failed to set media: {result}")

    def set_brightness(self):
        brightness = self.brightness_slider.value()
        self.show_message(f"Setting brightness to {brightness}...")
        self.run_async(self.client.set_brightness, self.on_brightness_set_finished, brightness)

    def on_brightness_set_finished(self, success: bool, result):
        if success:
            self.current_brightness = result.get("brightness", self.brightness_slider.value())
            self.info_brightness_label.setText(f"Brightness: {self.current_brightness}")
            self.show_message(f"Brightness set to: {self.current_brightness}")
        else:
            self.show_error(f"Failed to set brightness: {result}")

    def on_brightness_slider_changed(self, value: int):
        self.brightness_label.setText(f"Brightness: {value}")

    def on_media_double_clicked(self, item: QListWidgetItem):
        media_name = item.text().lstrip("* ").strip()
        self.show_message(f"Setting media: {media_name}...")
        self.run_async(
            self.client.set_media_and_brightness,
            self.on_set_media_finished,
            media_name,
            self.current_brightness
        )

    def run_async(self, func, callback, *args, **kwargs):
        if self.worker and self.worker.isRunning():
            self.worker.wait()
        self.worker = WorkerThread(func, *args, **kwargs)
        self.worker.finished.connect(lambda success, result: callback(success, result))
        self.worker.start()

    def show_message(self, message: str):
        self.status_bar.showMessage(message, 5000)

    def show_error(self, error_message: str):
        self.status_bar.showMessage(f"Error: {error_message}", 10000)
        QMessageBox.critical(self, "Error", error_message)

    def closeEvent(self, a0):
        self.media_player.stop()

        if self.cache_worker and self.cache_worker.isRunning():
            self.cache_worker.stop()
            self.cache_worker.wait(2000)
            if self.cache_worker.isRunning():
                self.cache_worker.terminate()

        if self.worker and self.worker.isRunning():
            self.worker.wait(1000)
            if self.worker.isRunning():
                self.worker.terminate()

        if a0:
            a0.accept()

    def run(self):
        self.show()


def main():
    app = QApplication(sys.argv)
    gui = GUI()
    gui.run()
    sys.exit(app.exec())
