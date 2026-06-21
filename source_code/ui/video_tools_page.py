"""Video Tools page UI component - video trimming and playback window"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QCheckBox,
                               QComboBox, QTabWidget)
from PySide6.QtGui import QFont
from source_code.ui.extra_page import TimePickerWidget


def create_video_tools_page():
    page = QWidget()
    outer_layout = QVBoxLayout(page)
    outer_layout.setContentsMargins(10, 5, 10, 5)

    # Current file indicator (updated by handle_navigation_change)
    video_current_file_label = QLabel("No video loaded - use the Downloader page to load a video")
    video_current_file_label.setStyleSheet("color: #e67e22; font-style: italic; padding: 2px 5px; font-size: 10px;")
    outer_layout.addWidget(video_current_file_label)
    outer_layout.addSpacing(4)

    tabs = QTabWidget()
    outer_layout.addWidget(tabs)

    # ── TAB 1: VIDEO TRIMMING ────────────────────────────────────────────────
    trim_tab = QWidget()
    trim_layout = QVBoxLayout(trim_tab)
    trim_layout.setContentsMargins(6, 8, 6, 6)

    trim_title = QLabel("<b>VIDEO TRIMMING</b>")
    trim_title.setFont(QFont("Segoe UI", 11, QFont.Bold))
    trim_layout.addWidget(trim_title)

    trim_first_cb = QCheckBox("Trim First X seconds:")
    trim_first_picker = TimePickerWidget()
    for _sp in (trim_first_picker.hour_spin, trim_first_picker.min_spin, trim_first_picker.sec_spin):
        _sp.valueChanged.connect(lambda _v, cb=trim_first_cb: cb.setChecked(True))
    r = QHBoxLayout()
    r.addWidget(trim_first_cb); r.addWidget(trim_first_picker); r.addStretch()
    trim_layout.addLayout(r)

    trim_last_cb = QCheckBox("Trim Last X seconds:")
    trim_last_picker = TimePickerWidget()
    for _sp in (trim_last_picker.hour_spin, trim_last_picker.min_spin, trim_last_picker.sec_spin):
        _sp.valueChanged.connect(lambda _v, cb=trim_last_cb: cb.setChecked(True))
    r = QHBoxLayout()
    r.addWidget(trim_last_cb); r.addWidget(trim_last_picker); r.addStretch()
    trim_layout.addLayout(r)

    keep_range_cb = QCheckBox("Keep Range (from A to B):")
    keep_range_start_picker = TimePickerWidget()
    keep_range_end_picker = TimePickerWidget()
    keep_range_end_picker.set_total_seconds(60)
    for _sp in (keep_range_start_picker.hour_spin, keep_range_start_picker.min_spin, keep_range_start_picker.sec_spin,
                keep_range_end_picker.hour_spin, keep_range_end_picker.min_spin, keep_range_end_picker.sec_spin):
        _sp.valueChanged.connect(lambda _v, cb=keep_range_cb: cb.setChecked(True))
    r = QHBoxLayout()
    r.addWidget(keep_range_cb)
    r.addWidget(QLabel("Start:")); r.addWidget(keep_range_start_picker)
    r.addWidget(QLabel("End:")); r.addWidget(keep_range_end_picker)
    r.addStretch()
    trim_layout.addLayout(r)

    trim_format_combo = QComboBox()
    trim_format_combo.addItems(["MP4", "MKV", "WebM", "AVI"])
    trim_btn = QPushButton("Trim Video")
    trim_btn.setStyleSheet("background-color: #ff9800; height: 35px; font-weight: bold; color: white;")
    r = QHBoxLayout()
    r.addWidget(QLabel("Format:")); r.addWidget(trim_format_combo); r.addStretch(); r.addWidget(trim_btn)
    trim_layout.addLayout(r)

    trim_status_label = QLabel("Ready to trim video")
    trim_status_label.setStyleSheet("color: #888; font-size: 10px;")
    trim_layout.addWidget(trim_status_label)
    trim_layout.addStretch()

    tabs.addTab(trim_tab, "✂️ Video Trimming")

    # ── TAB 2: PLAYBACK WINDOW ───────────────────────────────────────────────
    pw_tab = QWidget()
    pw_layout = QVBoxLayout(pw_tab)
    pw_layout.setContentsMargins(6, 8, 6, 6)

    pw_title = QLabel("<b>PLAYBACK WINDOW</b>")
    pw_title.setFont(QFont("Segoe UI", 11, QFont.Bold))
    pw_layout.addWidget(pw_title)

    pw_desc = QLabel("Set start/end points applied when Play is pressed. Cleared on each new song.")
    pw_desc.setStyleSheet("color: #aaa; font-size: 9px; font-style: italic;")
    pw_desc.setWordWrap(True)
    pw_layout.addWidget(pw_desc)
    pw_layout.addSpacing(6)

    # Skip Start: jump to this position when Play is pressed
    pw_skip_cb = QCheckBox("Skip to position:")
    pw_skip_picker = TimePickerWidget()
    for _sp in (pw_skip_picker.hour_spin, pw_skip_picker.min_spin, pw_skip_picker.sec_spin):
        _sp.valueChanged.connect(lambda _v, cb=pw_skip_cb: cb.setChecked(True))
    r = QHBoxLayout()
    r.addWidget(pw_skip_cb); r.addWidget(pw_skip_picker); r.addStretch()
    pw_layout.addLayout(r)

    # Stop Before End: stop this many seconds before the track ends
    pw_stop_cb = QCheckBox("Stop N seconds before end:")
    pw_stop_picker = TimePickerWidget()
    for _sp in (pw_stop_picker.hour_spin, pw_stop_picker.min_spin, pw_stop_picker.sec_spin):
        _sp.valueChanged.connect(lambda _v, cb=pw_stop_cb: cb.setChecked(True))
    r = QHBoxLayout()
    r.addWidget(pw_stop_cb); r.addWidget(pw_stop_picker); r.addStretch()
    pw_layout.addLayout(r)

    # Play Range: play only from A to B
    pw_range_cb = QCheckBox("Play range from A to B:")
    pw_range_start_picker = TimePickerWidget()
    pw_range_end_picker = TimePickerWidget()
    for _sp in (pw_range_start_picker.hour_spin, pw_range_start_picker.min_spin, pw_range_start_picker.sec_spin,
                pw_range_end_picker.hour_spin, pw_range_end_picker.min_spin, pw_range_end_picker.sec_spin):
        _sp.valueChanged.connect(lambda _v, cb=pw_range_cb: cb.setChecked(True))
    r = QHBoxLayout()
    r.addWidget(pw_range_cb)
    r.addWidget(QLabel("From:")); r.addWidget(pw_range_start_picker)
    r.addWidget(QLabel("To:")); r.addWidget(pw_range_end_picker)
    r.addStretch()
    pw_layout.addLayout(r)

    pw_layout.addSpacing(8)
    btn_row = QHBoxLayout()
    pw_apply_btn = QPushButton("▶  Apply & Play")
    pw_apply_btn.setStyleSheet("background-color: #2ecc71; color: black; font-weight: bold; height: 32px;")
    pw_clear_btn = QPushButton("Clear")
    pw_clear_btn.setStyleSheet("background-color: #555; color: white; height: 32px; min-width: 80px;")
    btn_row.addWidget(pw_apply_btn)
    btn_row.addWidget(pw_clear_btn)
    pw_layout.addLayout(btn_row)

    pw_status_label = QLabel("No playback window active")
    pw_status_label.setStyleSheet("color: #888; font-size: 10px;")
    pw_layout.addWidget(pw_status_label)
    pw_layout.addStretch()

    tabs.addTab(pw_tab, "⏱ Playback Window")

    return {
        "page": page,
        "video_current_file_label": video_current_file_label,
        # Trim tab
        "trim_first_cb": trim_first_cb,
        "trim_first_picker": trim_first_picker,
        "trim_last_cb": trim_last_cb,
        "trim_last_picker": trim_last_picker,
        "keep_range_cb": keep_range_cb,
        "keep_range_start_picker": keep_range_start_picker,
        "keep_range_end_picker": keep_range_end_picker,
        "trim_format_combo": trim_format_combo,
        "trim_btn": trim_btn,
        "trim_status_label": trim_status_label,
        # Playback Window tab
        "pw_skip_cb": pw_skip_cb,
        "pw_skip_picker": pw_skip_picker,
        "pw_stop_cb": pw_stop_cb,
        "pw_stop_picker": pw_stop_picker,
        "pw_range_cb": pw_range_cb,
        "pw_range_start_picker": pw_range_start_picker,
        "pw_range_end_picker": pw_range_end_picker,
        "pw_apply_btn": pw_apply_btn,
        "pw_clear_btn": pw_clear_btn,
        "pw_status_label": pw_status_label,
    }
