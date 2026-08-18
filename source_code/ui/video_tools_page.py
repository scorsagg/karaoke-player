"""Video Tools page UI component - video trimming and playback window"""

# Module-level hook that main can set to provide the current video length (seconds)
video_length_getter = lambda: 0

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
                               QComboBox, QTabWidget, QDoubleSpinBox)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from source_code.ui.range_row_section import (STUDIO_TAB_STYLESHEET, add_playback_window_controls,
                                              create_range_row_section)


def create_video_tools_page():
    page = QWidget()
    outer_layout = QVBoxLayout(page)
    outer_layout.setContentsMargins(10, 5, 10, 5)

    # Current file indicator (updated by handle_navigation_change)
    video_current_file_label = QLabel("No video loaded - use the Media Loader page to load a video")
    video_current_file_label.setStyleSheet("color: #e67e22; font-style: italic; padding: 2px 5px; font-size: 10px;")
    outer_layout.addWidget(video_current_file_label)
    outer_layout.addSpacing(4)

    tabs = QTabWidget()
    tabs.setStyleSheet(STUDIO_TAB_STYLESHEET)
    outer_layout.addWidget(tabs)

    # ── TAB 1: VIDEO TRIMMING ────────────────────────────────────────────────
    trim_tab = QWidget()
    trim_layout = QVBoxLayout(trim_tab)
    trim_layout.setContentsMargins(6, 8, 6, 6)

    trim_title = QLabel("<b>VIDEO TRIMMING</b>")
    trim_title.setFont(QFont("Segoe UI", 11, QFont.Bold))
    trim_layout.addWidget(trim_title)

    trim_desc = QLabel("Set one or more keep-ranges to export. Ranges are concatenated in order.")
    trim_desc.setStyleSheet("color: #aaa; font-size: 9px; font-style: italic;")
    trim_desc.setWordWrap(True)
    trim_layout.addWidget(trim_desc)
    trim_layout.addSpacing(6)

    trim_ranges_container, add_trim_range_row = create_range_row_section(lambda: video_length_getter())

    add_trim_range_row(0, int(video_length_getter()))

    trim_add_range_btn = QPushButton("Add Range")
    trim_add_range_btn.setFixedWidth(120)
    trim_add_range_btn.setStyleSheet("background-color: #0e639c; color: white;")

    trim_layout.addWidget(QLabel("Trim Ranges (kept sequentially):"))
    trim_layout.addWidget(trim_ranges_container)
    trim_add_row = QHBoxLayout()
    trim_add_row.addStretch(); trim_add_row.addWidget(trim_add_range_btn)
    trim_layout.addLayout(trim_add_row)

    trim_format_combo = QComboBox()
    trim_format_combo.addItems(["MP4", "MKV", "WebM", "AVI"])
    trim_btn = QPushButton("Export Trimmed Video")
    trim_btn.setStyleSheet("background-color: #ff9800; height: 35px; font-weight: bold; color: white;")
    trim_clear_btn = QPushButton("Clear")
    trim_clear_btn.setStyleSheet("background-color: #555; color: white; height: 32px; min-width: 80px;")

    r = QHBoxLayout()
    r.addWidget(QLabel("Format:")); r.addWidget(trim_format_combo); r.addStretch(); r.addWidget(trim_btn); r.addWidget(trim_clear_btn)
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

    # Playback Ranges: allow multiple Start/End rows (add/remove). Removing down to one row
    # stretches the remaining row's End to the video length.
    ranges_container, add_range_row = create_range_row_section(
        lambda: video_length_getter(), sync_single_row_end=True
    )

    # Initial single range row (defaults to 0:00 - 0:00; main will adjust end to video length)
    add_range_row()

    # Add Range button
    pw_add_range_btn = QPushButton("Add Range")
    pw_add_range_btn.setFixedWidth(120)
    pw_add_range_btn.setStyleSheet("background-color: #0e639c; color: white;")
    # Expose add function for the host (main) to compute defaults
    pw_add_range_btn_func = add_range_row
    # Note: main.py should connect `pw_add_range_btn.clicked` to its own handler

    pw_apply_btn, pw_clear_btn, pw_status_label = add_playback_window_controls(
        pw_layout, ranges_container, pw_add_range_btn
    )

    tabs.addTab(pw_tab, "⏱ Playback Window")

    # ── TAB 4: AUDIO EXTRACTION ─────────────────────────────────────────────
    extract_tab = QWidget()
    extract_layout = QVBoxLayout(extract_tab)
    extract_layout.setContentsMargins(6, 8, 6, 6)

    extract_title = QLabel("<b>AUDIO EXTRACTION</b>")
    extract_title.setFont(QFont("Segoe UI", 11, QFont.Bold))
    extract_layout.addWidget(extract_title)

    extract_status_label = QLabel("Load a video from the Media Loader page to extract audio")
    extract_status_label.setStyleSheet("color: #e67e22; font-size: 10px; font-style: italic; padding: 2px 4px;")
    extract_layout.addWidget(extract_status_label)
    extract_layout.addSpacing(8)

    extract_format_row = QHBoxLayout()
    extract_format_row.addWidget(QLabel("Format:"))
    extract_format_combo = QComboBox()
    extract_format_combo.addItems(["WAV", "MP3", "AAC"])
    extract_format_combo.setMaximumWidth(140)
    extract_format_row.addWidget(extract_format_combo)
    extract_format_row.addStretch()
    extract_layout.addLayout(extract_format_row)

    extract_btn = QPushButton("Extract & Load Audio")
    extract_btn.setStyleSheet("background-color: #2ecc71; height: 35px; font-weight: bold; color: white;")
    extract_layout.addWidget(extract_btn)
    extract_layout.addStretch()

    tabs.addTab(extract_tab, "🎬 Audio Extraction")

    # ── TAB 5: WIDEN VIDEO ────────────────────────────────────────────────
    widen_tab = QWidget()
    widen_layout = QVBoxLayout(widen_tab)
    widen_layout.setContentsMargins(6, 8, 6, 6)

    widen_title = QLabel("<b>📐 ASPECT-RATIO CROP/ZOOM ENGINE</b>")
    widen_title.setFont(QFont("Segoe UI", 11, QFont.Bold))
    widen_layout.addWidget(widen_title)

    widen_current_file_label = QLabel("No video loaded - use the Media Loader page to load a video")
    widen_current_file_label.setStyleSheet("color: #e67e22; font-style: italic; padding: 2px 5px; font-size: 10px;")
    widen_layout.addWidget(widen_current_file_label)
    widen_layout.addSpacing(10)

    widen_crop_row = QHBoxLayout()
    widen_crop_row.addWidget(QLabel("Top crop offset:"))
    widen_crop_y_spin = QDoubleSpinBox()
    widen_crop_y_spin.setRange(0.0, 0.7)
    widen_crop_y_spin.setSingleStep(0.05)
    widen_crop_y_spin.setDecimals(2)
    widen_crop_y_spin.setValue(0.10)
    widen_crop_y_spin.setMaximumWidth(100)
    widen_crop_row.addWidget(widen_crop_y_spin)
    widen_crop_row.addWidget(QLabel("x video height"))
    widen_crop_row.addStretch()
    widen_layout.addLayout(widen_crop_row)

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
        "widen_crop_y_spin": widen_crop_y_spin,
        "widen_exec_btn": widen_exec_btn,
        # Trim tab
        "trim_ranges_container": trim_ranges_container,
        "trim_add_range_btn": trim_add_range_btn,
        "trim_add_range": add_trim_range_row,
        "trim_format_combo": trim_format_combo,
        "trim_btn": trim_btn,
        "trim_clear_btn": trim_clear_btn,
        "trim_status_label": trim_status_label,
        # Playback Window tab
        "pw_ranges_container": ranges_container,
        "pw_add_range_btn": pw_add_range_btn,
        "pw_add_range": pw_add_range_btn_func,
        "pw_apply_btn": pw_apply_btn,
        "pw_clear_btn": pw_clear_btn,
        "pw_status_label": pw_status_label,
        # Extraction tab
        "extract_status_label": extract_status_label,
        "extract_format_combo": extract_format_combo,
        "extract_btn": extract_btn,
    }
