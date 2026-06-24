"""Video Tools page UI component - video trimming and playback window"""

# Module-level hook that main can set to provide the current video length (seconds)
video_length_getter = lambda: 0

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
    tabs.setStyleSheet("""
        QTabWidget::pane { border: 1px solid #3a3a3a; }
        QTabBar::tab { background-color: #2a2a2a; color: #fff; padding: 8px 20px; }
        QTabBar::tab:selected { background-color: #0e639c; }
    """)
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

    # Playback Ranges: allow multiple Start/End rows (add/remove)
    ranges_container = QWidget()
    ranges_layout = QVBoxLayout(ranges_container)
    ranges_layout.setContentsMargins(0, 0, 0, 0)
    ranges_layout.setSpacing(8)

    def make_range_row(default_start=None, default_end=None):
        row_w = QWidget()
        row_l = QHBoxLayout(row_w)
        start_picker = TimePickerWidget()
        end_picker = TimePickerWidget()
        # Apply provided defaults (seconds)
        try:
            if default_start is not None:
                start_picker.set_total_seconds(int(default_start))
            if default_end is not None:
                end_picker.set_total_seconds(int(default_end))
        except Exception:
            pass
        remove_btn = QPushButton("Remove")
        remove_btn.setFixedWidth(80)
        remove_btn.setStyleSheet("background-color: #b00020; color: white;")

        row_l.addWidget(QLabel("Start:"))
        row_l.addWidget(start_picker)
        row_l.addSpacing(10)
        row_l.addWidget(QLabel("End:"))
        row_l.addWidget(end_picker)
        row_l.addWidget(remove_btn)
        row_l.addStretch()

        # Remove handler
        def _remove():
            for i in range(ranges_layout.count()):
                if ranges_layout.itemAt(i).widget() is row_w:
                    item = ranges_layout.takeAt(i)
                    w = item.widget()
                    if w:
                        w.deleteLater()
                    break
            # If no rows remain, add a default row with end = video length (if available)
            try:
                cnt = ranges_layout.count()
                if cnt == 0:
                    add_range_row(0, int(video_length_getter()))
                elif cnt == 1:
                    # If one row remains, ensure its end equals video length
                    remaining_row = ranges_layout.itemAt(0).widget()
                    if remaining_row:
                        pickers = remaining_row.findChildren(TimePickerWidget)
                        if len(pickers) >= 2:
                            try:
                                pickers[1].set_total_seconds(int(video_length_getter()))
                            except Exception:
                                pass
            except Exception:
                # best-effort; ignore failures
                pass
        remove_btn.clicked.connect(_remove)
        return row_w

    # Helper to add a range row with optional defaults
    def add_range_row(start_seconds=None, end_seconds=None):
        ranges_layout.addWidget(make_range_row(start_seconds, end_seconds))

    # Initial single range row (defaults to 0:00 - 0:00; main will adjust end to video length)
    add_range_row()

    # Add Range button
    pw_add_range_btn = QPushButton("Add Range")
    pw_add_range_btn.setFixedWidth(120)
    pw_add_range_btn.setStyleSheet("background-color: #0e639c; color: white;")
    # Expose add function for the host (main) to compute defaults
    pw_add_range_btn_func = add_range_row
    # Note: main.py should connect `pw_add_range_btn.clicked` to its own handler

    # Layout: label, ranges container, add button
    pw_layout.addWidget(QLabel("Playback Ranges (played sequentially):"))
    pw_layout.addWidget(ranges_container)
    add_row = QHBoxLayout()
    add_row.addStretch(); add_row.addWidget(pw_add_range_btn)
    pw_layout.addLayout(add_row)

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

    # ── TAB 3: WIDEN VIDEO ────────────────────────────────────────────────
    widen_tab = QWidget()
    widen_layout = QVBoxLayout(widen_tab)
    widen_layout.setContentsMargins(6, 8, 6, 6)

    widen_title = QLabel("<b>📐 ASPECT-RATIO LAYOUT PAD ENGINE</b>")
    widen_title.setFont(QFont("Segoe UI", 11, QFont.Bold))
    widen_layout.addWidget(widen_title)

    widen_current_file_label = QLabel("No video loaded - use the Downloader page to load a video")
    widen_current_file_label.setStyleSheet("color: #e67e22; font-style: italic; padding: 2px 5px; font-size: 10px;")
    widen_layout.addWidget(widen_current_file_label)
    widen_layout.addSpacing(10)

    widen_exec_btn = QPushButton("Scale Active Video to Wide 16:9 Canvas")
    widen_exec_btn.setStyleSheet("background-color: #e67e22; height: 45px; font-weight: bold; font-size: 13px; color: white; border-radius: 4px;")
    widen_layout.addWidget(widen_exec_btn)
    widen_layout.addStretch()

    tabs.addTab(widen_tab, "📐 Widen Video")

    return {
        "page": page,
        "tabs": tabs,
        "video_current_file_label": video_current_file_label,
        # Widen Video tab
        "widen_current_file_label": widen_current_file_label,
        "widen_exec_btn": widen_exec_btn,
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
        "pw_ranges_container": ranges_container,
        "pw_add_range_btn": pw_add_range_btn,
        "pw_add_range": pw_add_range_btn_func,
        "pw_apply_btn": pw_apply_btn,
        "pw_clear_btn": pw_clear_btn,
        "pw_status_label": pw_status_label,
    }
