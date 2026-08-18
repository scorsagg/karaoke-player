import time
import sys
import os
import subprocess
import time
import json
import logging
import traceback
import shutil
import importlib.util
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
from source_code.workers.audio_separator_thread import AudioSeparatorThread
from source_code.workers.process_thread import ProcessThread
from source_code.dialogs.settings_dialog import SettingsDialog
from source_code.services.player_service import PlayerService
from source_code.services.download_service import DownloadService
from source_code.services.audio_service import AudioService
from source_code.services.file_loading_service import FileLoadingService
from source_code.services.realtime_pitch_service import RealtimePitchService
from source_code.ui.main_layout import create_main_layout
from source_code.models.app_state import AppState
from source_code.controllers.playback_controller import PlaybackController
from source_code.controllers.media_controller import MediaController
from source_code.controllers.processing_controller import ProcessingController
from source_code.controllers.navigation_controller import NavigationController
from source_code.utils import range_rows
from source_code.utils.ffprobe_utils import (
    probe_audio_sample_rate,
    probe_duration_seconds,
    probe_stream_codec_types,
    probe_video_resolution,
)
from source_code.utils.media_paths import build_output_path, source_base_name, to_ffmpeg_path
from source_code.utils.splash_utils import close_splash, show_download_splash, show_task_splash

# Main stack page indices
PAGE_MEDIA_LOADER = 0
PAGE_PLAYBACK = 1
PAGE_AUDIO_STUDIO = 2
PAGE_VIDEO_STUDIO = 3
PAGE_CONVERT_EXPORT = 4

