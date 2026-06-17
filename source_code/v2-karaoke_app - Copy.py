import sys, os, vlc, subprocess, re, time, json
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, QFileDialog, 
    QLabel, QLineEdit, QHBoxLayout, QFrame, QScrollArea, 
    QMessageBox, QDoubleSpinBox, QProgressBar, QSlider, QStackedWidget, 
    QListWidget, QGridLayout, QSplashScreen, QDialog
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer, QRect, QEvent, QPoint
from PySide6.QtGui import QFont, QPixmap, QColor, QCursor, QPainter, QPen
import numpy as np
import sounddevice as sd
from collections import deque

class VideoFrame(QFrame):
    """Custom QFrame that propagates drag/drop events up to the application controller."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
    
    def dragEnterEvent(self, event):
        parent = self.parent()
        while parent and parent.parent(): parent = parent.parent()
        if parent and parent != self and hasattr(parent, 'dragEnterEvent'):
            parent.dragEnterEvent(event)
        else:
            event.ignore()
    
    def dropEvent(self, event):
        parent = self.parent()
        while parent and parent.parent(): parent = parent.parent()
        if parent and parent != self and hasattr(parent, 'dropEvent'):
            parent.dropEvent(event)
        else:
            event.ignore()

class AudioLevelMeter(QWidget):
    """Custom widget to display real-time audio output level in dB"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.db_level = -80.0
        self.level_percent = 0.0  # 0-100%
        self.setFixedHeight(30)
        self.setMinimumWidth(150)
        self.setMaximumWidth(180)
        
    def set_level(self, db_value):
        """Update the current dB level from audio stream"""
        # Clamp to -80 to 0 dB range
        self.db_level = max(-80.0, min(0.0, db_value))
        # Convert dB to percentage (0-100%)
        # -80dB = 0%, 0dB = 100%
        self.level_percent = ((self.db_level + 80.0) / 80.0) * 100.0
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Background
        painter.fillRect(self.rect(), QColor("#2d2d2d"))
        
        # Border
        painter.setPen(QPen(QColor("#444"), 1))
        painter.drawRect(0, 0, self.width() - 1, self.height() - 1)
        
        # Draw meter
        meter_width = self.width() - 6
        meter_height = self.height() - 6
        meter_x = 3
        meter_y = 3
        
        # Fill based on actual dB level
        fill_ratio = max(0, self.level_percent / 100.0)
        fill_width = max(0, meter_width * fill_ratio)
        
        # Draw meter background
        painter.fillRect(meter_x, meter_y, meter_width, meter_height, QColor("#1a1a1a"))
        
        # Draw filled portion with color based on level
        if fill_width > 0:
            if self.level_percent < 50:
                color = QColor("#2ecc71")  # Green for low levels
            elif self.level_percent < 85:
                color = QColor("#f39c12")  # Orange for medium levels
            else:
                color = QColor("#e74c3c")  # Red for high levels (clipping risk)
                
            painter.fillRect(meter_x, meter_y, fill_width, meter_height, color)
        
        # Draw threshold lines at 50% and 85%
        painter.setPen(QPen(QColor("#666"), 1))
        line_50_x = meter_x + (meter_width * 0.5)
        line_85_x = meter_x + (meter_width * 0.85)
        painter.drawLine(int(line_50_x), meter_y - 2, int(line_50_x), meter_y + meter_height + 2)
        painter.drawLine(int(line_85_x), meter_y - 2, int(line_85_x), meter_y + meter_height + 2)
        
        # Draw text - show dB and percentage
        painter.setPen(QColor("#ffffff"))
        painter.setFont(QFont("Segoe UI", 7, QFont.Bold))
        text = f"{self.db_level:.1f}dB ({self.level_percent:.0f}%)"
        painter.drawText(self.rect(), Qt.AlignCenter, text)

class AudioAnalyzerThread(QThread):
    """Thread to capture and analyze real-time audio output levels"""
    level_updated = Signal(float)  # Emit dB value
    clip_warning = Signal()  # Emit when level exceeds 90%
    
    def __init__(self):
        super().__init__()
        self.running = True
        self.is_playing = False  # Track if music is playing
        self.audio_buffer = np.array([], dtype=np.float32)
        self.buffer_size = 4410  # ~100ms at 44.1kHz
        self.min_dB = -80.0
        self.max_dB = 0.0
        self.silence_count = 0
        
    def set_playing(self, is_playing):
        """Set whether audio should be monitored"""
        self.is_playing = is_playing
        self.silence_count = 0
        
    def audio_callback(self, indata, frames, time, status):
        """Callback for audio stream - capture audio data"""
        if status or not self.is_playing:
            return
        try:
            # Get mono mix of audio
            if indata.shape[1] > 1:
                audio_data = np.mean(indata, axis=1)
            else:
                audio_data = indata[:, 0]
            
            # Add to buffer
            self.audio_buffer = np.append(self.audio_buffer, audio_data)
            
            # Keep buffer size manageable
            if len(self.audio_buffer) > self.buffer_size * 2:
                self.audio_buffer = self.audio_buffer[-self.buffer_size:]
        except Exception as e:
            print(f"Audio callback error: {e}")
    
    def run(self):
        """Monitor audio levels continuously"""
        try:
            # Start audio stream
            with sd.InputStream(callback=self.audio_callback, channels=2, samplerate=44100, 
                              blocksize=2048, latency='low'):
                while self.running:
                    try:
                        # Only process if playing
                        if self.is_playing and len(self.audio_buffer) >= self.buffer_size // 2:
                            recent_audio = self.audio_buffer[-self.buffer_size:]
                            
                            # Calculate RMS (Root Mean Square)
                            rms = np.sqrt(np.mean(recent_audio ** 2))
                            
                            # Convert to dB (20 * log10(rms))
                            if rms > 0:
                                db_level = 20 * np.log10(rms + 1e-10)
                            else:
                                db_level = -80.0
                            
                            # Clamp to range
                            db_level = max(self.min_dB, min(self.max_dB, db_level))
                            
                            # Only emit if not silence
                            if db_level > -70:
                                self.level_updated.emit(db_level)
                                
                                # Check for clipping (> 90%)
                                level_percent = ((db_level + 80.0) / 80.0) * 100.0
                                if level_percent > 90:
                                    self.clip_warning.emit()
                                self.silence_count = 0
                            else:
                                self.silence_count += 1
                                if self.silence_count > 5:  # After 250ms of silence, reset
                                    self.level_updated.emit(-80.0)
                        elif not self.is_playing:
                            # Reset to silent when not playing
                            self.level_updated.emit(-80.0)
                            self.audio_buffer = np.array([], dtype=np.float32)
                        
                        self.msleep(50)  # Update every 50ms
                    except Exception as e:
                        print(f"Level calculation error: {e}")
                        self.msleep(100)
        except Exception as e:
            print(f"Audio stream error: {e}")
    
    def stop(self):
        """Stop the audio analyzer"""
        self.running = False
        self.wait(500)

