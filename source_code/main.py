import time
import sys
import os
import subprocess
import time
import json
from pathlib import Path

# Add parent directory to path so we can import source_code as a module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, QFileDialog,
    QLabel, QMessageBox, QProgressBar, QSplashScreen
)
from PySide6.QtCore import Qt, QTimer, QEvent
from PySide6.QtGui import QPixmap, QColor, QCursor

from source_code.workers.audio_analyzer import AudioAnalyzerThread
from source_code.workers.process_thread import ProcessThread
from source_code.dialogs.settings_dialog import SettingsDialog
from source_code.services.player_service import PlayerService
from source_code.services.download_service import DownloadService
from source_code.services.audio_service import AudioService
from source_code.services.file_loading_service import FileLoadingService
from source_code.ui.main_layout import create_main_layout

class KaraokeApp(QWidget):
    def __init__(self):
        super().__init__()
        self.video_path = ""
        self.widen_tab_video_path = ""  
        self.active_tasks = {}
        self.is_video_fullscreen = False
        self.download_splash = None
        self.export_splash = None

        self.init_settings_manager()

        self.setWindowTitle("Karaoke Studio Pro v2.0")
        self.resize(1150, 850)
        self.setStyleSheet("background-color: #1e1e1e; color: #ffffff; font-family: 'Segoe UI';")

        self.player = PlayerService(parent=self)

        self.setup_ui()
        self.nav_list.setCurrentRow(0)

        self.timer = QTimer()
        self.timer.setInterval(200)
        self.timer.timeout.connect(self.update_ui)
        self.timer.start()
        self.is_user_sliding = False

        # Fullscreen Hover Controls Logic Setup
        self.hide_controls_timer = QTimer()
        self.hide_controls_timer.setSingleShot(True)
        self.hide_controls_timer.setInterval(3000)  # Auto-hide after 3 seconds of no mouse movement
        self.hide_controls_timer.timeout.connect(self.hide_fullscreen_controls)

        self.fullscreen_timer = None
        self.last_mouse_pos = QCursor.pos()

        self.setAcceptDrops(True)
        self.video_frame.setAcceptDrops(True)

        # Monitor mouse events across the video framework structure
        self.video_frame.installEventFilter(self)
        self.playback_widget.installEventFilter(self)

        # Initialize and start audio analyzer thread
        self.audio_analyzer = AudioAnalyzerThread()
        self.audio_analyzer.level_updated.connect(self.on_audio_level_updated)
        self.audio_analyzer.start()

        # Initialize audio service for managing audio analyzer and meter
        self.audio_service = AudioService(self.audio_analyzer, self.audio_level_meter)

        # Initialize file loading service for thread-safe file operations
        self.file_loading_service = FileLoadingService(self.audio_service, self.player)

        # Initialize download service
        self._download_from_widen = False
        self.download_service = DownloadService(self.settings, ProcessThread)
        self.download_service.download_progress.connect(self._on_download_progress)
        self.download_service.download_finished.connect(self._on_download_finished)
        self.download_service.download_error.connect(self._on_download_error)

        # Auto-reduce tracking
        self.auto_reduce_active = False

    def init_settings_manager(self):
        app_dir = Path(sys._MEIPASS) if hasattr(sys, '_MEIPASS') else Path(__file__).parent.parent
        config_dir = app_dir / "config"
        config_dir.mkdir(exist_ok=True)
        self.settings_file = config_dir / "settings.json"

        self.settings = {
            "base_directory": str(app_dir),
            "download_directory": str(app_dir),
            "ffmpeg_path": "ffmpeg",
            "ffprobe_path": "ffprobe",
            "ytdlp_path": "yt-dlp",
            "measurement_mode": "dB Output (dBFS)",
            "auto_reduce_threshold": 80
        }
        if self.settings_file.exists():
            try:
                with open(self.settings_file, 'r') as f: self.settings.update(json.load(f))
            except: pass

    def save_settings(self):
        try:
            with open(self.settings_file, 'w') as f: json.dump(self.settings, f, indent=2)
        except: pass

    def setup_ui(self):
        """Set up the entire UI using modularized UI components"""
        layout_result = create_main_layout(self.settings)
        self.main_h_layout = layout_result["main_layout"]
        self.setLayout(self.main_h_layout)
        
        components = layout_result["components"]
        
        # Extract sidebar components
        sidebar_components = components["sidebar_components"]
        self.sidebar = sidebar_components["sidebar"]
        self.nav_list = sidebar_components["nav_list"]
        self.extra_tools_toggle_btn = sidebar_components["extra_tools_toggle_btn"]
        self.extra_tools_container = sidebar_components["extra_tools_container"]
        self.widen_video_btn = sidebar_components["widen_video_btn"]
        self.history_toggle_btn = sidebar_components["history_toggle_btn"]
        self.history_container = sidebar_components["history_container"]
        self.clear_hist_btn = sidebar_components["clear_hist_btn"]
        self.history_list = sidebar_components["history_list"]
        self.settings_btn = sidebar_components["settings_btn"]
        self.status_label = sidebar_components["status_label"]
        
        # Extract video frame and labels
        self.video_frame = components["video_frame"]
        self.filename_label = components["filename_label"]
        
        # Extract playback bar components
        playback_components = components["playback_components"]
        self.playback_widget = playback_components["playback_widget"]
        self.time_label = playback_components["time_label"]
        self.seek_slider = playback_components["seek_slider"]
        self.duration_label = playback_components["duration_label"]
        self.back_btn = playback_components["back_btn"]
        self.play_btn = playback_components["play_btn"]
        self.pause_btn = playback_components["pause_btn"]
        self.fwd_btn = playback_components["fwd_btn"]
        self.mute_btn = playback_components["mute_btn"]
        self.vol_slider = playback_components["vol_slider"]
        self.vol_label = playback_components["vol_label"]
        self.audio_level_meter = playback_components["audio_level_meter"]
        self.audio_level_label = playback_components["audio_level_label"]
        self.fullscreen_btn = playback_components["fullscreen_btn"]
        
        # Extract page components
        download_page_components = components["download_page_components"]
        self.load_btn = download_page_components["load_btn"]
        self.url_input = download_page_components["url_input"]
        dl_btn_download = download_page_components["dl_btn"]
        
        pitch_page_components = components["pitch_page_components"]
        self.pitch_minus = pitch_page_components["pitch_minus"]
        self.pitch_input = pitch_page_components["pitch_input"]
        self.pitch_plus = pitch_page_components["pitch_plus"]
        self.pitch_reset = pitch_page_components["pitch_reset"]
        self.speed_minus = pitch_page_components["speed_minus"]
        self.speed_input = pitch_page_components["speed_input"]
        self.speed_plus = pitch_page_components["speed_plus"]
        self.speed_reset = pitch_page_components["speed_reset"]
        self.export_btn = pitch_page_components["export_btn"]
        
        extra_page_components = components["extra_page_components"]
        widen_file_btn = extra_page_components["widen_file_btn"]
        self.widen_url_input = extra_page_components["widen_url_input"]
        widen_dl_btn = extra_page_components["widen_dl_btn"]
        self.widen_file_status_label = extra_page_components["widen_file_status_label"]
        self.widen_exec_btn = extra_page_components["widen_exec_btn"]
        
        self.stack = components["stack"]
        
        # Connect signals for button events
        self.nav_list.currentRowChanged.connect(self.handle_navigation_change)
        self.widen_video_btn.clicked.connect(lambda: self.handle_navigation_change(2))
        self.extra_tools_toggle_btn.clicked.connect(self.toggle_extra_tools)
        self.history_toggle_btn.clicked.connect(self.toggle_history)
        self.clear_hist_btn.clicked.connect(self.clear_history)
        self.settings_btn.clicked.connect(self.open_settings)
        self.load_btn.clicked.connect(lambda: self.load_video())
        dl_btn_download.clicked.connect(lambda: self.download_video(from_widen_tab=False))
        self.fullscreen_btn.clicked.connect(self.toggle_video_fullscreen)
        self.play_btn.clicked.connect(self.player.play)
        self.pause_btn.clicked.connect(self.player.pause)
        self.back_btn.clicked.connect(lambda: self.jump_time(-10000))
        self.fwd_btn.clicked.connect(lambda: self.jump_time(10000))
        self.mute_btn.clicked.connect(self.toggle_mute)
        self.vol_slider.valueChanged.connect(self.set_volume)
        self.seek_slider.sliderPressed.connect(self.on_slider_pressed)
        self.seek_slider.sliderReleased.connect(self.on_slider_released)
        self.speed_input.valueChanged.connect(lambda v: self.player.set_rate(v))
        self.export_btn.clicked.connect(self.export_video)
        widen_file_btn.clicked.connect(self.browse_widen_video)
        widen_dl_btn.clicked.connect(lambda: self.download_video(from_widen_tab=True))
        self.widen_exec_btn.clicked.connect(self.widen_active_video_canvas)
        self.history_list.itemDoubleClicked.connect(lambda item: self.load_video(item.toolTip()))
        
        # Initialize state flags
        self.extra_tools_is_expanded = False
        self.history_is_expanded = False
        
        # Load history from disk
        self.load_history_from_disk()

    def handle_navigation_change(self, idx):
        if idx == 2:
            self.nav_list.blockSignals(True)
            self.nav_list.clearSelection()
            self.nav_list.setCurrentRow(-1)
            self.nav_list.blockSignals(False)
        else:
            self.nav_list.blockSignals(True)
            self.nav_list.setCurrentRow(idx)
            self.nav_list.blockSignals(False)
        self.stack.setCurrentIndex(idx)

    def browse_widen_video(self):
        f, _ = QFileDialog.getOpenFileName(
            self, "Select Widen Target Video", self.settings["base_directory"],
            "Media Feeds (*.mp4 *.avi *.mkv *.mov *.webm);;All System Inputs (*.*)"
        )
        if f:
            self.widen_tab_video_path = os.path.normpath(f)
            self.widen_file_status_label.setText(f"Queued File for Widening: {os.path.basename(self.widen_tab_video_path)}")
            self.load_video(self.widen_tab_video_path)

    def open_settings(self):
        # Pause audio analyzer while settings dialog is open to prevent conflicts
        was_playing = self.audio_service.pause_analyzer()
        
        try:
            dialog = SettingsDialog(self, self)
            dialog.exec()
            # Update audio meter display mode if settings were changed
            self.audio_service.set_display_mode(self.settings.get("measurement_mode", "dB Output (dBFS)"))
        finally:
            # Resume audio analyzer if it was playing
            if was_playing:
                self.audio_service.resume_analyzer()

    def set_volume(self, value):
        self.player.set_volume(value); self.vol_label.setText(f"{value}%")
        self.mute_btn.setText("🔊" if value > 0 else "🔇")

    def toggle_mute(self):
        m = not self.player.get_mute(); self.player.set_mute(m)
        self.mute_btn.setText("🔇" if m else "🔊")

    def on_audio_level_updated(self, db_level):
        if not hasattr(self, 'audio_level_meter'): return

        self.audio_level_meter.set_level(db_level)

        # Convert dB to 0-100 scale (Assuming -80 to 0)
        level_percent = ((db_level + 80.0) / 80.0) * 100.0

        # Get configurable auto-reduce threshold (default 90%)
        threshold = self.settings.get("auto_reduce_threshold", 90)
        
        # Auto-reduction logic with configurable threshold
        if level_percent > threshold:
            # Increment a counter instead of triggering immediately
            if not hasattr(self, 'high_db_counter'): self.high_db_counter = 0
            self.high_db_counter += 1

            # If it stays loud for ~2 seconds (20 cycles at 100ms each), reduce volume
            if self.high_db_counter >= 20:
                current_vol = self.vol_slider.value()
                if current_vol > 20:
                    new_volume = max(20, current_vol - 5)
                    self.vol_slider.setValue(new_volume)
                    spl = 60 + (level_percent * 0.5)  # Approximate SPL
                    self.status_label.setText(f"Auto-reduced volume to {new_volume}% (Level: {level_percent:.0f}%, ~{spl:.0f} SPL)")
                    self.high_db_counter = 0  # Reset after action
        else:
            # Reset counter if volume drops below threshold
            self.high_db_counter = 0

    def jump_time(self, ms):
        if self.player.is_active():
            current = self.player.get_time()
            duration = self.player.get_length()
            if duration <= 0: return
            new_time = max(0, min(current + ms, duration - 1000))
            self.player.set_position(new_time / duration)

    def add_to_history(self, file_path):
        if not file_path or not os.path.exists(file_path): return
        filename = os.path.basename(file_path)
        for i in range(self.history_list.count()):
            if self.history_list.item(i).toolTip() == file_path:
                self.history_list.takeItem(i)
                break
        self.history_list.insertItem(0, filename)
        self.history_list.item(0).setToolTip(file_path)
        while self.history_list.count() > 10: self.history_list.takeItem(self.history_list.count() - 1)
        self.save_history_to_disk()

    def save_history_to_disk(self):
        paths = [self.history_list.item(i).toolTip() for i in range(self.history_list.count())]
        history_file = Path(self.settings_file.parent) / "history.json"
        try:
            with open(history_file, "w", encoding="utf-8") as f: json.dump(paths, f, indent=2)
        except: pass

    def load_history_from_disk(self):
        history_file = Path(self.settings_file.parent) / "history.json"
        if history_file.exists():
            try:
                with open(history_file, "r", encoding="utf-8") as f:
                    paths = json.load(f)
                    for path in reversed(paths):
                        if os.path.exists(path):
                            filename = os.path.basename(path)
                            self.history_list.insertItem(0, filename)
                            self.history_list.item(0).setToolTip(path)
            except: pass

    def clear_history(self):
        self.history_list.clear()
        history_file = Path(self.settings_file.parent) / "history.json"
        if history_file.exists(): history_file.unlink()

    def toggle_history(self):
        self.history_is_expanded = not self.history_is_expanded
        self.history_container.setVisible(self.history_is_expanded)
        self.history_toggle_btn.setText(f"{'▼' if self.history_is_expanded else '▶'} History")

    def toggle_extra_tools(self):
        self.extra_tools_is_expanded = not self.extra_tools_is_expanded
        self.extra_tools_container.setVisible(self.extra_tools_is_expanded)
        self.extra_tools_toggle_btn.setText(f"{'▼' if self.extra_tools_is_expanded else '▶'} 🛠 Extra Tools")

    def load_video(self, file_path=None, splash_screen=None):
        print(f"\n\n{'='*80}")
        print(f"[main.load_video] 🎬 ENTRY (file_path={file_path})")
        
        if not file_path:
            print(f"[main.load_video] 📂 No file path provided, opening dialog...")
            f, _ = QFileDialog.getOpenFileName(
                self, "Open Audio/Video Track Resource", self.settings["base_directory"],
                "Media Feeds (*.mp4 *.avi *.mkv *.mov *.mp3 *.wav *.aac *.m4a *.webm);;All System Inputs (*.*)"
            )
            if not f: 
                print(f"[main.load_video] ❌ Dialog cancelled")
                return
            file_path = f
            print(f"[main.load_video] ✓ File selected: {file_path}")

        # Prepare for loading using file loading service
        print(f"[main.load_video] Calling file_loading_service.prepare_for_loading()...")
        was_playing = self.file_loading_service.prepare_for_loading()
        print(f"[main.load_video] ✓ prepare_for_loading returned (was_playing={was_playing})")

        if splash_screen is None:
            loading_path = get_resource_path("Loading.png")
            pix = QPixmap(loading_path).scaled(600, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation) if os.path.exists(loading_path) else QPixmap(600, 300)
            if not os.path.exists(loading_path): pix.fill(QColor("#1e1e1e"))
            loader = ModernSplashScreen(pix)
            loader.show()
        else:
            loader = splash_screen

        QApplication.processEvents()
        self._pending_video_path = file_path
        self.add_to_history(file_path)

        try:
            # Core loading logic
            print(f"[main.load_video] 🎯 Starting core loading logic...")
            loader.set_progress(40, "Mapping Core Encoders...")
            self.video_path = self._pending_video_path
            print(f"[main.load_video] 📝 Setting video_path: {self.video_path}")
            
            print(f"[main.load_video] 🎬 Calling player.set_media({os.path.abspath(self.video_path)})...")
            self.player.set_media(os.path.abspath(self.video_path))
            print(f"[main.load_video] ✓ player.set_media() complete")

            print(f"[main.load_video] 🖥️  Calling player.set_video_widget()...")
            self.player.set_video_widget(int(self.video_frame.winId()))
            print(f"[main.load_video] ✓ Video widget set")

            loader.set_progress(70, "Synchronizing Canvas Matrix Pipeline...")

            time.sleep(0.1)  # Small delay before playing to ensure media is properly loaded
            print(f"[main.load_video] ⏱️  Waited 0.1s before playback...")
            
            print(f"[main.load_video] ▶️  Calling player.play()...")
            self.player.play()
            print(f"[main.load_video] ✓ player.play() called")
            
            self.time_label.setText("00:00")

            print(f"[main.load_video] 🔊 Waiting for audio track (retries up to 20)...")
            retries = 0
            while self.player.get_audio_track() == -1 and retries < 20:
                time.sleep(0.05)
                QApplication.processEvents()
                retries += 1
            print(f"[main.load_video] ✓ Audio track detected after {retries} retries")

            print(f"[main.load_video] 🔉 Setting volume to {self.vol_slider.value()}...")
            self.player.set_volume(self.vol_slider.value())
            print(f"[main.load_video] ✓ Volume set")

            # Start audio monitoring after playback begins
            print(f"[main.load_video] 🎙️  Starting audio analyzer (via audio_service)...")
            self.audio_service.start_audio_monitoring()
            print(f"[main.load_video] ✓ Audio analyzer started")

            print(f"[main.load_video] 📊 Calling finish_loading(loader)...")
            self.finish_loading(loader)
            print(f"[main.load_video] ✓ finish_loading() complete")

        except Exception as e:
            print(f"[main.load_video] ❌ Engine Fault: {e}")
            import traceback
            traceback.print_exc()
            loader.close()
        finally:
            # Ensure file loading service is notified of completion
            print(f"[main.load_video] 🔚 Calling file_loading_service.finish_loading(resume_audio={was_playing})...")
            self.file_loading_service.finish_loading(resume_audio=was_playing)
            print(f"[main.load_video] ✓ file_loading_service.finish_loading() complete")
            print(f"{'='*80}\n")

    def finish_loading(self, loader):
        self.pitch_input.setValue(0.0)
        self.speed_input.setValue(1.0)
        if self.video_path: self.filename_label.setText(f"Playing: {os.path.basename(self.video_path)}")

        loader.set_progress(100, "Ready")
        loader.finish(self)

    def download_video(self, from_widen_tab=False):
        input_widget = self.widen_url_input if from_widen_tab else self.url_input
        url = input_widget.text().strip()
        if not url.startswith("http"):
            QMessageBox.warning(self, "Validation Alert", "Provide target link URL parameters matching HTTP/HTTPS formats.")
            return

        self._download_from_widen = from_widen_tab
        self.status_label.setText("Status: Deploying Downloader Task Pipes...")
        loading_path = get_resource_path("Loading.png")
        pix = QPixmap(loading_path).scaled(600, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation) if os.path.exists(loading_path) else QPixmap(600, 300)
        if not os.path.exists(loading_path): pix.fill(QColor("#1e1e1e"))

        self.download_splash = ModernSplashScreen(pix, show_cancel_button=True)
        self.download_splash.cancel_btn.clicked.connect(self.download_service.stop_download)
        self.download_splash.show()
        QApplication.processEvents()

        self.download_service.download_video(url, self.settings["download_directory"])

    def _on_download_progress(self, percent, message):
        if self.download_splash:
            self.download_splash.set_progress(percent, message)

    def _on_download_finished(self, filename):
        if self.download_splash:
            self.download_splash.close()
            self.download_splash = None
        self.status_label.setText("Status: Ready")
        try:
            targets = [f for f in os.listdir(self.settings["download_directory"]) if f.endswith('.mp4')]
            if targets:
                latest = max(targets, key=lambda x: os.path.getmtime(os.path.join(self.settings["download_directory"], x)))
                full_p = os.path.normpath(os.path.join(self.settings["download_directory"], latest))
                
                # Wait for file to be completely written and stable (not locked)
                if self._wait_for_file_ready(full_p):
                    if self._download_from_widen:
                        self.widen_url_input.clear()
                        self.widen_tab_video_path = full_p
                        self.widen_file_status_label.setText(f"Queued File for Widening: {os.path.basename(full_p)}")
                        self.load_video(full_p)
                    else:
                        self.url_input.clear()
                        self.load_video(full_p)
                else:
                    QMessageBox.warning(self, "File Access Error", "Downloaded file is locked or inaccessible. Please try again.")
        except Exception as e:
            QMessageBox.critical(self, "File Capture Error", f"Failed capturing downloaded file: {e}")

    def _wait_for_file_ready(self, file_path, max_wait=15, stability_threshold=1.0):
        """
        Wait for a downloaded file to be completely written and stable.
        
        Args:
            file_path: Path to the file
            max_wait: Maximum seconds to wait
            stability_threshold: Seconds file size must remain stable
        
        Returns:
            True if file is ready, False if timeout/error
        """
        import os
        
        start_time = time.time()
        last_size = -1
        stable_start = None
        
        while time.time() - start_time < max_wait:
            try:
                # Check if file exists and is accessible
                if not os.path.exists(file_path):
                    time.sleep(0.1)
                    continue
                
                # Get current file size
                current_size = os.path.getsize(file_path)
                
                # Try to open file (check if locked)
                try:
                    with open(file_path, 'rb') as f:
                        f.read(1)  # Read one byte to ensure file is accessible
                except (IOError, OSError):
                    # File is locked, wait more
                    last_size = -1
                    stable_start = None
                    time.sleep(0.5)
                    continue
                
                # Check if file size has stabilized
                if current_size == last_size:
                    if stable_start is None:
                        stable_start = time.time()
                    elif time.time() - stable_start >= stability_threshold:
                        return True  # File is stable!
                else:
                    # Size changed, reset stability timer
                    last_size = current_size
                    stable_start = None
                    time.sleep(0.5)
                    
            except Exception as e:
                print(f"File readiness check error: {e}")
                time.sleep(0.5)
        
        return False

    def _on_download_error(self, message):
        if self.download_splash:
            self.download_splash.close()
            self.download_splash = None
        self.status_label.setText("Status: Ready")
        if "cancelled" not in message.lower():
            QMessageBox.warning(self, "Download Error", message)

    def get_video_duration_via_ffprobe(self, target_path):
        if not os.path.exists(target_path): return 0
        try:
            cmd = [self.settings["ffprobe_path"], "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", target_path]
            startupinfo = None
            if sys.platform == "win32":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = 0
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, startupinfo=startupinfo, text=True, timeout=3)
            return float(res.stdout.strip())
        except:
            return 0

    def export_video(self):
        if not self.video_path: return

        loading_path = get_resource_path("Loading.png")
        pix = QPixmap(loading_path).scaled(600, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation) if os.path.exists(loading_path) else QPixmap(600, 300)
        if not os.path.exists(loading_path): pix.fill(QColor("#1e1e1e"))

        self.export_splash = ModernSplashScreen(pix, show_cancel_button=True)
        self.export_splash.cancel_btn.clicked.connect(lambda: self.kill_allocated_task("exporter"))
        self.export_splash.show()

        s, p = self.speed_input.value(), self.pitch_input.value()
        pf = 2**(p/12)
        tempo_val = s / pf

        atempo_list = []
        curr_t = tempo_val
        while curr_t > 2.0: atempo_list.append("atempo=2.0"); curr_t /= 2.0
        while curr_t < 0.5: atempo_list.append("atempo=0.5"); curr_t /= 0.5
        atempo_list.append(f"atempo={round(curr_t, 4)}")

        out = os.path.join(self.settings["download_directory"], f"karaoke_export_{int(time.time())}.mp4")
        abs_in = os.path.abspath(self.video_path).replace("\\", "/")
        abs_out = os.path.abspath(out).replace("\\", "/")

        cmd = [self.settings["ffmpeg_path"], "-y", "-i", abs_in, "-filter_complex", 
               f"[0:v]setpts=PTS/{s}[v];[0:a]asetrate=44100*{pf},aresample=44100,{','.join(atempo_list)}[a]", 
               "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-b:v", "2000k", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", abs_out]

        duration = self.get_video_duration_via_ffprobe(abs_in) / s
        self.launch_async_task(cmd, abs_out, "exporter", override_duration=duration)

    def widen_active_video_canvas(self):
        target_input = self.widen_tab_video_path if self.widen_tab_video_path else self.video_path
        if not target_input or not os.path.exists(target_input):
            QMessageBox.warning(self, "Missing Asset Input", "Load a file path or complete a download segment beforehand.")
            return

        loading_path = get_resource_path("Loading.png")
        pix = QPixmap(loading_path).scaled(600, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation) if os.path.exists(loading_path) else QPixmap(600, 300)
        if not os.path.exists(loading_path): pix.fill(QColor("#1e1e1e"))

        self.export_splash = ModernSplashScreen(pix, show_cancel_button=True)
        self.export_splash.cancel_btn.clicked.connect(lambda: self.kill_allocated_task("widen_task"))
        self.export_splash.show()

        base_name = os.path.splitext(os.path.basename(target_input))[0]
        out = os.path.join(self.settings["download_directory"], f"{base_name}-wide.mp4")

        abs_in = os.path.abspath(target_input).replace("\\", "/")
        abs_out = os.path.abspath(out).replace("\\", "/")

        filter_str = "crop=in_w:in_h*0.3:0:in_h*0.2,scale=1920*1.1:1080*1.1:force_original_aspect_ratio=increase,crop=1920:1080"
        cmd = [self.settings["ffmpeg_path"], "-y", "-i", abs_in, "-vf", filter_str, "-c:a", "copy", abs_out]

        duration = self.get_video_duration_via_ffprobe(abs_in)
        self.launch_async_task(cmd, abs_out, "widen_task", override_duration=duration)

    def launch_async_task(self, cmd, out_path, task_key, override_duration=0):
        self.kill_allocated_task(task_key)

        thread = ProcessThread(cmd, override_duration)
        self.active_tasks[task_key] = thread

        thread.status_update.connect(lambda text: self.export_splash.set_progress(self.export_splash.pbar.value(), text))
        thread.progress.connect(lambda v: self.export_splash.set_progress(v, self.export_splash.showMessageLabel.text()))
        thread.finished.connect(lambda success: self.handle_task_completion(task_key, out_path, success))
        thread.start()

    def kill_allocated_task(self, task_key):
        if task_key in self.active_tasks:
            thread = self.active_tasks.pop(task_key)
            thread.stop()
            if self.export_splash:
                self.export_splash.close()
                self.export_splash = None
            self.status_label.setText("Status: Ready")

    def stop_all_tasks(self):
        """Stop all active tasks during app shutdown"""
        for task_key in list(self.active_tasks.keys()):
            try:
                thread = self.active_tasks[task_key]
                thread.stop()
                thread.wait(1000)
            except Exception:
                pass
        self.active_tasks.clear()

    def handle_task_completion(self, task_key, out_path, success):
        self.active_tasks.pop(task_key, None)

        if self.export_splash:
            self.export_splash.close()
            self.export_splash = None

        self.status_label.setText("Status: Ready")

        if not success:
            QMessageBox.warning(self, "Processing Break", "Execution pipeline stopped or configuration error checked.")
            return

        if out_path and os.path.exists(out_path):
            self.load_video(out_path)
            QMessageBox.information(self, "Success", f"Output loaded successfully:\n{os.path.basename(out_path)}")

    def update_ui(self):
        try:
            # Handle fullscreen hover controls - detect mouse movement anywhere on screen
            if self.is_video_fullscreen:
                current_mouse_pos = QCursor.pos()
                
                # If mouse has moved, show controls and restart the hide timer
                if current_mouse_pos != self.last_mouse_pos:
                    self.show_fullscreen_controls()
                    self.last_mouse_pos = current_mouse_pos
            
            if self.player.is_active():
                dur = self.player.get_length()
                if dur > 0 and not self.is_user_sliding:
                    pos = self.player.get_position()
                    self.seek_slider.setValue(int(pos * 1000))
                    ms = self.player.get_time()
                    self.time_label.setText(f"{max(0, (ms//1000)//60):02d}:{(ms//1000)%60:02d}")
                    self.duration_label.setText(f"{(dur//1000)//60:02d}:{(dur//1000)%60:02d}")
                    if pos >= 0.99:
                        self.audio_service.stop_audio_monitoring()
                        self.seek_slider.setValue(0)
                        self.time_label.setText("00:00")
                        QTimer.singleShot(100, self.player.stop)
            else:
                # Not playing or paused - stop audio monitoring
                self.audio_service.stop_audio_monitoring()
        except Exception as e:
            print(f"UI loop fault: {e}")

    def on_slider_pressed(self): self.is_user_sliding = True
    def on_slider_released(self):
        self.is_user_sliding = False
        if self.player.is_active():
            self.player.set_position(self.seek_slider.value() / 1000.0)

    def toggle_video_fullscreen(self):
        """Toggle true window fullscreen mode while expanding the controls cleanly"""
        if not self.is_video_fullscreen:
            # 1. Cache the fact that we were maximized
            self._was_maximized_before_fullscreen = self.isMaximized()

            # 2. Hide side layout components
            self.sidebar.hide()
            self.stack.hide()
            self.filename_label.hide()

            # 3. Enter TRUE OS-level Fullscreen (Hides Taskbar and Title bar completely)
            self.showFullScreen()
            self.is_video_fullscreen = True

            # 4. Enforce 100% Width and clean styles on the control bar container
            self.playback_widget.setStyleSheet("""
                QWidget {
                    background-color: #1e1e1e;
                    color: #ffffff;
                    font-family: 'Segoe UI';
                    font-size: 12px;
                }
                QPushButton {
                    background-color: #37373d;
                    color: #ccc;
                    border: 1px solid #444;
                    border-radius: 3px;
                    padding: 4px 8px;
                    min-height: 26px;
                }
                QPushButton:hover {
                    background-color: #4d4d54;
                    color: white;
                }
                QSlider::groove:horizontal {
                    border: 1px solid #444;
                    height: 6px;
                    background: #333;
                    border-radius: 3px;
                }
                QSlider::sub-page:horizontal {
                    background: #0e639c;
                    border-radius: 3px;
                }
                QSlider::handle:horizontal {
                    background: #ffffff;
                    border: 1px solid #555;
                    width: 14px;
                    margin-top: -4px;
                    margin-bottom: -4px;
                    border-radius: 7px;
                }
            """)

            # Set the height to be generous enough to easily fit buttons and labels without truncation
            self.playback_widget.setFixedHeight(110)

            # Stretch inner layout margins to give breathing room against monitor edges
            if self.playback_widget.layout():
                self.playback_widget.layout().setContentsMargins(50, 15, 50, 15)
                self.playback_widget.layout().setSpacing(10)
                self.playback_widget.layout().activate()

            # Lock standard button widths
            self.back_btn.setMinimumWidth(75)
            self.play_btn.setMinimumWidth(75)
            self.pause_btn.setMinimumWidth(75)
            self.fwd_btn.setMinimumWidth(75)

            self.fullscreen_btn.setText("⬜ Exit Full")
            self.fullscreen_btn.setToolTip("Exit fullscreen (or press Esc)")
            self.controls_visible = False

            # Trigger auto-hide hover countdowns
            self.show_fullscreen_controls()

            self.setMouseTracking(True)
            self.last_mouse_pos = QCursor.pos()

        else:
            # --- TEARDOWN FULLSCREEN STATE ---
            if self.hide_controls_timer:
                self.hide_controls_timer.stop()

            self.is_video_fullscreen = False
            self.last_mouse_pos = QCursor.pos()  # Reset mouse position tracking

            # Restore exact previous window state cleanly
            # Always show normal first to reset window decorations properly
            self.showNormal()
            
            # Then restore to maximized state if that's what we were before
            if getattr(self, '_was_maximized_before_fullscreen', False):
                # Use a timer to defer the maximize call, allowing window manager to fully process normal state
                QTimer.singleShot(50, self.showMaximized)
            
            # Force window to update its decorations and bring to front
            self.raise_()
            self.activateWindow()

            # 1. Revert component stylesheets to layout defaults
            self.playback_widget.setStyleSheet("")
            self.playback_widget.setFixedHeight(100)

            if self.playback_widget.layout():
                self.playback_widget.layout().setContentsMargins(15, 10, 15, 10)
                self.playback_widget.layout().setSpacing(8)
                self.playback_widget.layout().activate()

            # 2. Re-verify the layout tree mapping position below the video player canvas
            target_layout = None
            for i in range(self.main_h_layout.count()):
                layout_item = self.main_h_layout.itemAt(i)
                if isinstance(layout_item, QVBoxLayout):
                    target_layout = layout_item
                    break

            if target_layout is not None:
                target_layout.removeWidget(self.playback_widget)
                target_layout.insertWidget(2, self.playback_widget)

            # 3. Bring standard UI panels back into frame view
            self.sidebar.show()
            self.stack.show()
            self.filename_label.show()

            self.fullscreen_btn.setText("🖥 Full Video")
            self.fullscreen_btn.setToolTip("Maximize video area, hide controls")
            self.controls_visible = True
            self.setMouseTracking(False)

            # 4. Refresh layout painting pipelines
            self.playback_widget.show()
            self.update()

    def hide_fullscreen_controls(self):
        """Hide controls smoothly in fullscreen mode"""
        if self.is_video_fullscreen and self.controls_visible:
            self.playback_widget.hide()
            self.controls_visible = False

    def show_fullscreen_controls(self):
        """Show controls in fullscreen mode and refresh stacking priority over VLC"""
        if self.is_video_fullscreen:
            if not self.controls_visible:
                self.playback_widget.show()
                self.playback_widget.raise_()
                self.controls_visible = True

            # Stop any pending hide timer and restart it
            if self.hide_controls_timer.isActive():
                self.hide_controls_timer.stop()
            self.hide_controls_timer.start(3000)

    def eventFilter(self, watched, event):
        """Monitors global application events to catch hover tracking values on top of native video engines."""
        if self.is_video_fullscreen:
            # Catch mouse movements anywhere over the video frame or the controller window bar itself
            if event.type() == QEvent.MouseMove:
                # If mouse is in the bottom 15% region of the viewport screen, surface the controls panel layout
                screen_geo = QApplication.primaryScreen().geometry()
                cursor_pos = QCursor.pos()
                trigger_zone_y = screen_geo.height() - 140

                if cursor_pos.y() >= trigger_zone_y or self.playback_widget.underMouse():
                    self.show_fullscreen_controls()
                else:
                    # If moving away from the control layer, start hide timer if not already running
                    if not self.playback_widget.underMouse():
                        if not self.hide_controls_timer.isActive():
                            self.hide_controls_timer.start(3000)

            # If mouse exits the full app window layout context frame entirely
            elif event.type() == QEvent.Leave and watched == self.playback_widget:
                if not self.hide_controls_timer.isActive():
                    self.hide_controls_timer.start(3000)

        return super().eventFilter(watched, event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape and self.is_video_fullscreen: self.toggle_video_fullscreen()
        else: super().keyPressEvent(event)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls(): event.acceptProposedAction()
        else: event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                p = url.toLocalFile()
                if os.path.exists(p):
                    self.load_video(p)
                    event.acceptProposedAction()
                    return

    def closeEvent(self, event):
        """Handle window close event - proper cleanup is now in PlayerService.stop()"""
        try:
            # Stop player (uses pause-based cleanup to prevent VLC hang)
            if hasattr(self, 'player_service') and self.player_service:
                self.player_service.stop()
        except Exception as e:
            print(f"Error stopping player on close: {e}")
        
        try:
            # Stop audio analyzer
            if hasattr(self, 'audio_service') and self.audio_service:
                if hasattr(self.audio_service, 'stop_analyzer'):
                    self.audio_service.stop_analyzer()
        except Exception as e:
            print(f"Error stopping audio on close: {e}")
        
        event.accept()
        # Exit fullscreen mode first if active
        try:
            if self.is_video_fullscreen:
                self.toggle_video_fullscreen()
        except Exception as e:
            print(f"Error exiting fullscreen: {e}")
            pass

        # Stop audio analyzer thread FIRST - this is blocking (use audio service)
        try:
            if hasattr(self, 'audio_service') and self.audio_service:
                self.audio_service.cleanup()
        except Exception as e:
            print(f"Error stopping audio analyzer: {e}")
            pass

        # Stop periodic UI updates
        try:
            self.timer.stop()
        except Exception: pass

        # Stop fullscreen timer
        try:
            if self.hide_controls_timer: self.hide_controls_timer.stop()
        except Exception: pass

        # Stop auto-reduce timer
        try:
            if hasattr(self, 'auto_reduce_timer'):
                self.auto_reduce_timer.stop()
        except Exception: pass

        # Clean up floating overlay references to prevent dangling handles
        try:
            if self.playback_widget:
                self.playback_widget.setParent(None)
                self.playback_widget.close()
        except Exception: pass

        # Stop all background tasks
        self.stop_all_tasks()

        # Clean up VLC player and instance
        try:
            self.player.stop()
            self.player.release()
        except Exception: pass

        event.accept()

def get_resource_path(filename):
    base_dir = sys._MEIPASS if hasattr(sys, '_MEIPASS') else os.path.dirname(__file__)
    possible_paths = [
        os.path.join(base_dir, filename),
        os.path.join(base_dir, "..", "resources", filename),
        os.path.join(base_dir, "config", filename)
    ]
    for p in possible_paths:
        if os.path.exists(p): return os.path.normpath(p)
    return os.path.normpath(possible_paths[0])

class ModernSplashScreen(QSplashScreen):
    def __init__(self, pixmap, show_cancel_button=False):
        super().__init__(pixmap, Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        self.pbar = QProgressBar(self)
        self.pbar.setGeometry(50, self.size().height() - 45, self.size().width() - 100, 10)
        self.pbar.setStyleSheet("""
            QProgressBar { border: 1px solid #444; border-radius: 4px; background-color: #1e1e1e; text-align: center; color: transparent; }
            QProgressBar::chunk { background-color: #2ecc71; width: 8px; }
        """)
        self.pbar.setRange(0, 100)

        self.showMessageLabel = QLabel(self)
        self.showMessageLabel.setGeometry(50, self.size().height() - 70, self.size().width() - 100, 20)
        self.showMessageLabel.setStyleSheet("color: white; font-size: 11px;")
        self.showMessageLabel.setAlignment(Qt.AlignCenter)

        if show_cancel_button:
            self.cancel_btn = QPushButton("✖ STOP", self)
            self.cancel_btn.setGeometry(self.size().width() - 75, 10, 65, 26)
            self.cancel_btn.setStyleSheet("background-color: #c0392b; color: white; font-weight: bold; font-size: 10px; border: none; border-radius: 3px;")

    def set_progress(self, value, message):
        self.pbar.setValue(value)
        self.showMessageLabel.setText(message)
        QApplication.processEvents()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    splash_path = get_resource_path("splash.png")
    if os.path.exists(splash_path):
        pix = QPixmap(splash_path).scaled(700, 350, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    else:
        pix = QPixmap(700, 350); pix.fill(QColor("#1e1e1e"))

    splash = ModernSplashScreen(pix)
    splash.show()
    splash.set_progress(20, "Initializing UI Components...")
    time.sleep(0.2)

    try:
        window = KaraokeApp()
        splash.set_progress(70, "Synchronizing Core Audio Engine Drivers...")
        time.sleep(0.2)
        window.showMaximized()
        splash.finish(window)
        sys.exit(app.exec())
    except Exception as e:
        print(f"Fatal Initialization Failure: {e}")
        sys.exit(1)