class KaraokeApp(QWidget):
    _state_field_names = set(AppState.__dataclass_fields__.keys())
    _page_constant_names = {
        "PAGE_MEDIA_LOADER",
        "PAGE_PLAYBACK",
        "PAGE_AUDIO_STUDIO",
        "PAGE_VIDEO_STUDIO",
        "PAGE_CONVERT_EXPORT",
    }

    def __getattr__(self, name):
        if hasattr(self, "state") and name in self._state_field_names:
            return getattr(self.state, name)
        if name in self._page_constant_names:
            return globals().get(name)
        raise AttributeError(name)

    def __setattr__(self, name, value):
        if name == "state":
            super().__setattr__(name, value)
            return
        if hasattr(self, "state") and name in self._state_field_names:
            setattr(self.state, name, value)
            return
        super().__setattr__(name, value)

    def __init__(self):
        super().__init__()
        self.state = AppState()

        self.init_settings_manager()

        self.setWindowTitle("Karaoke Studio Pro v3.0")
        self.resize(1150, 850)
        self.setStyleSheet("background-color: #1e1e1e; color: #ffffff; font-family: 'Segoe UI';")

        self.player = PlayerService(parent=self)

        self.playback_controller = PlaybackController()
        self.media_controller = MediaController()
        self.processing_controller = ProcessingController()
        self.navigation_controller = NavigationController()

        self.setup_ui()
        self.nav_list.setCurrentRow(0)
        self.handle_navigation_change(PAGE_MEDIA_LOADER)  # explicitly init video frame + stack for Media Loader

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
        self.audio_analyzer.pitch_updated.connect(self.on_pitch_detected)
        self.audio_analyzer.start()

        # Initialize audio service for managing audio analyzer and meter
        self.audio_service = AudioService(
            self.audio_analyzer,
            self.audio_level_meter,
            level_update_handler=self.on_audio_level_updated,
            analyzer_replaced_handler=self.on_audio_analyzer_replaced,
        )

        # Initialize file loading service for thread-safe file operations
        self.file_loading_service = FileLoadingService(self.audio_service, self.player)

        # Real-time pitch-shift service (ffmpeg decode -> SoundTouch -> sounddevice playback).
        self.realtime_pitch = RealtimePitchService(ffmpeg_path=self.settings.get("ffmpeg_path", "ffmpeg"))

        # Initialize download service
        self.download_service = DownloadService(self.settings, ProcessThread)
        self.download_service.download_progress.connect(self._on_download_progress)
        self.download_service.download_finished.connect(self._on_download_finished)
        self.download_service.download_error.connect(self._on_download_error)

        # Auto-reduce tracking
        self.state.auto_reduce_active = False
        self.state._player_was_active = False
        self.state._pending_seek_ratio = None

    def init_settings_manager(self):
        app_dir = Path(sys._MEIPASS) if hasattr(sys, '_MEIPASS') else Path(__file__).parent.parent
        config_dir = app_dir / "config"
        config_dir.mkdir(exist_ok=True)
        self.settings_file = config_dir / "settings.json"
        self.debug_log_file = config_dir / "app_debug.log"
        self._setup_debug_logger()

        bundled_ffmpeg = get_resource_path("ffmpeg.exe")
        bundled_ffprobe = get_resource_path("ffprobe.exe")
        bundled_ytdlp = get_resource_path("yt-dlp.exe")

        self.settings = {
            "base_directory": str(app_dir),
            "download_directory": str(app_dir),
            "ffmpeg_path": bundled_ffmpeg if os.path.exists(bundled_ffmpeg) else "ffmpeg",
            "ffprobe_path": bundled_ffprobe if os.path.exists(bundled_ffprobe) else "ffprobe",
            "ytdlp_path": bundled_ytdlp if os.path.exists(bundled_ytdlp) else "yt-dlp",
            "measurement_mode": "dB Output (dBFS)",
            "auto_reduce_threshold": 90
        }
        if self.settings_file.exists():
            try:
                with open(self.settings_file, 'r') as f: self.settings.update(json.load(f))
            except: pass

        # Migrate legacy command-only paths to bundled tools when available.
        try:
            ffmpeg_path = str(self.settings.get("ffmpeg_path", "")).strip().lower()
            if ffmpeg_path in {"ffmpeg", "ffmpeg.exe"} and os.path.exists(bundled_ffmpeg):
                self.settings["ffmpeg_path"] = bundled_ffmpeg

            ffprobe_path = str(self.settings.get("ffprobe_path", "")).strip().lower()
            if ffprobe_path in {"ffprobe", "ffprobe.exe"} and os.path.exists(bundled_ffprobe):
                self.settings["ffprobe_path"] = bundled_ffprobe

            ytdlp_path = str(self.settings.get("ytdlp_path", "")).strip().lower()
            if ytdlp_path in {"yt-dlp", "yt-dlp.exe"} and os.path.exists(bundled_ytdlp):
                self.settings["ytdlp_path"] = bundled_ytdlp

            self.save_settings()
        except Exception:
            pass

    def save_settings(self):
        try:
            with open(self.settings_file, 'w') as f: json.dump(self.settings, f, indent=2)
        except: pass

    def _setup_debug_logger(self):
        """Initialize persistent debug logging to config/app_debug.log."""
        self.debug_logger = logging.getLogger("karaoke_app")
        self.debug_logger.setLevel(logging.INFO)
        self.debug_logger.propagate = False

        if not self.debug_logger.handlers:
            file_handler = logging.FileHandler(self.debug_log_file, encoding="utf-8")
            formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
            file_handler.setFormatter(formatter)
            self.debug_logger.addHandler(file_handler)

        self.log_debug("[app] debug logger initialized")

    def log_debug(self, message):
        """Log to both console and persistent file for post-crash diagnostics."""
        try:
            print(message)
        except Exception:
            pass

        try:
            if hasattr(self, "debug_logger") and self.debug_logger:
                self.debug_logger.info(message)
        except Exception:
            pass

    def log_exception(self, context, exc):
        """Log exception details with traceback."""
        tb_text = traceback.format_exc()
        self.log_debug(f"[{context}] ERROR: {exc}")
        self.log_debug(tb_text)

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
        self.video_tools_btn = sidebar_components["video_tools_btn"]
        self.audio_tools_btn = sidebar_components["audio_tools_btn"]
        self.convert_export_btn = sidebar_components["convert_export_btn"]
        self.history_toggle_btn = sidebar_components["history_toggle_btn"]
        self.history_container = sidebar_components["history_container"]
        self.clear_hist_btn = sidebar_components["clear_hist_btn"]
        self.history_list = sidebar_components["history_list"]
        self.settings_btn = sidebar_components["settings_btn"]
        self.status_label = sidebar_components["status_label"]
        
        # Extract video frame and labels
        self.video_frame = components["video_frame"]
        self.filename_label = components["filename_label"]
        
        # Create audio visualization overlay for Audio Tools (will be parented to video_frame after)
        
        # Extract playback bar components
        playback_components = components["playback_components"]
        self.playback_widget = playback_components["playback_widget"]
        self.time_label = playback_components["time_label"]
        self.seek_slider = playback_components["seek_slider"]
        self.duration_label = playback_components["duration_label"]
        self.back_btn = playback_components["back_btn"]
        self.play_btn = playback_components["play_btn"]
        self.pause_btn = playback_components["pause_btn"]
        self.stop_btn = playback_components["stop_btn"]
        self.fwd_btn = playback_components["fwd_btn"]
        self.mute_btn = playback_components["mute_btn"]
        self.vol_slider = playback_components["vol_slider"]
        self.vol_label = playback_components["vol_label"]
        self.audio_level_meter = playback_components["audio_level_meter"]
        self.audio_level_label = playback_components["audio_level_label"]
        self.fullscreen_btn = playback_components["fullscreen_btn"]
        if self.audio_level_meter is not None:
            self.audio_level_meter.set_auto_reduce_threshold(self.settings.get("auto_reduce_threshold", 90))
        
        # Extract page components
        media_loader_page_components = components.get("media_loader_page_components", components["download_page_components"])
        self.load_btn = media_loader_page_components["load_btn"]
        self.url_input = media_loader_page_components["url_input"]
        self.media_loader_download_btn = media_loader_page_components["dl_btn"]
        
        pitch_page_components = components["pitch_page_components"]
        self.pitch_minus = pitch_page_components["pitch_minus"]
        self.pitch_input = pitch_page_components["pitch_input"]
        self.pitch_plus = pitch_page_components["pitch_plus"]
        self.pitch_reset = pitch_page_components["pitch_reset"]
        self.pitch_note_label = pitch_page_components["pitch_note_label"]
        self.pitch_frequency_label = pitch_page_components["pitch_frequency_label"]
        self.pitch_lock_label = pitch_page_components["pitch_lock_label"]
        self.pitch_source_label = pitch_page_components["pitch_source_label"]
        self.sa_label = pitch_page_components["sa_label"]
        self.pa_label = pitch_page_components["pa_label"]
        self.hsa_label = pitch_page_components["hsa_label"]
        self.key_status_label = pitch_page_components["key_status_label"]
        self.speed_minus = pitch_page_components["speed_minus"]
        self.speed_input = pitch_page_components["speed_input"]
        self.speed_plus = pitch_page_components["speed_plus"]
        self.speed_reset = pitch_page_components["speed_reset"]
        self.realtime_pitch_toggle = pitch_page_components.get("realtime_pitch_toggle")
        self.realtime_pitch_status = pitch_page_components.get("realtime_pitch_status")
        self.export_btn = pitch_page_components["export_btn"]
        
        extra_page_components = components["extra_page_components"]
        self.audio_tools_tabs = extra_page_components.get("tabs")
        # Audio Tools File Loader controls
        audio_file_btn = extra_page_components["audio_file_btn"]
        self.audio_file_status = extra_page_components["audio_file_status"]
        audio_url_input = extra_page_components["audio_url_input"]
        self.audio_dl_btn = extra_page_components["audio_dl_btn"]
        # Audio Trimming controls (row-based ranges)
        self.audio_trim_ranges_container = extra_page_components["trim_ranges_container"]
        self.audio_trim_add_range_btn = extra_page_components["trim_add_range_btn"]
        self.audio_trim_add_range = extra_page_components.get("trim_add_range")
        self.trim_format_combo = extra_page_components["trim_format_combo"]
        audio_trim_btn = extra_page_components["trim_btn"]
        self.audio_trim_clear_btn = extra_page_components["trim_clear_btn"]
        self.audio_trim_status_label = extra_page_components["trim_status_label"]
        self.audio_amp_gain_slider = extra_page_components.get("amp_gain_slider")
        self.audio_amp_step_buttons = extra_page_components.get("amp_step_buttons", [])
        self.audio_amp_reset_btn = extra_page_components.get("amp_reset_btn")
        self.audio_amp_status_label = extra_page_components.get("amp_status_label")
        # Convert & Export controls
        convert_export_components = components["convert_export_page_components"]
        self.convert_export_tabs = convert_export_components.get("tabs")
        self.convert_source_combo = convert_export_components["convert_source_combo"]
        self.convert_target_combo = convert_export_components["convert_target_combo"]
        self.convert_quality_combo = convert_export_components["convert_quality_combo"]
        self.conversion_status_label = convert_export_components["conversion_status_label"]
        convert_btn = convert_export_components["convert_btn"]
        self.normalize_cb = convert_export_components["normalize_cb"]
        self.normalize_lufs_combo = convert_export_components["normalize_lufs_combo"]
        normalize_btn = convert_export_components["normalize_btn"]
        self.vocal_model_combo = convert_export_components["vocal_model_combo"]
        self.vocal_target_combo = convert_export_components["vocal_target_combo"]
        self.vocal_output_format_combo = convert_export_components["vocal_output_format_combo"]
        self.vocal_fast_cb = convert_export_components["vocal_fast_cb"]
        self.vocal_recovery_combo = convert_export_components["vocal_recovery_combo"]
        self.vocal_recovery_mode_combo = convert_export_components["vocal_recovery_mode_combo"]
        self.vocal_offline_warning_label = convert_export_components["vocal_offline_warning_label"]
        self.vocal_offline_warning_label.setVisible(self._should_enforce_vocal_offline_preflight())
        self.vocal_sep_btn = convert_export_components["vocal_sep_btn"]
        self.vocal_status_label = convert_export_components["vocal_status_label"]
        self.merge_input_a_btn = convert_export_components["merge_input_a_btn"]
        self.merge_input_a_label = convert_export_components["merge_input_a_label"]
        self.merge_input_b_btn = convert_export_components["merge_input_b_btn"]
        self.merge_input_b_label = convert_export_components["merge_input_b_label"]
        self.merge_output_format_combo = convert_export_components["merge_output_format_combo"]
        self.merge_mode_combo = convert_export_components["merge_mode_combo"]
        self.merge_audio_offset_spin = convert_export_components["merge_audio_offset_spin"]
        self.merge_execute_btn = convert_export_components["merge_execute_btn"]
        self.merge_status_label = convert_export_components["merge_status_label"]
        self.amp_factor_spin = convert_export_components["amp_factor_spin"]
        self.amp_mode_group = convert_export_components.get("amp_mode_group")
        self.amp_plus_btn = convert_export_components.get("amp_plus_btn")
        self.amp_minus_btn = convert_export_components.get("amp_minus_btn")
        self.amp_preview_label = convert_export_components.get("amp_preview_label")
        self.amp_live_btn = convert_export_components.get("amp_live_btn")
        self.amp_live_stop_btn = convert_export_components.get("amp_live_stop_btn")
        self.amp_btn = convert_export_components["amp_btn"]
        self.amp_source_label = convert_export_components["amp_source_label"]
        self.amp_status_label = convert_export_components["amp_status_label"]
        
        # Extract video tools page components
        video_tools_page_components = components["video_tools_page_components"]
        self.video_tools_page_components = video_tools_page_components
        self.video_tools_scroll = components.get("video_tools_scroll")
        self.video_tools_tabs = video_tools_page_components["tabs"]
        self.video_current_file_label = video_tools_page_components["video_current_file_label"]
        self.widen_current_file_label = video_tools_page_components["widen_current_file_label"]
        self.widen_crop_y_spin = video_tools_page_components["widen_crop_y_spin"]
        self.widen_exec_btn = video_tools_page_components["widen_exec_btn"]
        self.video_trim_ranges_container = video_tools_page_components["trim_ranges_container"]
        self.video_trim_add_range_btn = video_tools_page_components["trim_add_range_btn"]
        self.video_trim_add_range = video_tools_page_components.get("trim_add_range")
        self.video_trim_format_combo = video_tools_page_components["trim_format_combo"]
        self.video_trim_clear_btn = video_tools_page_components["trim_clear_btn"]
        video_trim_btn = video_tools_page_components["trim_btn"]
        self.video_trim_status_label = video_tools_page_components["trim_status_label"]
        self.video_extract_status_label = video_tools_page_components["extract_status_label"]
        self.extract_format_combo = video_tools_page_components["extract_format_combo"]
        self.extract_btn = video_tools_page_components["extract_btn"]
        # Playback Window controls (Video Studio)
        self.video_pw_ranges_container = video_tools_page_components["pw_ranges_container"]
        self.video_pw_add_range_btn = video_tools_page_components["pw_add_range_btn"]
        self.video_pw_add_range = video_tools_page_components.get("pw_add_range")
        self.video_pw_apply_btn = video_tools_page_components["pw_apply_btn"]
        self.video_pw_clear_btn = video_tools_page_components["pw_clear_btn"]
        self.video_pw_status_label = video_tools_page_components["pw_status_label"]
        self.video_amp_gain_slider = video_tools_page_components.get("amp_gain_slider")
        self.video_amp_step_buttons = video_tools_page_components.get("amp_step_buttons", [])
        self.video_amp_reset_btn = video_tools_page_components.get("amp_reset_btn")
        self.video_amp_status_label = video_tools_page_components.get("amp_status_label")

        # Playback Window controls (Audio Studio)
        self.audio_pw_ranges_container = extra_page_components.get("pw_ranges_container")
        self.audio_pw_add_range_btn = extra_page_components.get("pw_add_range_btn")
        self.audio_pw_add_range = extra_page_components.get("pw_add_range")
        self.audio_pw_apply_btn = extra_page_components.get("pw_apply_btn")
        self.audio_pw_clear_btn = extra_page_components.get("pw_clear_btn")
        self.audio_pw_status_label = extra_page_components.get("pw_status_label")
        # Provide video length getter to UI so it can default new rows when last row removed
        try:
            import source_code.ui.video_tools_page as vtp
            vtp.video_length_getter = lambda: max(0, int(self.player.get_length() // 1000))
        except Exception:
            pass
        try:
            import source_code.ui.audio_studio_page as asp
            asp.audio_length_getter = lambda: max(0, int(self.player.get_length() // 1000))
        except Exception:
            pass
        self.stack = components["stack"]
        # Active playback-window control set (switches by page)
        self._set_active_playback_window_controls(self.stack.currentIndex())
        
        # Create audio visualization overlay for Audio Tools (parented to video_frame)
        self.audio_overlay = self.create_audio_overlay()
        self.audio_overlay.setParent(self.video_frame)
        
        # Reposition overlay automatically whenever the video frame resizes
        self.video_frame.set_resize_callback(self._reposition_audio_overlay)
        
        # Connect signals for button events
        self.nav_list.itemClicked.connect(lambda item: self.navigation_controller.handle_navigation_change(self, self.nav_list.row(item)))
        self.audio_tools_btn.clicked.connect(lambda: self.navigation_controller.handle_navigation_change(self, PAGE_AUDIO_STUDIO))
        self.video_tools_btn.clicked.connect(lambda: self.navigation_controller.handle_navigation_change(self, PAGE_VIDEO_STUDIO))
        self.convert_export_btn.clicked.connect(lambda: self.navigation_controller.handle_navigation_change(self, PAGE_CONVERT_EXPORT))
        self.video_tools_tabs.currentChanged.connect(lambda tab_idx: self.navigation_controller._on_video_tools_tab_changed(self, tab_idx))
        if self.convert_export_tabs is not None:
            self.convert_export_tabs.currentChanged.connect(lambda tab_idx: self.navigation_controller._on_convert_export_tab_changed(self, tab_idx))
        self.extra_tools_toggle_btn.clicked.connect(lambda: self.media_controller.toggle_extra_tools(self))
        self.history_toggle_btn.clicked.connect(lambda: self.media_controller.toggle_history(self))
        self.clear_hist_btn.clicked.connect(lambda: self.media_controller.clear_history(self))
        self.settings_btn.clicked.connect(self.open_settings)
        self.load_btn.clicked.connect(lambda: self.media_controller.load_video(self))
        self.media_loader_download_btn.clicked.connect(lambda: self.download_video())
        self.fullscreen_btn.clicked.connect(self.toggle_video_fullscreen)
        self.play_btn.clicked.connect(lambda: self.playback_controller.handle_play(self))
        self.pause_btn.clicked.connect(lambda: self.playback_controller.handle_pause(self))
        self.stop_btn.clicked.connect(lambda: self.playback_controller.handle_stop(self))
        self.back_btn.clicked.connect(lambda: self.playback_controller.jump_time(self, -10000))
        self.fwd_btn.clicked.connect(lambda: self.playback_controller.jump_time(self, 10000))
        self.mute_btn.clicked.connect(self.toggle_mute)
        self.vol_slider.valueChanged.connect(self.set_volume)
        self.seek_slider.sliderPressed.connect(self.on_slider_pressed)
        self.seek_slider.sliderReleased.connect(self.on_slider_released)
        self.speed_input.valueChanged.connect(self.set_playback_speed)
        self.pitch_input.valueChanged.connect(self.set_pitch)
        if self.realtime_pitch_toggle is not None:
            self.realtime_pitch_toggle.toggled.connect(self.on_realtime_pitch_toggled)
        self.export_btn.clicked.connect(self.export_video)
        self.widen_exec_btn.clicked.connect(self.widen_active_video_canvas)
        audio_file_btn.clicked.connect(self.load_audio_tools_file)
        self.audio_dl_btn.clicked.connect(lambda: self.download_audio(audio_url_input))
        self.extract_btn.clicked.connect(self.extract_audio_from_video)
        if self.audio_amp_gain_slider is not None:
            self.audio_amp_gain_slider.valueChanged.connect(lambda _v: self.apply_live_amplification("audio"))
        if self.audio_amp_reset_btn is not None:
            self.audio_amp_reset_btn.clicked.connect(self.reset_live_amplification)
        for btn in (self.audio_amp_step_buttons or []):
            step = int(btn.property("amp_step"))
            btn.clicked.connect(lambda _checked=False, s=step: self.set_live_amplification_step(s))
        if self.video_amp_gain_slider is not None:
            self.video_amp_gain_slider.valueChanged.connect(lambda _v: self.apply_live_amplification("video"))
        if self.video_amp_reset_btn is not None:
            self.video_amp_reset_btn.clicked.connect(self.reset_live_amplification)
        for btn in (self.video_amp_step_buttons or []):
            step = int(btn.property("amp_step"))
            btn.clicked.connect(lambda _checked=False, s=step: self.set_live_amplification_step(s))
        audio_trim_btn.clicked.connect(self.trim_audio)
        self.audio_trim_clear_btn.clicked.connect(self.clear_audio_trim_ranges)
        try:
            self.audio_trim_add_range_btn.clicked.connect(self._on_audio_trim_add_range)
        except Exception:
            pass
        convert_btn.clicked.connect(self.convert_audio_format)
        normalize_btn.clicked.connect(self.normalize_audio)
        self.vocal_sep_btn.clicked.connect(self.start_audio_separator)
        self.vocal_model_combo.currentTextChanged.connect(lambda _v: self._update_vocal_separator_mode_notice())
        self.merge_input_a_btn.clicked.connect(self.select_merge_input_a)
        self.merge_input_b_btn.clicked.connect(self.select_merge_input_b)
        self.merge_execute_btn.clicked.connect(self.execute_join_merge)
        self.merge_mode_combo.currentTextChanged.connect(lambda _v: self._update_merge_status_hint())
        self.merge_audio_offset_spin.valueChanged.connect(lambda _v: self._update_merge_status_hint())
        self.amp_btn.clicked.connect(self.amplify_export_media)
        if self.amp_live_btn is not None:
            self.amp_live_btn.clicked.connect(self.start_live_amplify_preview)
        if self.amp_live_stop_btn is not None:
            self.amp_live_stop_btn.clicked.connect(self.stop_live_amplify_preview)
        self.convert_source_combo.currentTextChanged.connect(lambda _v: self.refresh_conversion_targets())

        self.merge_input_a_path = ""
        self.merge_input_b_path = ""
        self._last_merge_cmd_text = ""
        self._update_vocal_separator_mode_notice()
        # Video Tools: Video Trimming (uses video loaded from Media Loader page)
        video_trim_btn.clicked.connect(self.trim_video)
        self.video_trim_clear_btn.clicked.connect(self.clear_video_trim_ranges)
        try:
            self.video_trim_add_range_btn.clicked.connect(self._on_video_trim_add_range)
        except Exception:
            pass
        self.video_pw_apply_btn.clicked.connect(lambda: self.playback_controller.handle_play(self))
        self.video_pw_clear_btn.clicked.connect(lambda: self.playback_controller.clear_playback_window(self))
        if self.audio_pw_apply_btn is not None:
            self.audio_pw_apply_btn.clicked.connect(lambda: self.playback_controller.handle_play(self))
        if self.audio_pw_clear_btn is not None:
            self.audio_pw_clear_btn.clicked.connect(lambda: self.playback_controller.clear_playback_window(self))
        # Connect Add Range button to a handler that computes sensible defaults
        try:
            self.video_pw_add_range_btn.clicked.connect(lambda: self.playback_controller._on_pw_add_range(self))
            if self.audio_pw_add_range_btn is not None:
                self.audio_pw_add_range_btn.clicked.connect(lambda: self.playback_controller._on_pw_add_range(self))
        except Exception:
            pass
        self.history_list.itemDoubleClicked.connect(lambda item: self.media_controller.load_history_item(self, item.toolTip()))

        # Live amplification state (1.0 = no boost)
        self.state._live_amplify_factor = 1.0
        self.state._pre_amplify_base_volume = None
        self.state._live_amplify_step = 0
        self.state._live_amp_preview_active = False
        self.state._last_non_amplify_convert_export_tab_index = 0
        self._update_amplify_reset_buttons(0)
        self._update_amplify_step_button_styles(0)

        self.state._current_export_media_kind = "unknown"
        self.state._smoothed_pitch_hz = None
        self.state._last_pitch_confidence = 0.0
        self.state._realtime_pitch_apply_timer = None
        self._refresh_realtime_pitch_status()
        # Tonic detection accumulator
        self.state._tonic_note_counts = {}   # note_class (0-11) -> count
        self.state._tonic_frames_collected = 0
        self.state._tonic_locked = False
        self.state._tonic_note_class = None  # 0-11 once locked
        
        # Initialize state flags
        self.state.extra_tools_is_expanded = False
        self.state.history_is_expanded = False
        
        # Load history from disk
        self.load_history_from_disk()

    def handle_navigation_change(self, idx, is_audio_only=None):
        return self.navigation_controller.handle_navigation_change(self, idx, is_audio_only=is_audio_only)

    def _on_video_tools_tab_changed(self, tab_idx):
        return self.navigation_controller._on_video_tools_tab_changed(self, tab_idx)

    def _on_convert_export_tab_changed(self, tab_idx):
        return self.navigation_controller._on_convert_export_tab_changed(self, tab_idx)

    def open_settings(self):
        # Pause audio analyzer while settings dialog is open to prevent conflicts
        was_playing = self.audio_service.pause_analyzer()
        
        try:
            dialog = SettingsDialog(self, self)
            dialog.exec()
            # Update audio meter display mode if settings were changed
            self.audio_service.set_display_mode(self.settings.get("measurement_mode", "dB Output (dBFS)"))
            if hasattr(self, 'audio_level_meter') and self.audio_level_meter is not None:
                self.audio_level_meter.set_auto_reduce_threshold(self.settings.get("auto_reduce_threshold", 90))
        finally:
            # Resume audio analyzer if it was playing
            if was_playing:
                self.audio_service.resume_analyzer()

    def set_volume(self, value):
        effective = self._effective_output_volume(value)
        self.player.set_volume(effective)
        self.vol_label.setText(f"{value}%")
        self.mute_btn.setText("🔊" if value > 0 else "🔇")

        # Manual volume changes should be honored briefly before auto-reduce can react again.
        if not getattr(self, '_auto_adjusting_volume', False):
            self._manual_volume_override_until = time.time() + 0.75
            self._auto_reduce_cooldown_until = 0.0
            self.high_db_counter = 0

    def _reset_export_amplify_factor(self, loaded_file_label=None):
        """Reset the export amplify UI to neutral so the loaded file is treated as the new baseline."""
        self._clear_live_amplify_preview_state()

        if hasattr(self, 'amp_factor_spin') and self.amp_factor_spin is not None:
            self.amp_factor_spin.blockSignals(True)
            self.amp_factor_spin.setValue(1.0)
            self.amp_factor_spin.blockSignals(False)

        if hasattr(self, 'amp_plus_btn') and self.amp_plus_btn is not None:
            self.amp_plus_btn.blockSignals(True)
            self.amp_plus_btn.setChecked(True)
            self.amp_plus_btn.setStyleSheet("background-color: #0e639c; color: white; font-weight: bold; min-width: 140px;")
            self.amp_plus_btn.blockSignals(False)

        if hasattr(self, 'amp_minus_btn') and self.amp_minus_btn is not None:
            self.amp_minus_btn.blockSignals(True)
            self.amp_minus_btn.setChecked(False)
            self.amp_minus_btn.setStyleSheet("background-color: #2f2f2f; color: #ddd; min-width: 160px;")
            self.amp_minus_btn.blockSignals(False)

        if hasattr(self, 'amp_preview_label') and self.amp_preview_label is not None:
            self.amp_preview_label.setText("Selected export: Amplification + 1.00x")

        if hasattr(self, 'amp_source_label') and self.amp_source_label is not None:
            if loaded_file_label:
                self.amp_source_label.setText(f"Loaded file ready: {loaded_file_label} (Amplification + 1.00x)")
            else:
                self.amp_source_label.setText("Loaded file ready: Amplification + 1.00x")

    def _get_export_amplify_selection(self):
        amount = float(self.amp_factor_spin.value())
        mode_button = self.amp_mode_group.checkedButton() if hasattr(self, 'amp_mode_group') else None
        mode = mode_button.property("amp_mode") if mode_button is not None else "amplify"
        factor = amount if mode == "amplify" else 1.0 / max(amount, 0.01)
        return mode, amount, factor

    def _clear_live_amplify_preview_state(self):
        self._live_amp_preview_active = False
        try:
            self.realtime_pitch.set_gain(1.0)
        except Exception:
            pass
        if hasattr(self, 'amp_live_btn') and self.amp_live_btn is not None:
            self.amp_live_btn.setEnabled(True)
        if hasattr(self, 'amp_live_stop_btn') and self.amp_live_stop_btn is not None:
            self.amp_live_stop_btn.setEnabled(False)

    def _effective_output_volume(self, base_value):
        """Compute effective output volume after live amplification with VLC-safe clamp.

        Apply multiplicative gain so every step change has a consistent audible effect.
        """
        factor = float(getattr(self, '_live_amplify_factor', 1.0) or 1.0)
        return max(0, min(100, int(round(float(base_value) * factor))))

    def _factor_from_gain_percent(self, gain_percent):
        """Convert discrete step to a display factor based on the resulting output volume."""
        try:
            gain = int(round(float(gain_percent)))
        except Exception:
            gain = 0

        gain = max(-10, min(10, gain))
        return max(0.0, 1.0 + (gain * 0.12))

    def _set_amplify_status_text(self, text):
        if hasattr(self, 'audio_amp_status_label') and self.audio_amp_status_label is not None:
            self.audio_amp_status_label.setText(text)
        if hasattr(self, 'video_amp_status_label') and self.video_amp_status_label is not None:
            self.video_amp_status_label.setText(text)

    def _update_amplify_reset_buttons(self, gain_step):
        enabled = int(round(float(gain_step))) != 0
        if hasattr(self, 'audio_amp_reset_btn') and self.audio_amp_reset_btn is not None:
            self.audio_amp_reset_btn.setEnabled(enabled)
            self.audio_amp_reset_btn.setStyleSheet(
                "background-color: #2ecc71; color: black; font-weight: bold; height: 32px; min-width: 80px;"
                if enabled else
                "background-color: #555; color: #bbb; height: 32px; min-width: 80px;"
            )
        if hasattr(self, 'video_amp_reset_btn') and self.video_amp_reset_btn is not None:
            self.video_amp_reset_btn.setEnabled(enabled)
            self.video_amp_reset_btn.setStyleSheet(
                "background-color: #2ecc71; color: black; font-weight: bold; height: 32px; min-width: 80px;"
                if enabled else
                "background-color: #555; color: #bbb; height: 32px; min-width: 80px;"
            )

    def _update_amplify_step_button_styles(self, gain_step):
        active_step = int(round(float(gain_step)))
        for btn in (getattr(self, 'audio_amp_step_buttons', []) or []):
            step = int(btn.property("amp_step"))
            if step == active_step:
                btn.setStyleSheet("background-color: #0e639c; color: white; border: 1px solid #2ecc71; font-weight: bold; padding: 0 4px;")
            else:
                btn.setStyleSheet("background-color: #2f2f2f; color: #ddd; border: 1px solid #555; padding: 0 4px;")
        for btn in (getattr(self, 'video_amp_step_buttons', []) or []):
            step = int(btn.property("amp_step"))
            if step == active_step:
                btn.setStyleSheet("background-color: #0e639c; color: white; border: 1px solid #2ecc71; font-weight: bold; padding: 0 4px;")
            else:
                btn.setStyleSheet("background-color: #2f2f2f; color: #ddd; border: 1px solid #555; padding: 0 4px;")

    def _sync_amplify_gain_controls(self, gain_percent):
        for slider_name in ('audio_amp_gain_slider', 'video_amp_gain_slider'):
            slider = getattr(self, slider_name, None)
            if slider is None:
                continue
            slider.blockSignals(True)
            slider.setValue(int(round(float(gain_percent))))
            slider.blockSignals(False)

    def set_live_amplification_step(self, step):
        """Set amplification step from numbered markers and apply immediately."""
        self._sync_amplify_gain_controls(int(step))
        self.apply_live_amplification("audio")

    def apply_live_amplification(self, source="audio"):
        """Apply live playback amplification in real-time (no export)."""
        slider = self.audio_amp_gain_slider if source == "audio" else self.video_amp_gain_slider
        if slider is None:
            return

        old_factor = float(getattr(self, '_live_amplify_factor', 1.0) or 1.0)
        base_before = float(self.vol_slider.value())

        gain_percent = int(slider.value())
        self._live_amplify_step = gain_percent
        new_factor = self._factor_from_gain_percent(gain_percent)
        self._live_amplify_factor = new_factor

        # Remember pre-amplify base volume when entering amplified mode.
        if old_factor == 1.0 and new_factor != 1.0:
            self._pre_amplify_base_volume = int(round(base_before))
        elif new_factor == 1.0:
            self._pre_amplify_base_volume = None

        self._sync_amplify_gain_controls(gain_percent)
        self._update_amplify_reset_buttons(gain_percent)
        self._update_amplify_step_button_styles(gain_percent)
        self.set_volume(self.vol_slider.value())
        mode = "Normal" if gain_percent == 0 else ("Louder" if gain_percent > 0 else "Softer")
        effective_volume = self._effective_output_volume(self.vol_slider.value())
        self._set_amplify_status_text(
            f"Loudness: {mode}, Step: {gain_percent:+d}, Output: {effective_volume}/100"
        )

    def reset_live_amplification(self):
        """Reset live playback amplification to neutral (100%)."""
        self._live_amplify_factor = 1.0
        self._live_amplify_step = 0
        self._sync_amplify_gain_controls(0.0)
        self._update_amplify_reset_buttons(0)
        self._update_amplify_step_button_styles(0)

        # Restore pre-amplify base volume when available.
        if self._pre_amplify_base_volume is not None:
            self._auto_adjusting_volume = True
            try:
                self.vol_slider.setValue(int(max(0, min(100, self._pre_amplify_base_volume))))
            finally:
                self._auto_adjusting_volume = False
        self._pre_amplify_base_volume = None

        self.set_volume(self.vol_slider.value())
        neutral_output = self._effective_output_volume(self.vol_slider.value())
        self._set_amplify_status_text(f"Loudness: Normal, Step: 0, Output: {neutral_output}/100")

    def toggle_mute(self):
        m = not self.player.get_mute(); self.player.set_mute(m)
        self.mute_btn.setText("🔇" if m else "🔊")

    def on_audio_level_updated(self, db_level):
        if not hasattr(self, 'audio_level_meter'): return

        self.audio_level_meter.set_level(db_level)

        # Use the meter's approximate SPL so auto-reduce follows the configured SPL threshold.
        approx_spl = self.audio_level_meter.get_approximate_spl()

        # Default to 90 dB SPL, but keep the threshold user-adjustable.
        threshold = int(self.settings.get("auto_reduce_threshold", 90))
        manual_override_until = getattr(self, '_manual_volume_override_until', 0.0)
        cooldown_until = getattr(self, '_auto_reduce_cooldown_until', 0.0)

        if time.time() < manual_override_until:
            return

        if time.time() < cooldown_until:
            return
        
        # Auto-reduction only when sound goes beyond the configured SPL threshold.
        if approx_spl > threshold:
            if not hasattr(self, 'high_db_counter'): self.high_db_counter = 0
            self.high_db_counter += 1

            # If it stays loud for ~2 seconds (20 cycles at 100ms each), reduce volume once.
            if self.high_db_counter >= 20:
                current_vol = self.vol_slider.value()
                if current_vol > 20:
                    new_volume = max(20, current_vol - 5)
                    self._auto_adjusting_volume = True
                    try:
                        self.vol_slider.setValue(new_volume)
                    finally:
                        self._auto_adjusting_volume = False
                    self.status_label.setText(
                        f"Auto-reduced volume to {new_volume}% (Level: ~{approx_spl:.0f} dB SPL)")
                    self._auto_reduce_cooldown_until = time.time() + 1.0
                self.high_db_counter = 0
        else:
            # Reset counter if volume drops below threshold.
            self.high_db_counter = 0

    def on_audio_analyzer_replaced(self, new_thread):
        """Keep main reference synced when AudioService recreates analyzer thread."""
        self.audio_analyzer = new_thread
        try:
            self.audio_analyzer.level_updated.connect(self.on_audio_level_updated)
        except Exception:
            pass
        try:
            self.audio_analyzer.pitch_updated.connect(self.on_pitch_detected)
        except Exception:
            pass

    # ── NOTE NAMES for tonic derivation ─────────────────────────────────────
    _NOTE_NAMES_SHARP = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
    _MAJOR_PROFILE = (6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88)
    _MINOR_PROFILE = (6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17)

    @staticmethod
    def _note_class_to_name(note_class):
        return KaraokeApp._NOTE_NAMES_SHARP[int(note_class) % 12]

    def _select_tonic_note_class(self, note_counts):
        """Choose tonic by matching against shifted Sa-Pa templates and key profiles."""
        if not note_counts:
            return None

        total = float(sum(note_counts.values()))
        if total <= 0:
            return int(max(note_counts, key=note_counts.get))

        histogram = [float(note_counts.get(i, 0)) / total for i in range(12)]

        def _cosine_similarity(a, b):
            dot = sum(x * y for x, y in zip(a, b))
            na = sum(x * x for x in a) ** 0.5
            nb = sum(x * x for x in b) ** 0.5
            if na <= 1e-12 or nb <= 1e-12:
                return 0.0
            return dot / (na * nb)

        # Relative profile representing Sa-Pa-Sa support plus nearby svara presence.
        # 0:Sa, 7:Pa, 5:Ma, 2:Ri, 9:Dha, 4:Ga, 11:Ni
        sa_pa_template_rel = {
            0: 1.00,
            7: 0.88,
            5: 0.32,
            2: 0.24,
            9: 0.22,
            4: 0.16,
            11: 0.14,
        }

        def _build_template(tonic):
            template = [0.0] * 12
            for rel, w in sa_pa_template_rel.items():
                template[(tonic + rel) % 12] = float(w)
            return template

        def _score_tonic(tonic):
            template_score = _cosine_similarity(histogram, _build_template(tonic))

            major_score = 0.0
            minor_score = 0.0
            for pitch_class in range(12):
                rel = (pitch_class - tonic) % 12
                weight = histogram[pitch_class]
                major_score += weight * self._MAJOR_PROFILE[rel]
                minor_score += weight * self._MINOR_PROFILE[rel]

            profile_score = max(major_score, minor_score)

            sa_weight = histogram[tonic]
            pa_weight = histogram[(tonic + 7) % 12]
            # Favor candidates where tonic itself is present, and penalize cases
            # where the fifth overwhelms the tonic (common false-C outcome).
            pa_excess = max(0.0, pa_weight - sa_weight)
            tonic_prominence = sa_weight - (0.80 * pa_excess)

            # Blend template similarity with profile score.
            return (2.20 * template_score) + profile_score + (2.40 * tonic_prominence)

        candidate_scores = [(tonic, _score_tonic(tonic)) for tonic in range(12)]
        candidate_scores.sort(key=lambda item: item[1], reverse=True)
        best_tonic, best_score = candidate_scores[0]

        # If ranking is ambiguous, fall back to dominant post-intro note class.
        raw_ranked = sorted(note_counts.items(), key=lambda kv: kv[1], reverse=True)
        raw_top_tonic, raw_top_count = int(raw_ranked[0][0]), int(raw_ranked[0][1])
        raw_second_count = int(raw_ranked[1][1]) if len(raw_ranked) > 1 else 0
        profile_margin = best_score - candidate_scores[1][1] if len(candidate_scores) > 1 else best_score
        raw_margin_ratio = (float(raw_top_count) / max(1.0, float(raw_second_count)))

        if profile_margin <= 0.08 and raw_margin_ratio >= 1.20:
            best_tonic = raw_top_tonic

        return int(best_tonic)

    def _update_key_display(self):
        """Derive Pa and upper Sa from the locked tonic and update the singer's key panel."""
        nc = self._tonic_note_class
        if nc is None:
            for lbl in (self.sa_label, self.pa_label, self.hsa_label):
                lbl.setText("—")
            self.key_status_label.setText("Detecting song key…")
            self.key_status_label.setStyleSheet("color: #e67e22; font-size: 9px; font-style: italic;")
            return
        sa_name  = self._note_class_to_name(nc)
        pa_name  = self._note_class_to_name(nc + 7)
        hsa_name = self._note_class_to_name(nc)       # same name, octave higher
        self.sa_label.setText(sa_name)
        self.pa_label.setText(pa_name)
        self.hsa_label.setText(hsa_name + "'")
        self.key_status_label.setText(f"Key: {sa_name}  (locked after ~40 s main section)")
        self.key_status_label.setStyleSheet("color: #2ecc71; font-size: 9px; font-style: italic;")

    def _reset_pitch_display(self):
        self._smoothed_pitch_hz = None
        self._last_pitch_confidence = 0.0
        self._stable_note_name = ""
        self._candidate_note_name = ""
        self._candidate_note_hits = 0
        self._no_pitch_frames = 0
        # reset tonic accumulator for new song
        self._tonic_note_counts = {}
        self._tonic_frames_collected = 0
        self._tonic_locked = False
        self._tonic_note_class = None
        self._tonic_detection_start_ts = time.time()
        if hasattr(self, 'pitch_note_label') and self.pitch_note_label is not None:
            self.pitch_note_label.setText("—")
        if hasattr(self, 'pitch_frequency_label') and self.pitch_frequency_label is not None:
            self.pitch_frequency_label.setText("Waiting for audio…")
        if hasattr(self, 'pitch_lock_label') and self.pitch_lock_label is not None:
            self.pitch_lock_label.setText("Lock: searching")
            self.pitch_lock_label.setStyleSheet("color: #e67e22; font-size: 9px; font-weight: bold;")
        if hasattr(self, 'pitch_source_label') and self.pitch_source_label is not None:
            self.pitch_source_label.setText("Playback loopback")
        if hasattr(self, 'sa_label'):
            self._update_key_display()

    def on_pitch_detected(self, frequency_hz, note_name, confidence):
        if not hasattr(self, 'pitch_note_label') or self.pitch_note_label is None:
            return

        target_detection_seconds = 40
        intro_skip_seconds = 40
        min_votes_required = 280
        start_ts = getattr(self, '_tonic_detection_start_ts', None)
        if start_ts is None:
            start_ts = time.time()
            self._tonic_detection_start_ts = start_ts

        # Prefer real playback time so detection progress matches seek-bar timing.
        try:
            player_ms = int(self.player.get_time()) if hasattr(self, 'player') and self.player else -1
        except Exception:
            player_ms = -1

        if player_ms is not None and player_ms >= 0:
            elapsed_seconds = int(player_ms // 1000)
        else:
            elapsed_seconds = int(max(0, time.time() - start_ts))

        main_section_seconds = max(0, elapsed_seconds - intro_skip_seconds)

        # Keep status aligned with real elapsed playback time.
        if not self._tonic_locked:
            if elapsed_seconds < intro_skip_seconds:
                self.key_status_label.setText(
                    f"Listening to intro… ({elapsed_seconds} s / {intro_skip_seconds} s)"
                )
            elif main_section_seconds >= target_detection_seconds and self._tonic_note_counts and self._tonic_frames_collected >= min_votes_required:
                best_nc = self._select_tonic_note_class(self._tonic_note_counts)
                self._tonic_note_class = best_nc
                self._tonic_locked = True
                self._update_key_display()
            else:
                shown = min(main_section_seconds, target_detection_seconds)
                self.key_status_label.setText(
                    f"Detecting main section… ({shown} s / {target_detection_seconds} s, votes: {self._tonic_frames_collected})"
                )

        # ── Ignore weak frames ────────────────────────────────────────────────
        if frequency_hz <= 0 or confidence < 0.40:
            self._no_pitch_frames = getattr(self, '_no_pitch_frames', 0) + 1
            if self._no_pitch_frames >= 10:
                if not getattr(self, '_stable_note_name', ''):
                    self.pitch_note_label.setText("—")
                self.pitch_frequency_label.setText("Waiting for a stable pitch…")
                if hasattr(self, 'pitch_lock_label') and self.pitch_lock_label is not None:
                    self.pitch_lock_label.setText("Lock: searching")
                    self.pitch_lock_label.setStyleSheet("color: #e67e22; font-size: 9px; font-weight: bold;")
            return

        self._no_pitch_frames = 0

        # ── Smooth Hz ─────────────────────────────────────────────────────────
        if self._smoothed_pitch_hz is None:
            self._smoothed_pitch_hz = float(frequency_hz)
        else:
            self._smoothed_pitch_hz = 0.12 * float(frequency_hz) + 0.88 * self._smoothed_pitch_hz

        self._last_pitch_confidence = float(confidence)

        # ── Stable live note (hysteresis) ────────────────────────────────────
        stable_note    = getattr(self, '_stable_note_name', '')
        candidate_note = getattr(self, '_candidate_note_name', '')
        candidate_hits = getattr(self, '_candidate_note_hits', 0)

        if not stable_note:
            stable_note = candidate_note = note_name
            candidate_hits = 0
        elif note_name == stable_note:
            candidate_note = note_name
            candidate_hits = 0
        else:
            if note_name == candidate_note:
                candidate_hits += 1
            else:
                candidate_note = note_name
                candidate_hits = 1
            if candidate_hits >= 3:
                stable_note = candidate_note
                candidate_hits = 0

        self._stable_note_name  = stable_note
        self._candidate_note_name = candidate_note
        self._candidate_note_hits = candidate_hits

        # ── Tonic accumulation (votes from confident frames during elapsed window) ─
        if not self._tonic_locked and elapsed_seconds >= intro_skip_seconds and confidence >= 0.50:
            from source_code.workers.audio_analyzer import frequency_to_midi_note
            midi = frequency_to_midi_note(frequency_hz)
            if midi is not None:
                nc = int(midi) % 12
                self._tonic_note_counts[nc] = self._tonic_note_counts.get(nc, 0) + 1
                self._tonic_frames_collected += 1
                if main_section_seconds >= target_detection_seconds and self._tonic_frames_collected >= min_votes_required:
                    best_nc = self._select_tonic_note_class(self._tonic_note_counts)
                    self._tonic_note_class = best_nc
                    self._tonic_locked = True
                    self._update_key_display()

        # ── Update technical side-panel ───────────────────────────────────────
        self.pitch_note_label.setText(stable_note if stable_note else note_name)
        self.pitch_frequency_label.setText(
            f"{self._smoothed_pitch_hz:.1f} Hz  •  live {frequency_hz:.1f} Hz  •  conf {self._last_pitch_confidence:.2f}"
        )
        if hasattr(self, 'pitch_lock_label') and self.pitch_lock_label is not None:
            if self._last_pitch_confidence >= 0.65:
                self.pitch_lock_label.setText("Lock: yes ✓")
                self.pitch_lock_label.setStyleSheet("color: #2ecc71; font-size: 9px; font-weight: bold;")
            else:
                self.pitch_lock_label.setText("Lock: stabilizing…")
                self.pitch_lock_label.setStyleSheet("color: #f1c40f; font-size: 9px; font-weight: bold;")
        self.pitch_source_label.setText("Source: Playback audio analysis (smoothed)")

    def jump_time(self, ms):
        if not self.player.is_active() and not self._ensure_media_loaded_for_playback():
            return
        if self.player.has_media() or self.player.is_active():
            current = self.player.get_time()
            duration = self.player.get_length()
            if duration <= 0: return
            new_time = max(0, min(current + ms, duration - 1))
            self.player.set_position(new_time / duration)
            self._resync_realtime_audio_after_seek()

    def _ensure_media_loaded_for_playback(self):
        """Rebind media when a prior stop/end path has released VLC's active media reference."""
        needs_rebind = False
        try:
            if not self.player.has_media():
                needs_rebind = True
            elif hasattr(self.player, 'is_ended') and self.player.is_ended():
                # Ended state can look loaded but ignore seek/play until media is rebound.
                needs_rebind = True
        except Exception:
            needs_rebind = True

        if not needs_rebind:
            return True

        if not self.video_path or not os.path.exists(self.video_path):
            return False

        try:
            self.player.set_media(self.video_path)
            return True
        except Exception as e:
            self.log_debug(f"[playback_rebind] failed for {self.video_path}: {e}")
            return False

    def _apply_pending_seek_after_play(self, retries=10):
        """Apply a deferred seek target after Play when media timing is available."""
        pending = getattr(self, '_pending_seek_ratio', None)
        if pending is None:
            return

        dur = int(self.player.get_length()) if self.player else -1
        if dur <= 0 and retries > 0:
            QTimer.singleShot(90, lambda: self._apply_pending_seek_after_play(retries - 1))
            return

        target = max(0.0, min(float(pending), 1.0))
        try:
            if dur > 0:
                self.player.set_time(int(target * dur))
            else:
                self.player.set_position(target)
        except Exception:
            pass

        self._pending_seek_ratio = None
        self._resync_realtime_audio_after_seek()

    def _resync_realtime_audio_after_seek(self):
        """After timeline seeks, restart shifted audio from current position when realtime mode is active."""
        if not self._is_realtime_pitch_enabled():
            return
        try:
            if not self.realtime_pitch.is_active():
                return
            if not self.player.is_active():
                return
        except Exception:
            return

        # Give VLC a moment to apply the seek target before restarting shifted stream.
        QTimer.singleShot(120, lambda: self.play_shifted(start_from_current=True))

    def add_to_history(self, file_path):
        return self.media_controller.add_to_history(self, file_path)

    def save_history_to_disk(self):
        return self.media_controller.save_history_to_disk(self)

    def load_history_from_disk(self):
        return self.media_controller.load_history_from_disk(self)

    def clear_history(self):
        return self.media_controller.clear_history(self)

    def toggle_history(self):
        return self.media_controller.toggle_history(self)

    def toggle_extra_tools(self):
        return self.media_controller.toggle_extra_tools(self)

    def load_video(self, file_path=None, splash_screen=None, is_audio_only=None):
        return self.media_controller.load_video(self, file_path=file_path, splash_screen=splash_screen, is_audio_only=is_audio_only)

    def finish_loading(self, loader, is_audio_only=False):
        return self.media_controller.finish_loading(self, loader, is_audio_only=is_audio_only)

    def _reset_rows_to_single_range(self, container, add_row_fn, default_start=0, default_end=0):
        """Reset a range-row container to one row with provided defaults."""
        range_rows.reset_rows_to_single_range(container, add_row_fn, default_start, default_end)

    def _reset_all_page_timers_on_load(self):
        """Reset all timer/range controls across Audio Studio and Video Studio pages."""
        # Reset stateful playback-window runtime guards.
        self._pw_end_ms = None
        self._pw_ranges = []
        self._pw_range_idx = 0

        # Reset all range-based timer UIs to a single default row.
        self._reset_rows_to_single_range(self.video_trim_ranges_container, self.video_trim_add_range, 0, 0)
        self._reset_rows_to_single_range(self.audio_trim_ranges_container, self.audio_trim_add_range, 0, 0)
        self._reset_rows_to_single_range(self.video_pw_ranges_container, self.video_pw_add_range, 0, 0)
        self._reset_rows_to_single_range(self.audio_pw_ranges_container, self.audio_pw_add_range, 0, 0)

        # Keep status labels consistent after reset.
        self.video_trim_status_label.setText("Ready to trim video")
        self.audio_trim_status_label.setText("Ready to trim audio")
        self.video_pw_status_label.setText("No playback window active")
        self.video_pw_status_label.setStyleSheet("color: #888; font-size: 10px;")
        if self.audio_pw_status_label is not None:
            self.audio_pw_status_label.setText("No playback window active")
            self.audio_pw_status_label.setStyleSheet("color: #888; font-size: 10px;")

    def _set_first_row_end_to_duration(self, container, duration_seconds):
        """Set first row to 00:00 -> media duration for range-row containers."""
        range_rows.set_first_row_range(container, duration_seconds)

    def _reset_join_merge_controls(self):
        """Reset Join & Merge tab inputs, labels, and mode/output controls."""
        self.merge_input_a_path = ""
        self.merge_input_b_path = ""
        self._last_merge_cmd_text = ""

        self.merge_input_a_btn.setText("Input A: Click to select")
        self.merge_input_a_btn.setStyleSheet("background-color: #3a3a3a; color: white; height: 36px; font-weight: bold;")
        self.merge_input_a_btn.setToolTip("")
        self.merge_input_a_label.setText("Input A: Not selected")
        self.merge_input_a_label.setStyleSheet("color: #bcbcbc; font-size: 11px; font-weight: bold;")
        self.merge_input_a_label.setToolTip("")

        self.merge_input_b_btn.setText("Input B: Click to select")
        self.merge_input_b_btn.setStyleSheet("background-color: #3a3a3a; color: white; height: 36px; font-weight: bold;")
        self.merge_input_b_btn.setToolTip("")
        self.merge_input_b_label.setText("Input B: Not selected")
        self.merge_input_b_label.setStyleSheet("color: #bcbcbc; font-size: 11px; font-weight: bold;")
        self.merge_input_b_label.setToolTip("")

        self.merge_output_format_combo.setCurrentIndex(0)
        self.merge_mode_combo.setCurrentIndex(0)
        self.merge_audio_offset_spin.setValue(0.0)
        self.merge_status_label.setText("Ready. Select two files to begin.")
        self.merge_status_label.setToolTip("")

    def _reset_all_page_controls_on_load(self, is_audio_only):
        """Reset tab selection and control defaults across all studio pages on new load."""
        if self.audio_tools_tabs is not None:
            self.audio_tools_tabs.setCurrentIndex(0)
        if self.video_tools_tabs is not None:
            self.video_tools_tabs.setCurrentIndex(0)
        if self.convert_export_tabs is not None:
            self.convert_export_tabs.setCurrentIndex(0)

        # Reset trim/export format selectors to defaults.
        self.trim_format_combo.setCurrentIndex(0)
        self.video_trim_format_combo.setCurrentIndex(0)
        self.extract_format_combo.setCurrentIndex(0)
        self.widen_crop_y_spin.setValue(0.10)

        # Reset Convert & Export controls.
        self.convert_source_combo.setCurrentIndex(0)
        self.convert_quality_combo.setCurrentIndex(1)
        self.normalize_cb.setChecked(True)
        self.normalize_lufs_combo.setCurrentIndex(0)

        # Reset Vocal Separator controls/status.
        self.vocal_model_combo.setCurrentIndex(0)
        self.vocal_target_combo.setCurrentIndex(0)
        self.vocal_output_format_combo.setCurrentIndex(0)
        self.vocal_fast_cb.setChecked(False)
        default_recovery_index = self.vocal_recovery_combo.findText("5% (Subtle)")
        self.vocal_recovery_combo.setCurrentIndex(default_recovery_index if default_recovery_index >= 0 else 0)
        self.vocal_recovery_mode_combo.setCurrentIndex(0)
        self.vocal_status_label.setText("Ready. Load a file, then separate with Demucs or the faster UVR path.")
        self._update_vocal_separator_mode_notice()

        # Reset Join & Merge controls (requested behavior).
        self._reset_join_merge_controls()

        # Reset amplify export controls/status.
        self._reset_export_amplify_factor(os.path.basename(self.video_path) if self.video_path else None)
        media_kind = self.classify_media_type(self.video_path) if self.video_path else "media"
        self.amp_status_label.setText(f"Ready to amplify {media_kind}")

        # Reset Audio Studio file status so stale operation tags are cleared.
        if is_audio_only and self.video_path:
            self.audio_file_status.setText(f"✅ {os.path.basename(self.video_path)} (Audio)")
        else:
            self.audio_file_status.setText("No file loaded")

        # Keep conversion targets in sync with currently loaded media type.
        self.refresh_conversion_targets(self.video_path)

    def _sync_all_page_timer_defaults_from_media(self):
        """Apply loaded media duration to default rows on all timer pages."""
        try:
            total_ms = max(0, int(self.player.get_length()))
            total_s = total_ms // 1000
        except Exception:
            total_s = 0

        self._set_first_row_end_to_duration(self.video_trim_ranges_container, total_s)
        self._set_first_row_end_to_duration(self.audio_trim_ranges_container, total_s)
        self._set_first_row_end_to_duration(self.video_pw_ranges_container, total_s)
        self._set_first_row_end_to_duration(self.audio_pw_ranges_container, total_s)

    def _set_active_playback_window_controls(self, page_idx=None):
        """Bind playback-window helpers to the active page's controls (audio or video studio)."""
        try:
            if page_idx is None:
                page_idx = self.stack.currentIndex()
        except Exception:
            page_idx = PAGE_VIDEO_STUDIO

        if page_idx == PAGE_AUDIO_STUDIO and getattr(self, 'audio_pw_ranges_container', None) is not None:
            self.pw_ranges_container = self.audio_pw_ranges_container
            self.pw_add_range_btn = self.audio_pw_add_range_btn
            self.pw_add_range = self.audio_pw_add_range
            self.pw_status_label = self.audio_pw_status_label
        else:
            self.pw_ranges_container = self.video_pw_ranges_container
            self.pw_add_range_btn = self.video_pw_add_range_btn
            self.pw_add_range = self.video_pw_add_range
            self.pw_status_label = self.video_pw_status_label

    def create_audio_overlay(self):
        """Create an audio visualization overlay for the video frame area"""
        overlay = QLabel()
        overlay.setText("🎵 Audio File Loaded\n(Playing in player)")
        overlay.setAlignment(Qt.AlignCenter)
        overlay.setStyleSheet("""
            QLabel {
                background-color: rgba(30, 30, 30, 220);
                color: #2ecc71;
                font-size: 16px;
                font-weight: bold;
                border: 2px solid #2ecc71;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        overlay.hide()  # Hidden by default
        return overlay

    def _reposition_audio_overlay(self):
        """Called automatically on video frame resize — repositions overlay if visible."""
        if hasattr(self, 'audio_overlay') and self.audio_overlay.isVisible():
            self.show_audio_visualization()
    
    def show_audio_visualization(self):
        """Show audio visualization overlay when audio-only file is loaded"""
        if not hasattr(self, 'audio_overlay'):
            return
        
        # Get frame dimensions
        frame_width = self.video_frame.width()
        frame_height = self.video_frame.height()
        
        # If frame dimensions are still 0, retry after more delay
        if frame_width <= 0 or frame_height <= 0:
            from PySide6.QtCore import QTimer
            QTimer.singleShot(100, self.show_audio_visualization)
            return
        
        # Adjust overlay size and text based on available space
        is_audio_only = getattr(self, '_current_is_audio_only', False)
        if is_audio_only and frame_height < 150:
            # For small audio-only frame, use compact overlay that fits in available space
            overlay_width = max(60, min(180, frame_width - 10))
            overlay_height = max(35, min(55, frame_height - 5))
            self.audio_overlay.setText("🎵 Audio")
            self.audio_overlay.setStyleSheet("""
                QLabel {
                    background-color: rgba(30, 30, 30, 250);
                    color: #2ecc71;
                    font-size: 13px;
                    font-weight: bold;
                    border: 2px solid #2ecc71;
                    border-radius: 6px;
                    padding: 5px;
                }
            """)
        else:
            # For standard video frame, use larger overlay but still cap to frame size
            overlay_width = max(100, min(280, frame_width - 20))
            overlay_height = max(60, min(140, frame_height - 10))
            self.audio_overlay.setText("🎵 Audio File Loaded\n(Playing)")
            self.audio_overlay.setStyleSheet("""
                QLabel {
                    background-color: rgba(30, 30, 30, 250);
                    color: #2ecc71;
                    font-size: 15px;
                    font-weight: bold;
                    border: 2px solid #2ecc71;
                    border-radius: 8px;
                    padding: 10px;
                }
            """)
        
        self.audio_overlay.setFixedSize(overlay_width, overlay_height)
        
        # Position overlay in center of video frame
        overlay_x = max(0, (frame_width - overlay_width) // 2)
        overlay_y = max(0, (frame_height - overlay_height) // 2)
        self.audio_overlay.move(overlay_x, overlay_y)
        
        # Ensure overlay is visible and on top
        self.audio_overlay.raise_()
        self.audio_overlay.show()
    
    def hide_audio_visualization(self):
        """Hide audio visualization overlay when video is loaded"""
        if hasattr(self, 'audio_overlay'):
            self.audio_overlay.hide()
            self.audio_overlay.setFixedSize(300, 150)  # Reset to default size when hidden

    def _set_download_ui_busy(self, is_busy):
        """Disable download triggers while a download/load pipeline is active."""
        self._download_ui_busy = bool(is_busy)

        # Media Loader button + URL field
        if hasattr(self, 'media_loader_download_btn') and self.media_loader_download_btn is not None:
            self.media_loader_download_btn.setEnabled(not is_busy)
            self.media_loader_download_btn.setText("Downloading..." if is_busy else "Download and Load")
        if hasattr(self, 'url_input') and self.url_input is not None:
            self.url_input.setEnabled(not is_busy)

        # Keep Audio Studio URL download trigger in sync to prevent overlapping service calls.
        if hasattr(self, 'audio_dl_btn') and self.audio_dl_btn is not None:
            self.audio_dl_btn.setEnabled(not is_busy)

    def download_video(self):
        if self.download_service.is_downloading():
            QMessageBox.information(self, "Download Busy", "A download is already in progress. Please wait until it finishes.")
            self._set_download_ui_busy(True)
            return

        input_widget = self.url_input
        url = input_widget.text().strip()
        if not url.startswith("http"):
            QMessageBox.warning(self, "Validation Alert", "Provide target link URL parameters matching HTTP/HTTPS formats.")
            return

        self.status_label.setText("Status: Deploying Media Loader Task Pipes...")
        show_download_splash(self)

        if self.download_service.download_video(url, self.settings["download_directory"]):
            self._set_download_ui_busy(True)
        else:
            close_splash(self, "download_splash")
            self.status_label.setText("Status: Ready")
            self._set_download_ui_busy(False)

    def download_audio(self, audio_url_input):
        """Download audio from URL for audio tools page"""
        if self.download_service.is_downloading():
            QMessageBox.information(self, "Download Busy", "A download is already in progress. Please wait until it finishes.")
            self._set_download_ui_busy(True)
            return

        url = audio_url_input.text().strip()
        if not url.startswith("http"):
            QMessageBox.warning(self, "Validation Alert", "Provide target link URL parameters matching HTTP/HTTPS formats.")
            return

        self.status_label.setText("Status: Downloading audio...")
        show_download_splash(self, message="Initializing audio download...")

        self._download_from_audio_tools = True
        if self.download_service.download_video(
            url,
            self.settings["download_directory"],
            preferred_format="bestaudio/b"
        ):
            self._set_download_ui_busy(True)
        else:
            self._download_from_audio_tools = False
            close_splash(self, "download_splash")
            self.status_label.setText("Status: Ready")
            self._set_download_ui_busy(False)

    def _on_download_progress(self, percent, message):
        if self.download_splash:
            self.download_splash.set_progress(percent, message)

    def _on_download_finished(self, filename):
        close_splash(self, "download_splash")
        self.status_label.setText("Status: Ready")
        try:
            full_p = ""
            # Prefer exact filename from download service when available.
            if filename and os.path.exists(filename):
                full_p = os.path.normpath(filename)
            else:
                media_exts = ('.mp4', '.mkv', '.webm', '.avi', '.mov', '.mp3', '.m4a', '.aac', '.wav', '.flac', '.ogg', '.opus')
                targets = [f for f in os.listdir(self.settings["download_directory"]) if f.lower().endswith(media_exts)]
                if targets:
                    latest = max(targets, key=lambda x: os.path.getmtime(os.path.join(self.settings["download_directory"], x)))
                    full_p = os.path.normpath(os.path.join(self.settings["download_directory"], latest))
                
            if full_p:
                # Wait for file to be completely written and stable (not locked)
                if self._wait_for_file_ready(full_p):
                    if getattr(self, '_download_from_audio_tools', False):
                        media_type = self.classify_media_type(full_p)
                        if media_type != "audio":
                            QMessageBox.warning(
                                self,
                                "Audio Studio Only",
                                "Downloaded media contains video or unsupported streams. Use Media Loader for this URL."
                            )
                            return
                        self.audio_file_status.setText(f"✅ Downloaded: {os.path.basename(full_p)} (Audio)")
                        self.load_video(full_p, is_audio_only=True)
                    else:
                        self.url_input.clear()
                        self.load_video(full_p)
                else:
                    QMessageBox.warning(self, "File Access Error", "Downloaded file is locked or inaccessible. Please try again.")
        except Exception as e:
            QMessageBox.critical(self, "File Capture Error", f"Failed capturing downloaded file: {e}")
        finally:
            self._set_download_ui_busy(False)
            self._download_from_audio_tools = False

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
        close_splash(self, "download_splash")
        self.status_label.setText("Status: Ready")
        self._set_download_ui_busy(self.download_service.is_downloading())
        if "cancelled" in message.lower():
            return

        lowered = message.lower()
        if "unsupported url" in lowered or "unsupported" in lowered:
            QMessageBox.warning(
                self,
                "Unsupported Link",
                "This site/link is not supported by yt-dlp. Please use Media Loader with a supported URL or load a local file."
            )
            return

        QMessageBox.warning(self, "Download Error", message)

    def get_video_duration_via_ffprobe(self, target_path):
        return probe_duration_seconds(self.settings["ffprobe_path"], target_path, default=0)

    def get_audio_sample_rate_via_ffprobe(self, target_path):
        """Return first audio stream sample-rate, falling back to 44100."""
        return probe_audio_sample_rate(self.settings["ffprobe_path"], target_path)

    def export_video(self):
        if not self.video_path: return

        show_task_splash(self, "exporter")

        s, p = self.speed_input.value(), self.pitch_input.value()
        pf = 2**(p/12)
        # Keep pitch and tempo controls decoupled:
        # 1) asetrate changes pitch+tempo by pf
        # 2) atempo=1/pf restores original tempo
        # 3) atempo=s applies requested speed control
        pitch_comp = 1.0 / pf

        # Build output filename from original file name + pitch/speed tokens
        orig_name = os.path.splitext(os.path.basename(self.video_path))[0]
        def fmt(v):
            try:
                return ('%g' % float(v)).replace('.', '_')
            except:
                return str(v)

        p_token = None
        if p != 0:
            if p < 0:
                p_token = f"down_{fmt(abs(p))}"
            else:
                p_token = f"up_{fmt(p)}"

        s_token = None
        if s != 1.0:
            if s < 1.0:
                s_token = f"down_{fmt(s)}"
            else:
                s_token = f"up_{fmt(s)}"

        parts = [orig_name]
        if p_token: parts.append(p_token)
        if s_token: parts.append(s_token)
        out_name = "_".join(parts) + ".mp4"
        out = os.path.join(self.settings["download_directory"], out_name)
        abs_in = to_ffmpeg_path(self.video_path)
        abs_out = to_ffmpeg_path(out)
        input_sr = self.get_audio_sample_rate_via_ffprobe(abs_in)

        cmd = [self.settings["ffmpeg_path"], "-y", "-i", abs_in, "-filter_complex", 
               f"[0:v]setpts=PTS/{s}[v];[0:a]asetrate={input_sr}*{pf},aresample={input_sr},atempo={pitch_comp:.6f},atempo={s:.6f}[a]", 
               "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-b:v", "2000k", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", abs_out]

        duration = self.get_video_duration_via_ffprobe(abs_in) / s
        self.launch_async_task(cmd, abs_out, "exporter", override_duration=duration)

    def widen_active_video_canvas(self):
        target_input = self.video_path
        if not target_input or not os.path.exists(target_input):
            QMessageBox.warning(self, "Missing Asset Input", "Load a file path or complete a download segment beforehand.")
            return
        # Verify video aspect ratio first: if already ~16:9, warn user and ask confirmation.
        # When ffprobe is unavailable the widen attempt simply runs unverified.
        resolution = probe_video_resolution(self.settings["ffprobe_path"], target_input)
        if resolution and resolution[1] > 0:
            w, h = resolution
            ratio = w / h
            target_ratio = 16.0 / 9.0
            # Improved detection logic:
            # - If within 4% of 16:9, consider it already 16:9 and warn the user.
            # - If clearly narrow/portrait (ratio < 1.5) assume widening is appropriate.
            # - If ambiguous (1.5 <= ratio < ~1.7), ask the user with detected resolution and ratio.
            lower_wide = target_ratio * 0.96
            upper_wide = target_ratio * 1.04
            if lower_wide <= ratio <= upper_wide:
                # Very close to 16:9 — warn and ask
                reply = QMessageBox.question(self, "Already 16:9?",
                                             f"Detected resolution: {int(w)}x{int(h)} (ratio {ratio:.3f}).\n"
                                             "This appears to already be near 16:9. Running widen may add padding. Continue?",
                                             QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if reply != QMessageBox.Yes:
                    return
            elif ratio >= 1.5:
                # Ambiguous range — show more informative prompt with detected values
                reply = QMessageBox.question(self, "Widen Video - Confirm",
                                             f"Detected resolution: {int(w)}x{int(h)} (ratio {ratio:.3f}).\n"
                                             "This video is not exactly 16:9 and may be close to portrait/vertical.\n"
                                             "Do you want to run the widen operation anyway?",
                                             QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if reply != QMessageBox.Yes:
                    return

        show_task_splash(self, "widen_task")

        out = build_output_path(self.settings["download_directory"], target_input, "-wide", "mp4")

        abs_in = to_ffmpeg_path(target_input)
        abs_out = to_ffmpeg_path(out)

        crop_y = self.widen_crop_y_spin.value()
        filter_str = f"crop=in_w:in_h*0.3:0:in_h*{crop_y:.2f},scale=1920*1.1:1080*1.1:force_original_aspect_ratio=increase,crop=1920:1080"
        cmd = [self.settings["ffmpeg_path"], "-y", "-i", abs_in, "-vf", filter_str,
               "-preset", "ultrafast", "-c:a", "copy", abs_out]

        duration = self.get_video_duration_via_ffprobe(abs_in)
        self.launch_async_task(cmd, abs_out, "widen_task", override_duration=duration)

    def update_extraction_ui(self, is_video):
        return self.media_controller.update_extraction_ui(self, is_video)

    def load_audio_tools_file(self):
        return self.media_controller.load_audio_tools_file(self)
    
    def load_history_item(self, file_path):
        return self.media_controller.load_history_item(self, file_path)

    def classify_media_type(self, file_path):
        """Classify media file as audio, video, or unknown using ffprobe with extension fallback."""
        if not file_path or not os.path.exists(file_path):
            return "unknown"

        codec_types = probe_stream_codec_types(self.settings["ffprobe_path"], file_path)
        has_video = "video" in codec_types
        has_audio = "audio" in codec_types

        if has_video:
            return "video"
        if has_audio:
            return "audio"

        # Extension fallback when ffprobe stream probing is unavailable.
        ext = os.path.splitext(file_path)[1].lower()
        audio_exts = {'.mp3', '.wav', '.aac', '.m4a', '.flac', '.ogg', '.opus', '.wma'}
        video_exts = {'.mp4', '.avi', '.mkv', '.mov', '.webm', '.mts', '.m2ts'}
        if ext in video_exts:
            return "video"
        if ext in audio_exts:
            return "audio"
        return "unknown"

    def load_file(self, path):
        """Public API: load media for normal playback and real-time pitch workflow."""
        if not path or not os.path.exists(path):
            raise FileNotFoundError(f"Media file not found: {path}")

        media_type = self.classify_media_type(path)
        self.load_video(path, is_audio_only=(media_type == "audio"))
        self.realtime_pitch.load_file(path)
        self._refresh_realtime_pitch_status()

    def _is_realtime_pitch_enabled(self):
        return bool(self.realtime_pitch_toggle is not None and self.realtime_pitch_toggle.isChecked())

    def _sync_realtime_pitch_controls(self):
        """Push the pitch/speed spinbox values into the player and shifted-audio engine."""
        try:
            self.realtime_pitch.set_pitch(float(self.pitch_input.value()))
        except Exception:
            self.realtime_pitch.set_pitch(0.0)

        try:
            self.player.set_rate(float(self.speed_input.value()))
        except Exception:
            pass
        try:
            self.realtime_pitch.set_speed(float(self.speed_input.value()))
        except Exception:
            self.realtime_pitch.set_speed(1.0)

    def _is_realtime_neutral(self):
        """True when realtime mode should behave as passthrough (no pitch shift)."""
        try:
            return abs(float(self.pitch_input.value())) < 0.01
        except Exception:
            return True

    def _refresh_realtime_pitch_status(self):
        if self.realtime_pitch_status is None:
            return
        if not self._is_realtime_pitch_enabled():
            try:
                if self.realtime_pitch.is_active():
                    self.realtime_pitch_status.setText(f"Real-time pitch: retained ({self.pitch_input.value():+.1f} st)")
                    self.realtime_pitch_status.setStyleSheet("color: #8bc34a; font-size: 10px;")
                    return
            except Exception:
                pass
            self.realtime_pitch_status.setText("Real-time pitch: OFF")
            self.realtime_pitch_status.setStyleSheet("color: #888; font-size: 10px;")
            return

        if not self.video_path:
            self.realtime_pitch_status.setText("Real-time pitch: ON (load a file)")
            self.realtime_pitch_status.setStyleSheet("color: #f1c40f; font-size: 10px;")
            return

        if self._is_realtime_neutral():
            if self.player.is_active():
                self.realtime_pitch_status.setText("Real-time pitch: ON (neutral passthrough)")
            else:
                self.realtime_pitch_status.setText("Real-time pitch: ON (neutral)")
            self.realtime_pitch_status.setStyleSheet("color: #8bc34a; font-size: 10px;")
            return

        if self.realtime_pitch.is_active():
            self.realtime_pitch_status.setText(f"Real-time pitch: ACTIVE ({self.pitch_input.value():+.1f} st)")
            self.realtime_pitch_status.setStyleSheet("color: #2ecc71; font-size: 10px; font-weight: bold;")
        else:
            self.realtime_pitch_status.setText("Real-time pitch: ON (press Play)")
            self.realtime_pitch_status.setStyleSheet("color: #f1c40f; font-size: 10px;")

    def on_realtime_pitch_toggled(self, enabled):
        if not enabled:
            if getattr(self, '_live_amp_preview_active', False):
                self.stop_live_amplify_preview()
                return

            keep_shifted_playback = False
            try:
                keep_shifted_playback = (
                    self.realtime_pitch.is_active()
                    and self.player.is_active()
                    and not self._is_realtime_neutral()
                )
            except Exception:
                keep_shifted_playback = False

            if keep_shifted_playback:
                try:
                    self.player.set_mute(True)
                    self.player.set_rate(float(self.speed_input.value()))
                except Exception:
                    pass
                self._refresh_realtime_pitch_status()
                return

            try:
                if self.realtime_pitch.is_active():
                    self.realtime_pitch.stop()
            except Exception:
                pass

            try:
                self.player.set_mute(False)
                self.player.set_rate(float(self.speed_input.value()))
            except Exception:
                pass

            self._refresh_realtime_pitch_status()
            return

        if self.video_path:
            self.realtime_pitch.load_file(self.video_path)

        # Sync engine state to visible UI values so toggling ON is neutral at defaults.
        self._sync_realtime_pitch_controls()

        # If media is already playing, start shifted stream from current position.
        if self.player.is_active() and self.video_path:
            try:
                if self._is_realtime_neutral():
                    # Keep original VLC audio untouched at neutral pitch.
                    self.realtime_pitch.stop()
                    self.player.set_mute(False)
                else:
                    self.play_shifted(start_from_current=True)
            except Exception:
                pass

        self._refresh_realtime_pitch_status()

    def set_pitch(self, semitones):
        """Public API: set real-time pitch offset in semitones."""
        try:
            semitones = float(semitones)
        except Exception:
            semitones = 0.0

        # Keep UI and engine in sync.
        if hasattr(self, 'pitch_input') and self.pitch_input is not None:
            self.pitch_input.blockSignals(True)
            self.pitch_input.setValue(semitones)
            self.pitch_input.blockSignals(False)

        self.realtime_pitch.set_pitch(semitones)

        if not self._is_realtime_pitch_enabled():
            try:
                if self.realtime_pitch.is_active():
                    self.realtime_pitch.stop()
            except Exception:
                pass
            try:
                self.player.set_mute(False)
                self.player.set_rate(float(self.speed_input.value()))
            except Exception:
                pass
            self._refresh_realtime_pitch_status()
            return

        # In toggle-enabled mode, apply updated pitch during active playback within ~1s.
        if self._is_realtime_pitch_enabled() and self.video_path and self.player.is_active():
            if self._realtime_pitch_apply_timer is None:
                self._realtime_pitch_apply_timer = QTimer(self)
                self._realtime_pitch_apply_timer.setSingleShot(True)
                self._realtime_pitch_apply_timer.timeout.connect(
                    lambda: self.play_shifted(start_from_current=True)
                )
            self._realtime_pitch_apply_timer.start(250)

        self._refresh_realtime_pitch_status()

    def set_playback_speed(self, speed_value):
        """Keep VLC and realtime audio speed aligned with the Speed control."""
        try:
            speed = float(speed_value)
        except Exception:
            speed = 1.0

        speed = max(0.5, min(2.0, speed))

        try:
            self.player.set_rate(speed)
        except Exception:
            pass

        try:
            self.realtime_pitch.set_speed(speed)
        except Exception:
            pass

        # In realtime + active + non-neutral mode, speed change requires stream restart.
        if self._is_realtime_pitch_enabled() and self.video_path and self.player.is_active() and not self._is_realtime_neutral():
            if self._realtime_pitch_apply_timer is None:
                self._realtime_pitch_apply_timer = QTimer(self)
                self._realtime_pitch_apply_timer.setSingleShot(True)
                self._realtime_pitch_apply_timer.timeout.connect(
                    lambda: self.play_shifted(start_from_current=True)
                )
            self._realtime_pitch_apply_timer.start(180)

        self._refresh_realtime_pitch_status()

    def play_shifted(self, start_from_current=False):
        """Public API: play current media with real-time pitch-shifted audio.

        For video inputs, VLC continues rendering video while its audio is muted and
        the shifted audio is played through the low-latency sounddevice stream.
        """
        if not self.video_path:
            QMessageBox.warning(self, "No File", "Load a file first")
            return

        # Always apply currently shown controls before launching shifted stream.
        self._sync_realtime_pitch_controls()

        # At neutral pitch, do not route through shifted engine; preserve original playback.
        if self._is_realtime_neutral():
            try:
                self.realtime_pitch.stop()
                self.player.set_mute(False)
            except Exception:
                pass
            if self.video_path:
                self.status_label.setText(f"Status: Playing {os.path.basename(self.video_path)}")
            self._refresh_realtime_pitch_status()
            return

        self.realtime_pitch.load_file(self.video_path)

        player_was_active = False
        start_seconds = 0.0
        if start_from_current:
            try:
                player_was_active = bool(self.player.is_active())
                start_seconds = max(0.0, float(self.player.get_time() / 1000.0))
            except Exception:
                start_seconds = 0.0

        try:
            # Keep VLC timeline active and muted for both audio/video sources.
            # Important: while live-retuning during active playback, do NOT reset media,
            # otherwise UI timeline/seekbar jumps to 0 even though shifted audio starts later.
            if start_from_current and player_was_active:
                self.player.set_mute(True)
            else:
                self.player.set_media(os.path.abspath(self.video_path))
                self.player.set_video_widget(int(self.video_frame.winId()))
                self.player.set_mute(True)
                if start_seconds > 0:
                    self.player.set_time(int(start_seconds * 1000))
                self.player.play()
        except Exception as exc:
            QMessageBox.warning(self, "Playback Sync", f"Could not start media timeline: {exc}")

        try:
            self.realtime_pitch.play_shifted(start_seconds=start_seconds)
            self.audio_service.start_audio_monitoring()
            self.status_label.setText(
                f"Status: Real-time pitch playback ({self.realtime_pitch.pitch_semitones:+.1f} st)"
            )
            self._refresh_realtime_pitch_status()
        except Exception as exc:
            QMessageBox.warning(self, "Real-time Pitch", str(exc))
            self._refresh_realtime_pitch_status()

    def refresh_conversion_targets(self, file_path=None):
        """Update Convert & Export target formats based on selected source or detected media type."""
        if not hasattr(self, 'convert_target_combo'):
            return

        selected_source = self.convert_source_combo.currentText().strip().upper() if hasattr(self, 'convert_source_combo') else "AUTO-DETECT"
        audio_sources = {"MP3", "WAV", "M4A", "AAC", "FLAC", "OGG", "OPUS", "WMA", "AMR"}
        video_sources = {"MP4", "MKV", "AVI", "WEBM", "MOV", "MPEG", "MTS", "M2TS"}

        media_type = "unknown"
        if selected_source == "AUTO-DETECT":
            path_to_probe = file_path or self.video_path
            media_type = self.classify_media_type(path_to_probe) if path_to_probe else "unknown"
        elif selected_source in audio_sources:
            media_type = "audio"
        elif selected_source in video_sources:
            media_type = "video"

        current_target = self.convert_target_combo.currentText()
        self.convert_target_combo.blockSignals(True)
        self.convert_target_combo.clear()
        if media_type == "audio":
            self.convert_target_combo.addItems(["MP3", "WAV", "M4A", "AAC"])
            if hasattr(self, 'conversion_status_label'):
                self.conversion_status_label.setText("Audio source detected")
        else:
            self.convert_target_combo.addItems(["MP3", "WAV", "M4A", "AAC", "MP4", "MKV"])
            if hasattr(self, 'conversion_status_label'):
                if media_type == "video":
                    self.conversion_status_label.setText("Video source detected")
                else:
                    self.conversion_status_label.setText("Auto-detect mode active")

        idx = self.convert_target_combo.findText(current_target)
        if idx >= 0:
            self.convert_target_combo.setCurrentIndex(idx)
        self.convert_target_combo.blockSignals(False)

    def extract_audio_from_video(self):
        """Extract audio from video file and load it with selected format (WAV, MP3, AAC)"""
        # Extraction is owned by Video Studio and requires a video-loaded source.
        video_path = self.video_path
        if not video_path:
            QMessageBox.warning(self, "No Video", "Load a video from the Media Loader page first")
            return

        if self.classify_media_type(video_path) != "video":
            QMessageBox.warning(self, "No Video", "Current file is not a video. Load a video from Media Loader to extract audio.")
            return

        
        # Get selected format from combo
        selected_format = self.extract_format_combo.currentText().lower()
        
        # Determine file extension and FFmpeg codec parameters
        if selected_format == "mp3":
            ext = ".mp3"
            codec_args = ["-acodec", "libmp3lame", "-q:a", "0"]
        elif selected_format == "aac":
            ext = ".aac"
            codec_args = ["-acodec", "aac", "-q:a", "2"]
        else:  # WAV
            ext = ".wav"
            codec_args = []
        
        output_path = build_output_path(self.settings["download_directory"], video_path, "-extracted", ext)
        
        # Store output path for completion handler
        self._extract_output_path = output_path
        
        show_task_splash(self, "extract_task")

        # Build FFmpeg command
        abs_in = to_ffmpeg_path(video_path)
        abs_out = to_ffmpeg_path(output_path)
        cmd = [self.settings["ffmpeg_path"], "-y", "-i", abs_in] + codec_args + ["-map", "a", abs_out]

        duration = self.get_video_duration_via_ffprobe(abs_in)
        self.launch_async_task(cmd, abs_out, "extract_task", override_duration=duration)

    def trim_audio(self):
        """Export audio using row-based keep-ranges in Audio Studio."""
        if not self.video_path:
            QMessageBox.warning(self, "No File", "Load a file first")
            return

        target_format = self.trim_format_combo.currentText().lower()

        show_task_splash(self, "trim_task")

        duration = self.get_video_duration_via_ffprobe(to_ffmpeg_path(self.video_path))
        ranges_ms = self._collect_audio_trim_ranges(duration)
        if not ranges_ms:
            QMessageBox.warning(self, "No Trim Ranges", "Add at least one valid trim range (End must be after Start).")
            close_splash(self)
            return

        out = build_output_path(self.settings["download_directory"], self.video_path, "_trimmed", target_format)

        abs_in = to_ffmpeg_path(self.video_path)
        abs_out = to_ffmpeg_path(out)

        if len(ranges_ms) == 1:
            start_time = ranges_ms[0][0] / 1000.0
            end_time = ranges_ms[0][1] / 1000.0
            cmd = [
                self.settings["ffmpeg_path"], "-y", "-ss", str(start_time), "-to", str(end_time),
                "-i", abs_in, "-vn", "-acodec", "copy", abs_out
            ]
        else:
            cmd = self.build_audio_multi_trim_cmd(abs_in, abs_out, target_format, ranges_ms)

        trimmed_duration = sum((e - s) for s, e in ranges_ms) / 1000.0
        self.audio_trim_status_label.setText(f"Trimming audio ({len(ranges_ms)} range(s), {trimmed_duration:.1f}s total)...")
        self.launch_async_task(cmd, abs_out, "trim_task", override_duration=trimmed_duration)

    def _collect_audio_trim_ranges(self, duration_seconds):
        """Collect and normalize audio trim ranges from row controls (milliseconds)."""
        return range_rows.collect_ranges_ms(
            getattr(self, 'audio_trim_ranges_container', None), duration_seconds
        )

    def build_audio_multi_trim_cmd(self, input_file, output_file, target_fmt, ranges_ms):
        """Compatibility wrapper for the extracted audio trim builder."""
        return self.processing_controller.build_audio_multi_trim_cmd(
            self, input_file, output_file, target_fmt, ranges_ms
        )

    def clear_audio_trim_ranges(self):
        """Reset audio trim rows to one default range (0 to media duration)."""
        self._reset_trim_ranges(
            getattr(self, 'audio_trim_ranges_container', None),
            getattr(self, 'audio_trim_add_range', None),
            self.audio_trim_status_label,
            "Ready to trim audio",
        )

    def _on_audio_trim_add_range(self):
        """Add a new audio trim range row with sensible defaults based on previous row end."""
        self._append_trim_range(
            getattr(self, 'audio_trim_ranges_container', None),
            getattr(self, 'audio_trim_add_range', None),
            self.audio_trim_status_label,
            "Cannot add range — already covers to media end",
        )

    def _reset_trim_ranges(self, container, add_row_fn, status_label, ready_text):
        """Reset a trim tab to a single 0 -> media duration row and restore its ready status."""
        if container is None or container.layout() is None:
            return

        range_rows.reset_rows_to_single_range(
            container, add_row_fn, 0, self._get_current_media_duration_seconds()
        )
        status_label.setText(ready_text)

    def _append_trim_range(self, container, add_row_fn, status_label, exhausted_text):
        """Append a trim range row starting just after the last row's end."""
        if not callable(add_row_fn):
            return

        total_s = self._get_current_media_duration_seconds()
        prev_end_s = range_rows.last_row_end_seconds(container)

        if prev_end_s >= total_s and total_s > 0:
            status_label.setText(exhausted_text)
            return

        new_start = max(0, prev_end_s + 1)
        add_row_fn(new_start, max(new_start, total_s))

    def _get_current_media_duration_seconds(self):
        """Return current media duration in seconds from player or ffprobe fallback."""
        total_ms = max(0, int(self.player.get_length())) if self.player else 0
        if total_ms > 0:
            return total_ms // 1000

        if self.video_path:
            try:
                return int(self.get_video_duration_via_ffprobe(to_ffmpeg_path(self.video_path)))
            except Exception:
                return 0
        return 0

    def convert_audio_format(self):
        """Convert audio/video to different format (Feature 7)"""
        if not self.video_path:
            QMessageBox.warning(self, "No File", "Load a file first")
            return

        source_fmt = self.convert_source_combo.currentText()
        target_fmt = self.convert_target_combo.currentText().lower()
        quality_text = self.convert_quality_combo.currentText()

        # Extract bitrate from quality selector
        bitrate_map = {
            "High (320kbps)": "320k",
            "Medium (192kbps)": "192k",
            "Low (128kbps)": "128k"
        }
        bitrate = bitrate_map.get(quality_text, "192k")

        show_task_splash(self, "convert_task")

        out = build_output_path(self.settings["download_directory"], self.video_path, "_converted", target_fmt)

        abs_in = to_ffmpeg_path(self.video_path)
        abs_out = to_ffmpeg_path(out)

        # Build intelligent FFmpeg command based on target format
        cmd = self.build_format_conversion_cmd(abs_in, abs_out, target_fmt, bitrate)

        duration = self.get_video_duration_via_ffprobe(abs_in)
        self.launch_async_task(cmd, abs_out, "convert_task", override_duration=duration)

    def _format_amp_suffix(self, factor):
        """Create user-friendly suffix like amp_up_2_times or amp_down_3_times."""
        try:
            value = float(factor)
        except Exception:
            value = 1.0

        if value >= 1.0:
            if abs(value - round(value)) < 0.01:
                return f"amp_up_{int(round(value))}_times"
            return f"amp_up_{str(round(value, 2)).replace('.', '_')}_times"

        inverse = 1.0 / max(value, 0.0001)
        if abs(inverse - round(inverse)) < 0.01:
            return f"amp_down_{int(round(inverse))}_times"
        return f"amp_down_{str(round(inverse, 2)).replace('.', '_')}_times"

    def amplify_export_media(self):
        """Amplify loaded audio/video using ffmpeg and load the exported result."""
        if not self.video_path:
            QMessageBox.warning(self, "No File", "Load an audio or video file first")
            return

        amount = float(self.amp_factor_spin.value())
        if amount <= 0:
            QMessageBox.warning(self, "Invalid Amount", "Amplification amount must be greater than 0")
            return

        mode, amount, factor = self._get_export_amplify_selection()

        media_kind = self.classify_media_type(self.video_path)
        self._current_export_media_kind = media_kind

        show_task_splash(self, "amplify_task")

        suffix = self._format_amp_suffix(factor)

        src_ext = os.path.splitext(self.video_path)[1].lower().lstrip(".")
        audio_out_ext = src_ext if src_ext in {"mp3", "wav", "aac", "m4a", "flac", "ogg", "opus"} else "mp3"
        video_out_ext = "mp4"

        out_ext = audio_out_ext if media_kind == "audio" else video_out_ext
        out = build_output_path(self.settings["download_directory"], self.video_path, f"_{suffix}", out_ext)

        abs_in = to_ffmpeg_path(self.video_path)
        abs_out = to_ffmpeg_path(out)

        cmd = self.build_amplify_export_cmd(abs_in, abs_out, factor, media_kind, src_ext)
        duration = self.get_video_duration_via_ffprobe(abs_in)
        if mode == "reduce":
            self.amp_status_label.setText(f"Reducing amplification for {os.path.basename(self.video_path)} by {amount:.2f}x...")
        else:
            self.amp_status_label.setText(f"Amplifying {os.path.basename(self.video_path)} by {amount:.2f}x with anti-clipping limiter...")
        self.launch_async_task(cmd, abs_out, "amplify_task", override_duration=duration)

    def start_live_amplify_preview(self):
        """Preview the Amplify & Export settings in real time without writing a file."""
        if not self.video_path:
            QMessageBox.warning(self, "No File", "Load an audio or video file first")
            return

        if self._is_realtime_pitch_enabled():
            QMessageBox.information(
                self,
                "Real-time Pitch Active",
                "Turn Real-time Pitch Mode OFF on the Playback page before using Live Preview here."
            )
            self.amp_status_label.setText("Real-time Pitch Mode is ON; turn it OFF before Live Preview")
            return

        mode, amount, factor = self._get_export_amplify_selection()
        try:
            self.realtime_pitch.set_gain(factor)
            self.realtime_pitch.set_pitch(float(self.pitch_input.value()))
        except Exception:
            self.realtime_pitch.set_pitch(0.0)
        try:
            speed = float(self.speed_input.value())
            self.player.set_rate(speed)
            self.realtime_pitch.set_speed(speed)
        except Exception:
            self.realtime_pitch.set_speed(1.0)

        self.realtime_pitch.load_file(self.video_path)

        player_was_active = False
        start_seconds = 0.0
        try:
            player_was_active = bool(self.player.is_active())
            if player_was_active:
                start_seconds = max(0.0, float(self.player.get_time() / 1000.0))
        except Exception:
            player_was_active = False
            start_seconds = 0.0

        try:
            if player_was_active:
                self.player.set_mute(True)
            else:
                self.player.set_media(os.path.abspath(self.video_path))
                self.player.set_video_widget(int(self.video_frame.winId()))
                self.player.set_mute(True)
                self.player.play()
        except Exception as exc:
            self._clear_live_amplify_preview_state()
            QMessageBox.warning(self, "Live Preview", f"Could not start media timeline: {exc}")
            return

        try:
            self.realtime_pitch.play_shifted(start_seconds=start_seconds)
            self.audio_service.start_audio_monitoring()
        except Exception as exc:
            self._clear_live_amplify_preview_state()
            try:
                self.player.set_mute(False)
            except Exception:
                pass
            QMessageBox.warning(self, "Live Preview", str(exc))
            return

        self._live_amp_preview_active = True
        if self.amp_live_btn is not None:
            self.amp_live_btn.setEnabled(False)
        if self.amp_live_stop_btn is not None:
            self.amp_live_stop_btn.setEnabled(True)
        direction = "reduced" if mode == "reduce" else "amplified"
        self.amp_status_label.setText(f"Live preview active: {direction} by {amount:.2f}x (no export)")
        self.status_label.setText(f"Status: Live amplification preview ({factor:.2f}x)")
        self._refresh_realtime_pitch_status()

    def stop_live_amplify_preview(self):
        """Stop live amplification preview and restore the normal realtime audio state."""
        self._clear_live_amplify_preview_state()

        if self._is_realtime_pitch_enabled() and not self._is_realtime_neutral() and self.player.is_active():
            self.play_shifted(start_from_current=True)
            self.amp_status_label.setText("Live preview stopped; real-time pitch restored")
            return

        try:
            if self.realtime_pitch.is_active():
                self.realtime_pitch.stop()
            self.player.set_mute(False)
        except Exception:
            pass

        self.amp_status_label.setText("Live preview stopped")
        self.status_label.setText("Status: Ready")
        self._refresh_realtime_pitch_status()

    def build_amplify_export_cmd(self, input_file, output_file, factor, media_kind, src_ext):
        """Compatibility wrapper around the extracted processing controller."""
        return self.processing_controller.build_amplify_export_cmd(
            self, input_file, output_file, factor, media_kind, src_ext
        )

    def build_format_conversion_cmd(self, input_file, output_file, target_fmt, bitrate):
        """Compatibility wrapper around the extracted processing controller."""
        return self.processing_controller.build_format_conversion_cmd(
            self, input_file, output_file, target_fmt, bitrate
        )

    def normalize_audio(self):
        """Normalize audio loudness to consistent LUFS level (Feature 8)"""
        if not self.video_path:
            QMessageBox.warning(self, "No File", "Load a file first")
            return

        if not self.normalize_cb.isChecked():
            QMessageBox.information(self, "Normalization Disabled", "Check the 'Normalize Loudness' checkbox to proceed")
            return

        # Get target LUFS from dropdown
        lufs_text = self.normalize_lufs_combo.currentText()
        # Extract LUFS value: "-14 LUFS (Streaming)" → -14
        lufs_value = lufs_text.split()[0]  # Get "-14"

        show_task_splash(self, "normalize_task")

        out = build_output_path(self.settings["download_directory"], self.video_path, "_normalized", "wav")

        abs_in = to_ffmpeg_path(self.video_path)
        abs_out = to_ffmpeg_path(out)

        # Two-pass loudness normalization using FFmpeg
        # Pass 1: Analyze with loudnorm filter and capture JSON output
        ffmpeg_path = self.settings["ffmpeg_path"]
        
        # For simplicity, we'll use a single-pass approach with reasonable defaults
        # loudnorm filter parameters: I (integrated LUFS), LRA (loudness range), tp (true peak)
        loudnorm_filter = f"loudnorm=I={lufs_value}:LRA=11:tp=-1.5"
        
        cmd = [ffmpeg_path, "-y", "-i", abs_in, "-af", loudnorm_filter, "-acodec", "pcm_s16le", "-ar", "44100", abs_out]

        duration = self.get_video_duration_via_ffprobe(abs_in)
        self.launch_async_task(cmd, abs_out, "normalize_task", override_duration=duration)

    def select_merge_input_a(self):
        """Pick first input for Join & Merge tab."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Input A",
            self.settings["download_directory"],
            "Media Files (*.mp4 *.mkv *.avi *.mov *.webm *.mts *.m2ts *.mp3 *.wav *.aac *.m4a *.flac *.ogg *.opus *.wma);;All Files (*)",
        )
        if not path:
            return

        self.merge_input_a_path = path
        media_type = self._classify_media_type_for_merge(path)
        self._set_merge_input_display("A", path, media_type)
        self._update_merge_status_hint()

    def select_merge_input_b(self):
        """Pick second input for Join & Merge tab."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Input B",
            self.settings["download_directory"],
            "Media Files (*.mp4 *.mkv *.avi *.mov *.webm *.mts *.m2ts *.mp3 *.wav *.aac *.m4a *.flac *.ogg *.opus *.wma);;All Files (*)",
        )
        if not path:
            return

        self.merge_input_b_path = path
        media_type = self._classify_media_type_for_merge(path)
        self._set_merge_input_display("B", path, media_type)
        self._update_merge_status_hint()

    def _set_merge_input_display(self, slot, path, media_type):
        """Update Join & Merge controls so selected files are immediately obvious."""
        if slot not in {"A", "B"}:
            return

        base_name = os.path.basename(path)
        clipped_name = base_name if len(base_name) <= 38 else (base_name[:35] + "...")
        full_line = f"Input {slot} ({media_type.upper()}): {base_name}"
        detail_line = f"Path: {path}"

        if slot == "A":
            self.merge_input_a_btn.setText(f"✔ Input A selected: {clipped_name}")
            self.merge_input_a_btn.setStyleSheet("background-color: #1f7a4f; color: white; height: 36px; font-weight: bold;")
            self.merge_input_a_label.setText(f"{full_line}\n{detail_line}")
            self.merge_input_a_label.setStyleSheet("color: #d5ffe9; font-size: 11px; font-weight: bold;")
            self.merge_input_a_label.setToolTip(path)
            self.merge_input_a_btn.setToolTip(path)
            return

        self.merge_input_b_btn.setText(f"✔ Input B selected: {clipped_name}")
        self.merge_input_b_btn.setStyleSheet("background-color: #1f7a4f; color: white; height: 36px; font-weight: bold;")
        self.merge_input_b_label.setText(f"{full_line}\n{detail_line}")
        self.merge_input_b_label.setStyleSheet("color: #d5ffe9; font-size: 11px; font-weight: bold;")
        self.merge_input_b_label.setToolTip(path)
        self.merge_input_b_btn.setToolTip(path)

    def _classify_media_type_for_merge(self, file_path):
        """Classify media for Join & Merge with extension-first handling for audio files with artwork streams."""
        ext = os.path.splitext(file_path)[1].lower()
        audio_exts = {'.mp3', '.wav', '.aac', '.m4a', '.flac', '.ogg', '.opus', '.wma', '.amr'}
        video_exts = {'.mp4', '.avi', '.mkv', '.mov', '.webm', '.mts', '.m2ts', '.mpeg'}

        if ext in audio_exts:
            return "audio"
        if ext in video_exts:
            return "video"

        return self.classify_media_type(file_path)

    def _resolve_merge_behavior(self, mode):
        """Resolve append/overlay behavior from UI selection with type-based defaults."""
        selected = self.merge_mode_combo.currentText().strip().lower() if hasattr(self, "merge_mode_combo") else "auto"
        if "append" in selected:
            return "append"
        if "overlay" in selected:
            return "overlay"

        # Auto mode defaults:
        # - same-type joins use append
        # - mixed video+audio merge uses overlay
        if mode in {"audio_audio_join", "video_video_join"}:
            return "append"
        return "overlay"

    def _update_merge_status_hint(self):
        """Update Join & Merge status with resolved behavior preview."""
        input_a = getattr(self, "merge_input_a_path", "")
        input_b = getattr(self, "merge_input_b_path", "")
        if not input_a or not input_b:
            self.merge_status_label.setText("Ready. Select two files to begin.")
            return

        type_a = self._classify_media_type_for_merge(input_a)
        type_b = self._classify_media_type_for_merge(input_b)
        if "unknown" in {type_a, type_b}:
            self.merge_status_label.setText("Selected files are not recognized as audio/video.")
            return

        if {type_a, type_b} == {"video", "audio"}:
            mode = "video_audio_merge"
        elif type_a == "audio" and type_b == "audio":
            mode = "audio_audio_join"
        elif type_a == "video" and type_b == "video":
            mode = "video_video_join"
        else:
            self.merge_status_label.setText("Unsupported combination. Use video+audio, audio+audio, or video+video.")
            return

        behavior = self._resolve_merge_behavior(mode)
        offset_s = 0.0
        try:
            offset_s = float(self.merge_audio_offset_spin.value())
        except Exception:
            offset_s = 0.0

        if mode == "video_audio_merge" and behavior == "overlay":
            self.merge_status_label.setText(
                f"Ready: {mode.replace('_', ' ')} with {behavior} behavior (audio offset {offset_s:.2f}s)"
            )
        else:
            self.merge_status_label.setText(
                f"Ready: {mode.replace('_', ' ')} with {behavior} behavior"
            )

    def _resolve_join_merge_output(self, mode, input_a, input_b):
        """Resolve output path/extension based on selected mode and optional format override."""
        base_a = source_base_name(input_a)
        base_b = source_base_name(input_b)
        fmt_choice = self.merge_output_format_combo.currentText().strip().upper()
        behavior = self._resolve_merge_behavior(mode)

        if mode == "video_audio_merge":
            ext = "mp4"
            if fmt_choice in {"MP4", "MKV"}:
                ext = fmt_choice.lower()
            return os.path.join(self.settings["download_directory"], f"{base_a}_{base_b}_karaoke_merge.{ext}")

        if mode == "audio_audio_join":
            ext = "wav"
            if fmt_choice in {"WAV", "MP3"}:
                ext = fmt_choice.lower()
            suffix = "overlay" if behavior == "overlay" else "append"
            return os.path.join(self.settings["download_directory"], f"{base_a}_{base_b}_{suffix}.{ext}")

        # video_video_join
        ext = "mp4"
        if fmt_choice in {"MP4", "MKV"}:
            ext = fmt_choice.lower()
        suffix = "overlay" if behavior == "overlay" else "append"
        return os.path.join(self.settings["download_directory"], f"{base_a}_{base_b}_{suffix}.{ext}")

    def _build_join_merge_cmd(self, input_a, input_b, mode, out_path):
        """Compatibility wrapper for the extracted join/merge command builder."""
        return self.processing_controller._build_join_merge_cmd(self, input_a, input_b, mode, out_path)

    def execute_join_merge(self):
        """Execute media join/merge operation from Convert & Export tab."""
        input_a = getattr(self, "merge_input_a_path", "")
        input_b = getattr(self, "merge_input_b_path", "")

        if not input_a or not os.path.exists(input_a):
            QMessageBox.warning(self, "Missing Input", "Select Input A first")
            return
        if not input_b or not os.path.exists(input_b):
            QMessageBox.warning(self, "Missing Input", "Select Input B first")
            return

        type_a = self._classify_media_type_for_merge(input_a)
        type_b = self._classify_media_type_for_merge(input_b)
        if "unknown" in {type_a, type_b}:
            QMessageBox.warning(self, "Unsupported File", "Only audio and video files are supported")
            return

        if {type_a, type_b} == {"video", "audio"}:
            mode = "video_audio_merge"
        elif type_a == "audio" and type_b == "audio":
            mode = "audio_audio_join"
        elif type_a == "video" and type_b == "video":
            mode = "video_video_join"
        else:
            QMessageBox.warning(self, "Unsupported Combination", "Supported: video+audio, audio+audio, video+video")
            return

        out_path = self._resolve_join_merge_output(mode, input_a, input_b)
        abs_a = to_ffmpeg_path(input_a)
        abs_b = to_ffmpeg_path(input_b)
        abs_out = to_ffmpeg_path(out_path)

        cmd = self._build_join_merge_cmd(abs_a, abs_b, mode, abs_out)
        cmd_text = subprocess.list2cmdline([str(part) for part in cmd])
        self._last_merge_cmd_text = cmd_text
        self.log_debug(f"[merge_task] final_cmd | {cmd_text}")

        try:
            QApplication.clipboard().setText(cmd_text)
        except Exception:
            pass

        self.merge_status_label.setText("Final ffmpeg command copied to clipboard. Paste it anywhere to inspect.")
        self.merge_status_label.setToolTip(cmd_text)

        QMessageBox.information(
            self,
            "Join & Merge - Final ffmpeg Command",
            "Final ffmpeg command has been copied to clipboard.\n\n"
            "Paste (Ctrl+V) into Notepad/terminal to inspect or run manually.",
        )

        duration_hint = 0
        try:
            dur_a = self.get_video_duration_via_ffprobe(abs_a)
            dur_b = self.get_video_duration_via_ffprobe(abs_b)
            behavior = self._resolve_merge_behavior(mode)
            if mode == "video_video_join" and behavior == "overlay":
                duration_hint = min(dur_a, dur_b)
            elif mode == "video_video_join" and behavior == "append":
                duration_hint = dur_a + dur_b
            elif mode == "video_audio_merge" and behavior == "append":
                duration_hint = dur_a + dur_b
            elif mode == "video_audio_merge" and behavior == "overlay":
                try:
                    offset_s = max(0.0, float(self.merge_audio_offset_spin.value()))
                except Exception:
                    offset_s = 0.0
                duration_hint = min(dur_a, dur_b + offset_s)
            elif mode == "audio_audio_join" and behavior == "overlay":
                duration_hint = max(dur_a, dur_b)
            elif mode == "audio_audio_join" and behavior == "append":
                duration_hint = dur_a + dur_b
            else:
                duration_hint = min(dur_a, dur_b)
        except Exception:
            duration_hint = 0

        show_task_splash(self, "merge_task")

        behavior = self._resolve_merge_behavior(mode)
        self.merge_status_label.setText(f"Running {mode.replace('_', ' ')} with {behavior} behavior...")
        self.launch_async_task(cmd, abs_out, "merge_task", override_duration=duration_hint)

    def start_audio_separator(self):
        """Run the selected separator backend, defaulting to Demucs quality mode."""
        if not self.video_path:
            QMessageBox.warning(self, "No File", "Load an audio or video file first")
            return

        selection = self.vocal_model_combo.currentText()
        target_text = self.vocal_target_combo.currentText()
        output_format = self.vocal_output_format_combo.currentText().lower()
        fast_mode = self.vocal_fast_cb.isChecked()
        recovery_text = self.vocal_recovery_combo.currentText()
        recovery_mode_text = self.vocal_recovery_mode_combo.currentText()
        demucs_music_recovery = 0
        demucs_recovery_mode = "standard"
        try:
            demucs_music_recovery = int(str(recovery_text).split("%")[0].strip())
        except Exception:
            demucs_music_recovery = 0

        if recovery_mode_text.startswith("Side-heavy"):
            demucs_recovery_mode = "side_heavy"
        elif recovery_mode_text.startswith("Center-aware"):
            demucs_recovery_mode = "center_aware"

        if selection.startswith("Demucs:"):
            backend_name = "demucs"
            model_filename = "htdemucs_ft" if "htdemucs_ft" in selection else "htdemucs"
        else:
            backend_name = "audio-separator"
            if "UVR_MDXNET_KARA_2.onnx" in selection:
                model_filename = "UVR_MDXNET_KARA_2.onnx"
            else:
                model_filename = "UVR-MDX-NET-Voc_FT.onnx"

        target_map = {
            "Instrumental only (Recommended)": "instrumental_only",
            "Vocals only": "vocals_only",
            "Vocals + Instrumental": "both",
        }
        target_mode = target_map.get(target_text, "instrumental_only")

        model_dir = self._get_audio_separator_model_dir()
        enforce_offline_preflight = self._should_enforce_vocal_offline_preflight()

        # Team/offline packaged builds support only the bundled Demucs offline model.
        if enforce_offline_preflight and not self._is_packaged_offline_demucs_allowed(backend_name, model_filename):
            self.vocal_status_label.setText(
                "Internet required for this model in team build. Use Demucs: htdemucs_ft (Offline Team Build)."
            )
            return

        preflight_error = self._get_vocal_separator_preflight_error(
            backend_name,
            model_filename,
            model_dir,
            enforce_offline_preflight=enforce_offline_preflight,
        )
        if preflight_error:
            self.vocal_status_label.setText("Vocal Separator unavailable in this build")
            # For packaged team builds use in-page status only; avoid modal warning spam.
            if enforce_offline_preflight:
                self.vocal_status_label.setText(preflight_error.replace("\n", " "))
            else:
                QMessageBox.warning(self, "Vocal Separator", preflight_error)
            return

        # Point Demucs cache at local bundled/offline model directory so subprocess inherits it.
        if backend_name == "demucs":
            try:
                os.makedirs(model_dir, exist_ok=True)
                os.environ["TORCH_HOME"] = model_dir
            except Exception:
                pass

        self.log_debug(
            f"[audio_separator_task] start | input={self.video_path} | backend={backend_name} | model={model_filename} | "
            f"target={target_mode} | format={output_format} | fast_mode={fast_mode} | demucs_music_recovery={demucs_music_recovery}% | demucs_recovery_mode={demucs_recovery_mode}"
        )

        show_task_splash(
            self,
            "audio_separator_task",
            progress=5,
            message=f"Starting Vocal Separator ({model_filename})...",
        )

        os.makedirs(model_dir, exist_ok=True)

        self.kill_allocated_task("audio_separator_task")
        thread = AudioSeparatorThread(
            input_path=to_ffmpeg_path(self.video_path),
            ffmpeg_path=self.settings["ffmpeg_path"],
            output_dir=self.settings["download_directory"],
            backend_name=backend_name,
            model_filename=model_filename,
            output_format=output_format,
            target_mode=target_mode,
            fast_mode=fast_mode,
            model_file_dir=model_dir,
            demucs_music_recovery=demucs_music_recovery,
            demucs_recovery_mode=demucs_recovery_mode,
        )

        self.active_tasks["audio_separator_task"] = thread
        thread.status_update.connect(lambda text: self.vocal_status_label.setText(text))
        thread.status_update.connect(lambda text: self.export_splash.set_progress(self.export_splash.pbar.value(), text))
        thread.status_update.connect(lambda text: self.log_debug(f"[audio_separator_task] status | {text}"))
        thread.progress.connect(lambda v: self.export_splash.set_progress(v, self.export_splash.showMessageLabel.text()))
        thread.line_output.connect(lambda line: self.log_debug(f"[audio_separator_task] output | {line}"))
        thread.separator_done.connect(self.handle_audio_separator_completion)
        thread.finished.connect(lambda: self._finalize_audio_separator_thread("audio_separator_task"))
        thread.start()

    def _get_vocal_separator_offline_notice(self):
        return (
            "Offline team build supports only Demucs htdemucs_ft from bundled local models. "
            "Other separator models require internet/manual setup and are not offline-guaranteed."
        )

    def _get_audio_separator_model_dir(self):
        return os.path.join(self.settings["base_directory"], "config", "audio_separator_models")

    def _is_packaged_runtime(self):
        return bool(getattr(sys, "frozen", False) or hasattr(sys, "_MEIPASS"))

    def _should_enforce_vocal_offline_preflight(self):
        return self._is_packaged_runtime()

    def _is_packaged_offline_demucs_allowed(self, backend_name, model_filename):
        return backend_name == "demucs" and model_filename == "htdemucs_ft"

    def _update_vocal_separator_mode_notice(self):
        """Show non-modal guidance for model availability in packaged/offline team build."""
        try:
            selection = (self.vocal_model_combo.currentText() if self.vocal_model_combo else "").strip()
        except Exception:
            selection = ""

        if not self._should_enforce_vocal_offline_preflight():
            return

        if selection.startswith("Demucs:") and "htdemucs_ft" in selection:
            self.vocal_status_label.setText("Ready: Offline team build will run Demucs htdemucs_ft locally.")
            return

        self.vocal_status_label.setText(
            "Selected model requires internet/manual setup in team build. Use Demucs: htdemucs_ft for offline operation."
        )

    def _has_local_separator_model(self, model_filename, model_dir):
        if not os.path.isdir(model_dir):
            return False

        target = str(model_filename).lower()
        for root, _dirs, files in os.walk(model_dir):
            for file_name in files:
                if target in file_name.lower():
                    return True
        return False

    def _get_vocal_separator_preflight_error(self, backend_name, model_filename, model_dir, enforce_offline_preflight=False):
        missing_runtime = []

        if backend_name == "demucs":
            if importlib.util.find_spec("demucs") is None:
                missing_runtime.append("demucs")
            if importlib.util.find_spec("soundfile") is None:
                missing_runtime.append("soundfile")
        else:
            has_cli = shutil.which("audio-separator") is not None
            has_module = importlib.util.find_spec("audio_separator") is not None
            if not has_cli and not has_module:
                missing_runtime.append("audio-separator")

        if missing_runtime:
            notice_prefix = ""
            if enforce_offline_preflight:
                notice_prefix = self._get_vocal_separator_offline_notice() + "\n\n"
            return (
                notice_prefix
                + "This machine does not currently have the required separator backend installed: "
                + ", ".join(missing_runtime)
                + ".\n\nThe app will not start separator processing here, so it should fail safely rather than crash."
            )

        if enforce_offline_preflight and not self._has_local_separator_model(model_filename, model_dir):
            return (
                self._get_vocal_separator_offline_notice()
                + "\n\n"
                + f"Local model cache for '{model_filename}' was not found in {model_dir}. "
                + "On an offline team machine, the separator would not be able to fetch the missing model."
            )

        return ""

    def _finalize_audio_separator_thread(self, task_key):
        """Drop the audio separator thread reference only after QThread.finished fires."""
        self.active_tasks.pop(task_key, None)
        self.log_debug(f"[{task_key}] thread finished | reference released")

    def handle_audio_separator_completion(self, success, instrumental_path, vocals_path, error_text):
        """Handle completion callback for external audio-separator runs."""
        self.log_debug(
            f"[audio_separator_task] done | success={success} | instrumental={instrumental_path} | "
            f"vocals={vocals_path} | error={error_text}"
        )

        close_splash(self)

        self.status_label.setText("Status: Ready")

        if not success:
            self.vocal_status_label.setText("Audio separator failed")
            QMessageBox.warning(self, "Vocal Separator", error_text or "Audio separation failed")
            return

        chosen_target = self.vocal_target_combo.currentText()
        to_load = ""
        if chosen_target == "Vocals only":
            to_load = vocals_path
        elif chosen_target == "Vocals + Instrumental":
            to_load = instrumental_path if os.path.exists(instrumental_path) else vocals_path
        else:
            to_load = instrumental_path

        created = [p for p in [instrumental_path, vocals_path] if p and os.path.exists(p)]
        if to_load and os.path.exists(to_load):
            self.load_video(to_load, is_audio_only=True)
            self.audio_tools_file_path = to_load
            self.audio_file_status.setText(f"✅ {os.path.basename(to_load)} (Separated Stem)")

        if created:
            created_names = "\n".join([f"- {os.path.basename(p)}" for p in created])
            self.vocal_status_label.setText(f"✅ Audio separation complete ({len(created)} file(s))")
            QMessageBox.information(self, "Vocal Separator", f"Created stem file(s):\n{created_names}")
            QTimer.singleShot(100, lambda: self.handle_navigation_change(PAGE_CONVERT_EXPORT))
            return

        self.vocal_status_label.setText("Audio separation completed, but no output files were found")
        QMessageBox.warning(self, "Vocal Separator", "Separation finished but no output files were found.")

    def trim_video(self):
        """Trim video using range rows from Video Tools tab (similar to Playback Window)."""
        if not self.video_path:
            QMessageBox.warning(self, "No Video Loaded", "Load a video from the Media Loader page first")
            return

        # Extract target format
        target_fmt_text = self.video_trim_format_combo.currentText()
        if "MP4" in target_fmt_text:
            target_fmt = "mp4"
        elif "MKV" in target_fmt_text:
            target_fmt = "mkv"
        elif "WebM" in target_fmt_text:
            target_fmt = "webm"
        elif "AVI" in target_fmt_text:
            target_fmt = "avi"
        else:
            target_fmt = "mp4"

        duration = self.get_video_duration_via_ffprobe(to_ffmpeg_path(self.video_path))
        ranges_ms = self._collect_video_trim_ranges(duration)
        if not ranges_ms:
            QMessageBox.warning(self, "No Trim Ranges", "Add at least one valid trim range (End must be after Start).")
            return

        show_task_splash(self, "video_trim_task")

        out = build_output_path(self.settings["download_directory"], self.video_path, "_trimmed", target_fmt)

        abs_in = to_ffmpeg_path(self.video_path)
        abs_out = to_ffmpeg_path(out)

        if len(ranges_ms) == 1:
            start_time = ranges_ms[0][0] / 1000.0
            end_time = ranges_ms[0][1] / 1000.0
            cmd = self.build_video_trim_cmd(abs_in, abs_out, target_fmt, start_time, end_time)
        else:
            cmd = self.build_video_multi_trim_cmd(abs_in, abs_out, target_fmt, ranges_ms)

        trimmed_duration = sum((e - s) for s, e in ranges_ms) / 1000.0
        self.launch_async_task(cmd, abs_out, "video_trim_task", override_duration=trimmed_duration)
        self.video_trim_status_label.setText(f"Trimming video ({len(ranges_ms)} range(s), {trimmed_duration:.1f}s total)...")

    def _collect_video_trim_ranges(self, duration_seconds):
        """Collect and normalize trim ranges from trim range rows (milliseconds)."""
        return range_rows.collect_ranges_ms(
            getattr(self, 'video_trim_ranges_container', None), duration_seconds
        )

    def clear_video_trim_ranges(self):
        """Reset video trim rows to a single default range (0 to full video length)."""
        self._reset_trim_ranges(
            getattr(self, 'video_trim_ranges_container', None),
            getattr(self, 'video_trim_add_range', None),
            self.video_trim_status_label,
            "Ready to trim video",
        )

    def _on_video_trim_add_range(self):
        """Add a new trim range row with sensible defaults based on previous row end."""
        self._append_trim_range(
            getattr(self, 'video_trim_ranges_container', None),
            getattr(self, 'video_trim_add_range', None),
            self.video_trim_status_label,
            "Cannot add range — already covers to video end",
        )

    def _get_current_video_duration_seconds(self):
        """Return current video duration in seconds from player or ffprobe fallback."""
        return self._get_current_media_duration_seconds()

    def build_video_trim_cmd(self, input_file, output_file, target_fmt, start_time, end_time):
        """Build FFmpeg command for video trimming with format-specific codec selection"""
        ffmpeg_path = self.settings["ffmpeg_path"]
        duration = end_time - start_time
        
        if target_fmt == "mp4":
            # MP4: Re-encode with H.264 for best compatibility
            return [ffmpeg_path, "-y", "-ss", str(start_time), "-to", str(end_time), 
                    "-i", input_file, "-c:v", "libx264", "-preset", "fast", 
                    "-c:a", "aac", "-b:a", "192k", output_file]
        elif target_fmt == "mkv":
            # MKV: Copy video codec (faster), re-encode audio as AAC
            return [ffmpeg_path, "-y", "-ss", str(start_time), "-to", str(end_time),
                    "-i", input_file, "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", output_file]
        elif target_fmt == "webm":
            # WebM: Use VP9 for video, Opus for audio
            return [ffmpeg_path, "-y", "-ss", str(start_time), "-to", str(end_time),
                    "-i", input_file, "-c:v", "libvpx-vp9", "-crf", "30", "-b:v", "0",
                    "-c:a", "libopus", "-b:a", "192k", output_file]
        elif target_fmt == "avi":
            # AVI: Use MPEG-4 for video, MP3 for audio
            return [ffmpeg_path, "-y", "-ss", str(start_time), "-to", str(end_time),
                    "-i", input_file, "-c:v", "mpeg4", "-q:v", "5",
                    "-c:a", "libmp3lame", "-b:a", "192k", output_file]
        else:
            # Default to MP4
            return [ffmpeg_path, "-y", "-ss", str(start_time), "-to", str(end_time),
                    "-i", input_file, "-c:v", "libx264", "-preset", "fast",
                    "-c:a", "aac", "-b:a", "192k", output_file]

    def build_video_multi_trim_cmd(self, input_file, output_file, target_fmt, ranges_ms):
        """Compatibility wrapper for the extracted video trim builder."""
        return self.processing_controller.build_video_multi_trim_cmd(
            self, input_file, output_file, target_fmt, ranges_ms
        )

    def launch_async_task(self, cmd, out_path, task_key, override_duration=0):
        """Compatibility wrapper around the extracted processing lifecycle."""
        return self.processing_controller.launch_async_task(
            self, cmd, out_path, task_key, override_duration=override_duration
        )

    def kill_allocated_task(self, task_key):
        """Compatibility wrapper around the extracted task cancellation logic."""
        return self.processing_controller.kill_allocated_task(self, task_key)

    def stop_all_tasks(self):
        """Compatibility wrapper around the extracted shutdown task cleanup."""
        return self.processing_controller.stop_all_tasks(self)

    def handle_task_completion(self, task_key, out_path, success):
        """Compatibility wrapper around the extracted completion orchestration."""
        return self.processing_controller.handle_task_completion(self, task_key, out_path, success)

    def _return_to_widen_video_tab(self):
        """Return to Video Studio's Widen tab after a widen export reloads."""
        self.handle_navigation_change(PAGE_VIDEO_STUDIO)
        self.video_tools_tabs.setCurrentIndex(3)
        self._on_video_tools_tab_changed(3)

    def _return_to_amplify_export_tab(self):
        """Return to Convert & Export's Amplify tab after an amplify export reloads."""
        self.handle_navigation_change(PAGE_CONVERT_EXPORT)
        if self.convert_export_tabs is not None:
            self.convert_export_tabs.setCurrentIndex(4)

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
                self._player_was_active = True
                dur = self.player.get_length()
                if dur > 0 and not self.is_user_sliding:
                    ms = self.player.get_time()
                    safe_ms = max(0, min(int(ms), int(dur)))
                    # Show full duration in the final half-second so labels do not appear 1s short.
                    display_ms = int(dur) if (int(dur) - safe_ms) <= 500 else safe_ms
                    seek_ratio = min(1.0, float(display_ms) / float(dur)) if dur > 0 else 0.0
                    self.seek_slider.setValue(int(seek_ratio * 1000))
                    self.time_label.setText(f"{(display_ms//1000)//60:02d}:{(display_ms//1000)%60:02d}")
                    self.duration_label.setText(f"{(dur//1000)//60:02d}:{(dur//1000)%60:02d}")
                    # Playback Window: stop at end cutoff
                    pw_end_ms = getattr(self, '_pw_end_ms', None)
                    if pw_end_ms is not None and safe_ms >= pw_end_ms:
                        # If there are more ranges queued, advance to next range
                        ranges = getattr(self, '_pw_ranges', []) or []
                        idx = getattr(self, '_pw_range_idx', 0)
                        if ranges and idx + 1 < len(ranges):
                            # advance
                            print(f"[main.update_ui] advancing from range {idx} to {idx+1}")
                            self._pw_range_idx = idx + 1
                            next_start, next_end = ranges[self._pw_range_idx]
                            # seek to next start and set new end cutoff
                            QTimer.singleShot(50, lambda ns=next_start: self.player.set_time(int(ns)))
                            self._pw_end_ms = next_end
                            # update status
                            parts = [f"{(s//1000)//60:02d}:{(s//1000)%60:02d}-{(e//1000)//60:02d}:{(e//1000)%60:02d}" for s, e in ranges]
                            self.pw_status_label.setText("Ranges: " + ", ".join(parts))
                        else:
                            self._pw_end_ms = None  # clear immediately to prevent re-triggering on next tick
                            self.audio_service.stop_audio_monitoring()
                            self._player_was_active = False
                            try:
                                self.player.pause()
                                self.player.set_time(0)
                                self.player.set_position(0.0)
                            except Exception:
                                pass
                            self.seek_slider.setValue(0)
                            self.time_label.setText("00:00")
                            self.pw_status_label.setText("Playback window ended")
            else:
                # Only stop monitoring once when transitioning from active → inactive
                if getattr(self, '_player_was_active', False):
                    self.audio_service.stop_audio_monitoring()
                    self._player_was_active = False
                    # After natural end, rewind timeline to start while keeping media bound for replay.
                    try:
                        if self.player.has_media():
                            self.player.set_time(0)
                            self.player.set_position(0.0)
                        self.seek_slider.setValue(0)
                        self.time_label.setText("00:00")
                    except Exception:
                        pass
        except Exception as e:
            print(f"UI loop fault: {e}")

    def on_slider_pressed(self): self.is_user_sliding = True
    def on_slider_released(self):
        self.is_user_sliding = False
        target = self.seek_slider.value() / 1000.0
        if self.player.is_active() or self._ensure_media_loaded_for_playback():
            if self.player.is_active():
                self.player.set_position(target)
                self._resync_realtime_audio_after_seek()
                # Re-apply playback window start if user seeks back to zero
                if target == 0.0:
                    QTimer.singleShot(150, self.apply_playback_window)
            else:
                # In inactive/end states, store target and apply immediately after Play starts.
                self._pending_seek_ratio = target
                dur = int(self.player.get_length()) if self.player else -1
                if dur > 0:
                    preview_ms = int(max(0.0, min(1.0, target)) * dur)
                    self.time_label.setText(f"{(preview_ms//1000)//60:02d}:{(preview_ms//1000)%60:02d}")

    def handle_play(self):
        return self.playback_controller.handle_play(self)

    def handle_pause(self):
        return self.playback_controller.handle_pause(self)

    def handle_stop(self):
        return self.playback_controller.handle_stop(self)

    def apply_playback_window(self):
        return self.playback_controller.apply_playback_window(self)

    def clear_playback_window(self):
        return self.playback_controller.clear_playback_window(self)

    def _on_pw_add_range(self):
        return self.playback_controller._on_pw_add_range(self)

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

            # 4a. Remove video frame height cap so it fills the full screen
            self.video_frame.setMinimumHeight(0)
            self.video_frame.setMaximumHeight(16777215)

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

            # Restore correct video frame height constraints for the current page
            self.handle_navigation_change(self.stack.currentIndex())

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
            if hasattr(self, 'realtime_pitch') and self.realtime_pitch:
                self.realtime_pitch.stop()
        except Exception:
            pass

        try:
            # Stop player (uses pause-based cleanup to prevent VLC hang)
            if hasattr(self, 'player') and self.player:
                self.player.stop()
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

def log_uncaught_exception(exc_type, exc_value, exc_traceback):
    """Global uncaught exception handler for startup/runtime fatal errors."""
    try:
        app_dir = Path(sys._MEIPASS) if hasattr(sys, '_MEIPASS') else Path(__file__).parent.parent
        config_dir = app_dir / "config"
        config_dir.mkdir(exist_ok=True)
        log_file = config_dir / "app_debug.log"

        logger = logging.getLogger("karaoke_app_boot")
        logger.setLevel(logging.ERROR)
        logger.propagate = False
        if not logger.handlers:
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

        tb_text = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        logger.error("Uncaught exception:\n%s", tb_text)
    except Exception:
        pass

if __name__ == "__main__":
    sys.excepthook = log_uncaught_exception
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