class SettingsDialog(QDialog):
    """Unified Schema-Driven Settings Dialog Window"""
    def __init__(self, parent=None, settings_manager=None):
        super().__init__(parent)
        self.manager = settings_manager
        self.temp_states = dict(self.manager.settings)
        
        self.setWindowTitle("⚙️ Settings Configuration")
        self.resize(750, 500)
        self.setModal(True)
        self.setStyleSheet("background-color: #1e1e1e; color: #ffffff;")
        
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        self.sidebar = QFrame()
        self.sidebar.setFixedWidth(200)
        self.sidebar.setStyleSheet("background-color: #252526; border-right: 1px solid #333;")
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(0, 15, 0, 0)
        
        self.settings_list = QListWidget()
        self.settings_list.setStyleSheet("""
            QListWidget { border: none; background: transparent; outline: 0; color: #ccc; }
            QListWidget::item { height: 45px; padding-left: 15px; }
            QListWidget::item:selected { background-color: #37373d; color: white; border-left: 4px solid #2ecc71; }
        """)
        sidebar_layout.addWidget(self.settings_list)
        sidebar_layout.addStretch()
        
        self.right_panel = QFrame()
        self.right_panel.setStyleSheet("background-color: #1e1e1e;")
        self.right_layout = QVBoxLayout(self.right_panel)
        self.right_layout.setContentsMargins(25, 25, 25, 25)
        
        self.settings_stack = QStackedWidget()
        self.right_layout.addWidget(self.settings_stack)
        
        self.display_fields = {}
        
        self.schema = {
            "📁 Paths & Storage": [
                {"key": "base_directory", "label": "Base Workspace Library:", "type": "directory", "desc": "Default repository lookup target root path."},
                {"key": "download_directory", "label": "Media Download Directory:", "type": "directory", "desc": "Location where incoming media stream files are downloaded."}
            ],
            "🛠️ System Binaries": [
                {"key": "ffmpeg_path", "label": "FFmpeg Core Binary Path:", "type": "file", "desc": "Target path targeting local executable 'ffmpeg'."},
                {"key": "ffprobe_path", "label": "FFprobe Context Parser Path:", "type": "file", "desc": "Target location targeting local executable 'ffprobe'."},
                {"key": "ytdlp_path", "label": "YT-DLP Extract Target Path:", "type": "file", "desc": "Target location pointing to your engine binary 'yt-dlp'."}
            ]
        }
        
        self.build_pages()
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.ok_btn = QPushButton("Save"); self.ok_btn.setFixedSize(90, 35)
        self.cancel_btn = QPushButton("Cancel"); self.cancel_btn.setFixedSize(90, 35)
        self.ok_btn.setStyleSheet("background-color: #0e639c; color: white; font-weight: bold; border-radius: 3px;")
        self.cancel_btn.setStyleSheet("background-color: #444; color: white; border-radius: 3px;")
        
        self.ok_btn.clicked.connect(self.accept_changes)
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.ok_btn)
        btn_layout.addWidget(self.cancel_btn)
        self.right_layout.addLayout(btn_layout)
        
        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(self.right_panel)
        
        self.settings_list.setCurrentRow(0)
        self.settings_list.currentRowChanged.connect(self.settings_stack.setCurrentIndex)

    def build_pages(self):
        for page_title, properties in self.schema.items():
            self.settings_list.addItem(page_title)
            page_widget = QWidget()
            page_layout = QVBoxLayout(page_widget)
            page_layout.setContentsMargins(0, 0, 0, 0)
            page_layout.setAlignment(Qt.AlignTop)
            
            title_lbl = QLabel(f"<b>{page_title.upper()}</b>")
            title_lbl.setFont(QFont("Segoe UI", 12, QFont.Bold))
            page_layout.addWidget(title_lbl)
            page_layout.addSpacing(15)
            
            for prop in properties:
                row_container = QWidget()
                row_layout = QVBoxLayout(row_container)
                row_layout.setContentsMargins(0, 5, 0, 10)
                
                label = QLabel(prop["label"])
                label.setFont(QFont("Segoe UI", 9, QFont.Bold))
                row_layout.addWidget(label)
                
                input_row = QHBoxLayout()
                edit_field = QLineEdit(str(self.temp_states.get(prop["key"], "")))
                edit_field.setStyleSheet("background-color: #2d2d2d; border: 1px solid #444; padding: 6px; color: #90ee90; border-radius: 3px;")
                self.display_fields[prop["key"]] = edit_field
                
                browse_btn = QPushButton("📁 Browse...")
                browse_btn.setFixedSize(90, 28)
                browse_btn.setStyleSheet("background-color: #3a3a3a; color: white;")
                browse_btn.clicked.connect(lambda checked=False, k=prop["key"], t=prop["type"]: self.handle_browse(k, t))
                
                input_row.addWidget(edit_field)
                input_row.addWidget(browse_btn)
                row_layout.addLayout(input_row)
                
                desc_lbl = QLabel(f"<i>{prop['desc']}</i>")
                desc_lbl.setStyleSheet("color: #777; font-size: 11px;")
                row_layout.addWidget(desc_lbl)
                
                page_layout.addWidget(row_container)
                
            page_layout.addStretch()
            self.settings_stack.addWidget(page_widget)

    def handle_browse(self, key, path_type):
        current_val = self.display_fields[key].text()
        if path_type == "directory":
            res = QFileDialog.getExistingDirectory(self, "Select Folder Location", current_val)
        else:
            res, _ = QFileDialog.getOpenFileName(self, "Locate Binary Executable", current_val, "Executables (*.exe *.*)")
        
        if res:
            normalized = os.path.normpath(res)
            self.temp_states[key] = normalized
            self.display_fields[key].setText(normalized)

    def accept_changes(self):
        for key in self.display_fields.keys():
            self.temp_states[key] = self.display_fields[key].text().strip()
        self.manager.settings.update(self.temp_states)
        self.manager.save_settings()
        self.accept()

class ProcessThread(QThread):
    progress = Signal(int)
    finished = Signal(bool)
    status_update = Signal(str)

    def __init__(self, cmd, duration=0):
        super().__init__()
        self.cmd = cmd
        self.duration = duration
        self.process = None
        self.is_killed = False

    def run(self):
        startupinfo = None
        creationflags = 0
        if sys.platform == "win32":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0
            creationflags = 0x08000000
            
        self.process = subprocess.Popen(
            self.cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT,  
            universal_newlines=True, 
            startupinfo=startupinfo,
            creationflags=creationflags,
            bufsize=1
        )
        
        buffer = ""
        try:
            while True:
                if self.is_killed: break
                
                char = self.process.stdout.read(1)
                if not char:
                    if self.process.poll() is not None: break
                    continue
                
                if char == '\n' or char == '\r':
                    line = buffer.strip()
                    buffer = ""
                    if not line: continue
                    
                    if "[download]" in line and "%" in line:
                        match = re.search(r"\[download\]\s+([0-9.]+)%", line)
                        if match:
                            percent = int(float(match.group(1)))
                            self.progress.emit(min(percent, 100))
                            self.status_update.emit(f"Downloading Assets... {percent}%")
                    
                    elif "time=" in line and self.duration > 0:
                        time_match = re.search(r"time=(\d+):(\d+):(\d+\.\d+)", line)
                        if time_match:
                            h, m, s = time_match.groups()
                            current_sec = int(h) * 3600 + int(m) * 60 + float(s)
                            percent = int((current_sec / self.duration) * 100)
                            self.progress.emit(min(percent, 100))
                            self.status_update.emit(f"Converting Video Layout... {percent}%")
                else:
                    buffer += char
        except Exception as e:
            print(f"Extraction monitoring thread exception: {e}")

        self.cleanup_process()
        self.finished.emit(not self.is_killed and self.process.returncode == 0)

    def cleanup_process(self):
        if self.process:
            if self.is_killed:
                try:
                    self.process.terminate()
                    self.process.kill()
                except: pass
            try:
                self.process.wait(timeout=0.5)
            except: pass
            if self.process.stdout:
                try: self.process.stdout.close()
                except: pass

    def stop(self):
        self.is_killed = True
        self.cleanup_process()

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

        vlc_args = ["--aout=directx"] if sys.platform == "win32" else []
        self.instance = vlc.Instance(vlc_args)
        self.player = self.instance.media_player_new()

        self.setup_ui()
        self.nav_list.setCurrentRow(0)
        
        self.timer = QTimer()
        self.timer.setInterval(200)
        self.timer.timeout.connect(self.update_ui)
        self.timer.start()
        self.is_user_sliding = False

        # Fullscreen Hover Controls Logic Setup
        self.hide_controls_timer = QTimer()
        self.hide_controls_timer.setInterval(2500)  # Auto-hide after 2.5 seconds
        self.hide_controls_timer.timeout.connect(self.hide_fullscreen_controls)
        
        self.fullscreen_timer = None
        self.fullscreen_mouse_timer = None
        
        self.setAcceptDrops(True)
        self.video_frame.setAcceptDrops(True)
        
        # Monitor mouse events across the video framework structure
        self.video_frame.installEventFilter(self)
        self.playback_widget.installEventFilter(self)
        
        # Initialize and start audio analyzer thread
        self.audio_analyzer = AudioAnalyzerThread()
        self.audio_analyzer.level_updated.connect(self.on_audio_level_updated)
        self.audio_analyzer.start()
        
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
            "ytdlp_path": "yt-dlp"
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
        self.main_h_layout = QHBoxLayout(self)
        self.main_h_layout.setContentsMargins(0, 0, 0, 0)
        self.main_h_layout.setSpacing(0)

        self.stack = QStackedWidget()
        self.stack.addWidget(self.create_download_page())   
        self.stack.addWidget(self.create_pitch_page())      
        self.stack.addWidget(self.create_extra_page())      

        self.sidebar = QFrame()
        self.sidebar.setFixedWidth(200)
        self.sidebar.setStyleSheet("background-color: #252526; border-right: 1px solid #333;")
        side_layout = QVBoxLayout(self.sidebar)
        side_layout.setContentsMargins(0, 0, 0, 0)
        
        logo = QLabel("KARAOKE STUDIO PRO")
        logo.setFont(QFont("Segoe UI", 12, QFont.Bold))
        logo.setContentsMargins(15, 20, 10, 20)
        side_layout.addWidget(logo)

        self.nav_list = QListWidget()
        self.nav_list.setFixedHeight(110)
        self.nav_list.setStyleSheet("""
            QListWidget { border: none; background: transparent; outline: 0; color: #ccc; }
            QListWidget::item { height: 50px; padding-left: 15px; }
            QListWidget::item:selected { background-color: #37373d; color: white; border-left: 4px solid #2ecc71; }
        """)
        self.nav_list.addItems(["📥 Downloader", "🎬 Pitch & Speed"])
        self.nav_list.currentRowChanged.connect(self.handle_navigation_change)
        side_layout.addWidget(self.nav_list)

        self.extra_tools_toggle_btn = QPushButton("▶ 🛠 Extra Tools")
        self.extra_tools_toggle_btn.setStyleSheet("background-color: #37373d; color: #ccc; padding: 10px; border: 1px solid #444; border-radius: 3px; text-align: left;")
        self.extra_tools_toggle_btn.clicked.connect(self.toggle_extra_tools)
        self.extra_tools_is_expanded = False
        side_layout.addWidget(self.extra_tools_toggle_btn)

        self.extra_tools_container = QFrame()
        self.extra_tools_container.setVisible(False)
        extra_tools_container_layout = QVBoxLayout(self.extra_tools_container)
        extra_tools_container_layout.setContentsMargins(0, 5, 0, 0)
        
        self.widen_video_btn = QPushButton("📐 Widen Video")
        self.widen_video_btn.setStyleSheet("background-color: #2d2d2d; color: #aaa; padding: 8px 15px; border: none; text-align: left; margin-left: 15px; margin-right: 10px;")
        self.widen_video_btn.clicked.connect(lambda: self.handle_navigation_change(2))
        extra_tools_container_layout.addWidget(self.widen_video_btn)
        side_layout.addWidget(self.extra_tools_container)

        line = QFrame(); line.setFrameShape(QFrame.HLine); line.setStyleSheet("color: #333; margin: 5px 15px;")
        side_layout.addWidget(line)

        self.history_toggle_btn = QPushButton("▶ History")
        self.history_toggle_btn.setStyleSheet("background-color: #37373d; color: #ccc; padding: 10px; border: 1px solid #444; border-radius: 3px; text-align: left;")
        self.history_toggle_btn.clicked.connect(self.toggle_history)
        self.history_is_expanded = False
        side_layout.addWidget(self.history_toggle_btn)

        self.history_container = QFrame()
        self.history_container.setVisible(False)
        history_container_layout = QVBoxLayout(self.history_container)
        history_container_layout.setContentsMargins(0, 0, 0, 0)
        
        hist_header = QHBoxLayout()
        history_label = QLabel("RECENT FILES")
        history_label.setFont(QFont("Segoe UI", 8, QFont.Bold))
        history_label.setStyleSheet("color: #666; margin-left: 15px;")
        
        self.clear_hist_btn = QPushButton("Clear")
        self.clear_hist_btn.setFixedSize(45, 18)
        self.clear_hist_btn.setStyleSheet("font-size: 9px; background-color: #333; color: #888; border-radius: 2px;")
        self.clear_hist_btn.clicked.connect(self.clear_history)
        
        hist_header.addWidget(history_label)
        hist_header.addStretch()
        hist_header.addWidget(self.clear_hist_btn)
        hist_header.addSpacing(10)
        history_container_layout.addLayout(hist_header)

        self.history_list = QListWidget()
        self.history_list.setStyleSheet("""
            QListWidget { border: none; background: transparent; outline: 0; color: #aaa; font-size: 10px; }
            QListWidget::item { height: 30px; padding-left: 15px; border-bottom: 1px solid #2d2d2d; }
            QListWidget::item:hover { background-color: #37373d; color: white; }
        """)
        self.history_list.itemDoubleClicked.connect(lambda item: self.load_video(item.toolTip()))
        history_container_layout.addWidget(self.history_list)
        side_layout.addWidget(self.history_container)
        
        self.load_history_from_disk()
        side_layout.addStretch(1)
        
        self.settings_btn = QPushButton("⚙️ Settings")
        self.settings_btn.setStyleSheet("background-color: #37373d; color: #ccc; padding: 10px; border: 1px solid #444; border-radius: 3px;")
        self.settings_btn.clicked.connect(self.open_settings)
        side_layout.addWidget(self.settings_btn)
        
        self.status_label = QLabel("Status: Ready")
        self.status_label.setStyleSheet("color: #ffffff; padding: 5px 10px; font-size: 12px; font-weight: bold; border-top: 1px solid #333;")
        self.status_label.setWordWrap(True)
        side_layout.addWidget(self.status_label)
        self.main_h_layout.addWidget(self.sidebar)

        self.content_container = QVBoxLayout()
        self.video_frame = VideoFrame()
        self.video_frame.setStyleSheet("background-color: #000;")
        self.video_frame.setMinimumHeight(420)
        self.content_container.addWidget(self.video_frame, 10)

        self.filename_label = QLabel("No file loaded")
        self.filename_label.setStyleSheet("color: #ccc; padding: 5px 15px; font-size: 12px; background-color: #1e1e1e;")
        self.content_container.addWidget(self.filename_label)

        self.playback_widget = QWidget()
        self.playback_widget.setLayout(self.create_playback_bar())
        self.playback_widget.setFixedHeight(95)
        self.content_container.addWidget(self.playback_widget)
        
        self.content_container.addWidget(self.stack)
        self.content_container.addStretch()
        self.main_h_layout.addLayout(self.content_container)

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

    def create_playback_bar(self):
        container = QVBoxLayout(); container.setContentsMargins(15, 5, 15, 5)
        seek_row = QHBoxLayout()
        self.time_label = QLabel("00:00")
        self.seek_slider = QSlider(Qt.Horizontal); self.seek_slider.setRange(0, 1000)
        self.seek_slider.sliderPressed.connect(self.on_slider_pressed)
        self.seek_slider.sliderReleased.connect(self.on_slider_released)
        self.duration_label = QLabel("00:00")
        seek_row.addWidget(self.time_label); seek_row.addWidget(self.seek_slider); seek_row.addWidget(self.duration_label)
        
        ctrl_row = QHBoxLayout()
        self.back_btn = QPushButton("⏪ -10s"); self.back_btn.clicked.connect(lambda: self.jump_time(-10000))
        self.play_btn = QPushButton("▶ Play"); self.play_btn.clicked.connect(self.player.play)
        self.pause_btn = QPushButton("⏸ Pause"); self.pause_btn.clicked.connect(self.player.pause)
        self.fwd_btn = QPushButton("+10s ⏩"); self.fwd_btn.clicked.connect(lambda: self.jump_time(10000))

        self.mute_btn = QPushButton("🔊"); self.mute_btn.setFixedWidth(35); self.mute_btn.clicked.connect(self.toggle_mute)
        self.vol_slider = QSlider(Qt.Horizontal); self.vol_slider.setRange(0, 100); self.vol_slider.setValue(80); self.vol_slider.setFixedWidth(120)
        self.vol_slider.valueChanged.connect(self.set_volume)
        self.vol_label = QLabel("80%"); self.vol_label.setFixedWidth(40)
        
        # Add audio level meter
        self.audio_level_meter = AudioLevelMeter()
        self.audio_level_meter.set_level(-80.0)  # Initialize to silent
        self.audio_level_label = QLabel("Audio:")
        self.audio_level_label.setStyleSheet("color: #ccc; font-size: 10px;")

        for w in [self.back_btn, self.play_btn, self.pause_btn, self.fwd_btn]: ctrl_row.addWidget(w)
        ctrl_row.addStretch()
        
        # Add audio level meter to control row
        ctrl_row.addWidget(self.audio_level_label)
        ctrl_row.addWidget(self.audio_level_meter)
        ctrl_row.addSpacing(10)
        
        self.fullscreen_btn = QPushButton("🖥 Full Video"); self.fullscreen_btn.setFixedWidth(95)
        self.fullscreen_btn.clicked.connect(self.toggle_video_fullscreen)
        ctrl_row.addWidget(self.fullscreen_btn)
        
        for w in [self.mute_btn, self.vol_slider, self.vol_label]: ctrl_row.addWidget(w)
        container.addLayout(seek_row)
        container.addSpacing(5)
        container.addLayout(ctrl_row)
        return container

    def create_download_page(self):
        page = QWidget(); layout = QVBoxLayout(page)
        layout.setContentsMargins(10, 5, 10, 5)
        grid = QGridLayout()
        
        self.load_btn = QPushButton("📂 Open File..."); self.load_btn.setFixedSize(110, 30)
        self.load_btn.clicked.connect(lambda: self.load_video())
        grid.addWidget(self.load_btn, 1, 0)

        sep = QFrame(); sep.setFrameShape(QFrame.VLine); sep.setStyleSheet("color: #3a3a3a;")
        grid.addWidget(sep, 1, 1)

        grid.addWidget(QLabel("<b>YouTube / Stream Target URL:</b>"), 0, 2)
        self.url_input = QLineEdit(); self.url_input.setPlaceholderText("Paste network audio/video stream links here...")
        self.url_input.setStyleSheet("background-color: #333; border: 1px solid #555; padding: 5px; color: white;")
        self.url_input.setFixedSize(700, 30)
        grid.addWidget(self.url_input, 1, 2)

        dl_btn = QPushButton("Download and Load"); dl_btn.setFixedSize(140, 30)
        dl_btn.setStyleSheet("background-color: #2ecc71; font-weight: bold; color: white;")
        dl_btn.clicked.connect(lambda: self.download_video(from_widen_tab=False))
        grid.addWidget(dl_btn, 1, 3)

        layout.addLayout(grid)       
        layout.addStretch()
        return page

    def create_pitch_page(self):
        page = QWidget(); layout = QVBoxLayout(page)
        p_row = QHBoxLayout(); p_row.addWidget(QLabel("Pitch Shifter Matrix Shift:"))
        self.pitch_minus = QPushButton("-"); self.pitch_minus.setFixedWidth(30)
        self.pitch_input = QDoubleSpinBox(); self.pitch_input.setRange(-12.0, 12.0); self.pitch_input.setValue(0.0); self.pitch_input.setSuffix(" semitones"); self.pitch_input.setSingleStep(0.5) 
        self.pitch_plus = QPushButton("+"); self.pitch_plus.setFixedWidth(30)
        self.pitch_reset = QPushButton("↺"); self.pitch_reset.setFixedWidth(40)
        
        self.pitch_minus.clicked.connect(lambda: self.pitch_input.setValue(self.pitch_input.value() - 1.0))
        self.pitch_plus.clicked.connect(lambda: self.pitch_input.setValue(self.pitch_input.value() + 1.0))
        self.pitch_reset.clicked.connect(lambda: self.pitch_input.setValue(0.0))
        
        for w in [self.pitch_minus, self.pitch_input, self.pitch_plus, self.pitch_reset]: p_row.addWidget(w)
        p_row.addStretch()

        s_row = QHBoxLayout(); s_row.addWidget(QLabel("Playback Velocity Frequency:"))
        self.speed_minus = QPushButton("-"); self.speed_minus.setFixedWidth(30)
        self.speed_input = QDoubleSpinBox(); self.speed_input.setRange(0.5, 2.0); self.speed_input.setValue(1.0); self.speed_input.setSuffix("x Timeline"); self.speed_input.setSingleStep(0.05) 
        self.speed_plus = QPushButton("+"); self.speed_plus.setFixedWidth(30)
        self.speed_reset = QPushButton("↺"); self.speed_reset.setFixedWidth(40)
        
        self.speed_minus.clicked.connect(lambda: self.speed_input.setValue(round(self.speed_input.value() - 0.1, 2)))
        self.speed_plus.clicked.connect(lambda: self.speed_input.setValue(round(self.speed_input.value() + 0.1, 2)))
        self.speed_reset.clicked.connect(lambda: self.speed_input.setValue(1.0))
        self.speed_input.valueChanged.connect(lambda v: self.player.set_rate(v))
        
        for w in [self.speed_minus, self.speed_input, self.speed_plus, self.speed_reset]: s_row.addWidget(w)
        s_row.addStretch()

        self.export_btn = QPushButton("Export Unified Master Render File"); self.export_btn.setStyleSheet("background-color: #0e639c; height: 45px; font-weight: bold; color: white;")
        self.export_btn.clicked.connect(self.export_video)
        layout.addLayout(p_row); layout.addLayout(s_row); layout.addWidget(self.export_btn); layout.addStretch()
        return page

    def create_extra_page(self):
        page = QWidget(); layout = QVBoxLayout(page)
        layout.setContentsMargins(10, 5, 10, 5)
        
        title = QLabel("<b>📐 ASPECT-RATIO LAYOUT PAD ENGINE</b>")
        title.setFont(QFont("Segoe UI", 11, QFont.Bold))
        layout.addWidget(title)
        
        grid = QGridLayout()
        widen_file_btn = QPushButton("📂 Open Widen File..."); widen_file_btn.setFixedSize(140, 30)
        widen_file_btn.clicked.connect(self.browse_widen_video)
        grid.addWidget(widen_file_btn, 1, 0)

        sep = QFrame(); sep.setFrameShape(QFrame.VLine); sep.setStyleSheet("color: #3a3a3a;")
        grid.addWidget(sep, 1, 1)

        grid.addWidget(QLabel("<b>YouTube / Stream Link:</b>"), 0, 2)
        self.widen_url_input = QLineEdit(); self.widen_url_input.setPlaceholderText("Paste target URL link here to download directly to Widen context...")
        self.widen_url_input.setStyleSheet("background-color: #333; border: 1px solid #555; padding: 5px; color: white;")
        self.widen_url_input.setFixedSize(540, 30)
        grid.addWidget(self.widen_url_input, 1, 2)

        widen_dl_btn = QPushButton("Download & Queue"); widen_dl_btn.setFixedSize(140, 30)
        widen_dl_btn.setStyleSheet("background-color: #2ecc71; font-weight: bold; color: white;")
        widen_dl_btn.clicked.connect(lambda: self.download_video(from_widen_tab=True))
        grid.addWidget(widen_dl_btn, 1, 3)
        layout.addLayout(grid)
        
        self.widen_file_status_label = QLabel("Queued File for Widening: None (Will fallback to currently loaded player asset if blank)")
        self.widen_file_status_label.setStyleSheet("color: #e67e22; font-style: italic; padding: 5px 0px;")
        layout.addWidget(self.widen_file_status_label)
        layout.addSpacing(10)
        
        self.widen_exec_btn = QPushButton("Scale Active Video to Wide 16:9 Canvas")
        self.widen_exec_btn.setStyleSheet("background-color: #e67e22; height: 45px; font-weight: bold; font-size: 13px; color: white; border-radius: 4px;")
        self.widen_exec_btn.clicked.connect(self.widen_active_video_canvas)
        layout.addWidget(self.widen_exec_btn)
        
        layout.addStretch()
        return page

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
        dialog = SettingsDialog(self, self)
        dialog.exec()

    def set_volume(self, value):
        self.player.audio_set_volume(value); self.vol_label.setText(f"{value}%")
        self.mute_btn.setText("🔊" if value > 0 else "🔇")

    def toggle_mute(self):
        m = not self.player.audio_get_mute(); self.player.audio_set_mute(m)
        self.mute_btn.setText("🔇" if m else "🔊")
    
    def on_audio_level_updated(self, db_level):
        """Update meter with real audio output level"""
        if hasattr(self, 'audio_level_meter'):
            self.audio_level_meter.set_level(db_level)
            
            # Check for clipping and auto-reduce
            level_percent = ((db_level + 80.0) / 80.0) * 100.0
            if level_percent > 90 and self.vol_slider.value() > 20 and not self.auto_reduce_active:
                self.auto_reduce_active = True
                # Reduce volume by 5%
                new_volume = max(20, self.vol_slider.value() - 5)
                self.vol_slider.setValue(new_volume)
                self.status_label.setText(f"Status: Auto-reduced volume to {new_volume}% (audio level: {level_percent:.0f}%)")
            elif level_percent < 70 and self.auto_reduce_active:
                # Reset auto-reduce flag when levels are safe
                self.auto_reduce_active = False

    def jump_time(self, ms):
        if self.player.get_state() in [vlc.State.Playing, vlc.State.Paused]:
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
        if not file_path:
            f, _ = QFileDialog.getOpenFileName(
                self, "Open Audio/Video Track Resource", self.settings["base_directory"],
                "Media Feeds (*.mp4 *.avi *.mkv *.mov *.mp3 *.wav *.aac *.m4a *.webm);;All System Inputs (*.*)"
            )
            if not f: return
            file_path = f
        
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
        
        # Stop audio monitoring when loading
        self.audio_analyzer.set_playing(False)
        
        try:
            self.player.stop()
            
            loader.set_progress(40, "Mapping Core Encoders...")
            self.video_path = self._pending_video_path
            media = self.instance.media_new(os.path.abspath(self.video_path))
            self.player.set_media(media)
            
            win_id = int(self.video_frame.winId())
            if sys.platform == "win32": self.player.set_hwnd(win_id)
            else: self.player.set_xwindow(win_id)
            
            loader.set_progress(70, "Synchronizing Canvas Matrix Pipeline...")
            
            self.player.play()
            self.time_label.setText("00:00")
            
            retries = 0
            while self.player.audio_get_track() == -1 and retries < 20:
                time.sleep(0.05)
                QApplication.processEvents()
                retries += 1
                
            self.player.audio_set_volume(self.vol_slider.value())
            
            # Start audio monitoring after playback begins
            self.audio_analyzer.set_playing(True)
            
            self.finish_loading(loader)
            
        except Exception as e:
            print(f"Engine Fault: {e}")
            loader.close()

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
        
        self.status_label.setText("Status: Deploying Downloader Task Pipes...")
        loading_path = get_resource_path("Loading.png")
        pix = QPixmap(loading_path).scaled(600, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation) if os.path.exists(loading_path) else QPixmap(600, 300)
        if not os.path.exists(loading_path): pix.fill(QColor("#1e1e1e"))
        
        task_key = "widen_download" if from_widen_tab else "downloader"
        self.download_splash = ModernSplashScreen(pix, show_cancel_button=True)
        self.download_splash.cancel_btn.clicked.connect(lambda: self.kill_allocated_task(task_key))
        self.download_splash.show()
        QApplication.processEvents()
        
        out_pattern = os.path.join(self.settings["download_directory"], "%(title)s.%(ext)s").replace("\\", "/")
        cmd = [self.settings["ytdlp_path"], "-f", "bv[vcodec^=avc1]+ba[acodec^=mp4a]/b", "-o", out_pattern, "--force-overwrites", "--no-warnings", url]
        
        self.launch_async_task(cmd, None, task_key)

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
               "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", abs_out]
        
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
        
        duration = override_duration
        if duration == 0 and task_key in ["downloader", "widen_download"] and self.player.get_length() > 0:
            duration = self.player.get_length() / 1000.0
            
        thread = ProcessThread(cmd, duration)
        self.active_tasks[task_key] = thread
        
        if task_key in ["downloader", "widen_download"]:
            thread.status_update.connect(lambda text: self.download_splash.set_progress(self.download_splash.pbar.value(), text))
            thread.progress.connect(lambda v: self.download_splash.set_progress(v, self.download_splash.showMessageLabel.text()))
        else:
            thread.status_update.connect(lambda text: self.export_splash.set_progress(self.export_splash.pbar.value(), text))
            thread.progress.connect(lambda v: self.export_splash.set_progress(v, self.export_splash.showMessageLabel.text()))
            
        thread.finished.connect(lambda success: self.handle_task_completion(task_key, out_path, success))
        thread.start()

    def kill_allocated_task(self, task_key):
        if task_key in self.active_tasks:
            thread = self.active_tasks[task_key]
            thread.stop()
            thread.wait(1000)
            self.active_tasks.pop(task_key, None)

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
        
        if task_key in ["downloader", "widen_download"] and self.download_splash:
            self.download_splash.close(); self.download_splash = None
        elif self.export_splash:
            self.export_splash.close(); self.export_splash = None
            
        self.status_label.setText("Status: Ready")
        
        if not success:
            QMessageBox.warning(self, "Processing Break", "Execution pipeline stopped or configuration error checked.")
            return
            
        if task_key in ["downloader", "widen_download"]:
            try:
                targets = [f for f in os.listdir(self.settings["download_directory"]) if f.endswith('.mp4')]
                if targets:
                    latest = max(targets, key=lambda x: os.path.getmtime(os.path.join(self.settings["download_directory"], x)))
                    full_p = os.path.normpath(os.path.join(self.settings["download_directory"], latest))
                    
                    if task_key == "widen_download":
                        self.widen_url_input.clear()
                        self.widen_tab_video_path = full_p
                        self.widen_file_status_label.setText(f"Queued File for Widening: {os.path.basename(full_p)}")
                        self.load_video(full_p)
                    else:
                        self.url_input.clear()
                        self.load_video(full_p)
            except Exception as e:
                QMessageBox.critical(self, "File Capture Error", f"Failed capturing downloaded file: {e}")
        else:
            if out_path and os.path.exists(out_path):
                self.load_video(out_path)
                QMessageBox.information(self, "Success", f"Output loaded successfully:\n{os.path.basename(out_path)}")

    def update_ui(self):
        try:
            state = self.player.get_state()
            if state in [vlc.State.Playing, vlc.State.Paused]:
                dur = self.player.get_length()
                if dur > 0 and not self.is_user_sliding:
                    pos = self.player.get_position()
                    self.seek_slider.setValue(int(pos * 1000))
                    ms = self.player.get_time()
                    self.time_label.setText(f"{max(0, (ms//1000)//60):02d}:{(ms//1000)%60:02d}")
                    self.duration_label.setText(f"{(dur//1000)//60:02d}:{(dur//1000)%60:02d}")
                    if pos >= 0.99:
                        self.audio_analyzer.set_playing(False)
                        self.seek_slider.setValue(0)
                        self.time_label.setText("00:00")
                        QTimer.singleShot(100, self.player.stop)
            else:
                # Not playing or paused - stop audio monitoring
                self.audio_analyzer.set_playing(False)
        except Exception as e:
            print(f"UI loop fault: {e}")

    def on_slider_pressed(self): self.is_user_sliding = True
    def on_slider_released(self):
        self.is_user_sliding = False
        if self.player.get_state() not in [vlc.State.NothingSpecial, vlc.State.Stopped]:
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
            self.fullscreen_btn.setMinimumWidth(115)
            
            self.fullscreen_btn.setText("⬜ Exit Full")
            self.fullscreen_btn.setToolTip("Exit fullscreen (or press Esc)")
            self.controls_visible = False
            
            # Trigger auto-hide hover countdowns
            self.show_fullscreen_controls()
            if self.fullscreen_timer is None:
                self.fullscreen_timer = QTimer()
                self.fullscreen_timer.setSingleShot(True)
                self.fullscreen_timer.timeout.connect(self.hide_fullscreen_controls)
            self.fullscreen_timer.start(3000)
            
            self.setMouseTracking(True)
            if hasattr(self, 'fullscreen_mouse_timer') and self.fullscreen_mouse_timer is not None:
                self.fullscreen_mouse_timer.start()
                
        else:
            # --- TEARDOWN FULLSCREEN STATE ---
            if hasattr(self, 'fullscreen_mouse_timer') and self.fullscreen_mouse_timer is not None:
                self.fullscreen_mouse_timer.stop()
            if self.fullscreen_timer:
                self.fullscreen_timer.stop()
            
            # Restore exact previous window state cleanly
            if getattr(self, '_was_maximized_before_fullscreen', True):
                self.showMaximized()
            else:
                self.showNormal()
                
            self.is_video_fullscreen = False
            
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
            
            if self.fullscreen_timer:
                self.fullscreen_timer.stop()
                self.fullscreen_timer.start(3000)

    def eventFilter(self, watched, event):
        """Monitors global application events to catch hover tracking values on top of native video engines."""
        if self.is_video_fullscreen:
            # Catch mouse movements anywhere over the video frame or the controller window bar itself
            if event.type() in [QEvent.MouseMove, QEvent.HoverMove]:
                # If mouse is in the bottom 15% region of the viewport screen, surface the controls panel layout
                screen_geo = QApplication.primaryScreen().geometry()
                cursor_pos = QCursor.pos()
                trigger_zone_y = screen_geo.height() - 140
                
                if cursor_pos.y() >= trigger_zone_y or self.playback_widget.underMouse():
                    self.show_fullscreen_controls()
                else:
                    # If moving away from the control layer, reset/tick down the timer aggressively
                    if not self.hide_controls_timer.isActive() and not self.playback_widget.underMouse():
                        self.hide_controls_timer.start()
                        
            # If mouse exits the full app window layout context frame entirely
            elif event.type() == QEvent.Leave and watched == self.playback_widget:
                self.hide_controls_timer.start()
                
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
        # Stop audio analyzer thread
        try:
            if hasattr(self, 'audio_analyzer'):
                self.audio_analyzer.stop()
        except Exception: pass
        
        # Stop auto-reduce timer
        try:
            if hasattr(self, 'auto_reduce_timer'):
                self.auto_reduce_timer.stop()
        except Exception: pass
        
        # Stop periodic UI updates first
        try:
            self.timer.stop()
        except Exception: pass
        
        try:
            if self.fullscreen_timer: self.fullscreen_timer.stop()
            if self.fullscreen_mouse_timer: self.fullscreen_mouse_timer.stop()
        except Exception: pass

        # Clean up floating overlay references to prevent dangling handles
        try:
            if self.playback_widget:
                self.playback_widget.setParent(None)
                self.playback_widget.close()
        except Exception: pass
        
        self.stop_all_tasks()

        try: self.player.stop()
        except Exception: pass
        try: self.player.release()
        except Exception: pass
        try: self.instance.release()
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