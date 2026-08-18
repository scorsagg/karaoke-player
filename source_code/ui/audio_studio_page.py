"""Audio Studio page UI component - audio-only tools"""

audio_length_getter = lambda: 0

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton, QTabWidget
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt
from source_code.ui.range_row_section import (STUDIO_TAB_STYLESHEET, add_playback_window_controls,
                                              create_range_row_section)


def create_audio_studio_page():
    page = QWidget()
    layout = QVBoxLayout(page)
    layout.setContentsMargins(10, 5, 10, 5)

    title = QLabel("<b>AUDIO STUDIO</b>")
    title.setFont(QFont("Segoe UI", 11, QFont.Bold))
    layout.addWidget(title)

    # File + URL loading controls (single row)
    file_row = QHBoxLayout()
    audio_file_btn = QPushButton("📂 Open Audio File...")
    audio_file_btn.setFixedSize(180, 35)
    audio_file_btn.setStyleSheet("background-color: #2ecc71; font-weight: bold; color: white;")
    file_row.addWidget(audio_file_btn)

    audio_url_label = QLabel("Audio URL:")
    from PySide6.QtWidgets import QLineEdit
    audio_url_input = QLineEdit()
    audio_url_input.setPlaceholderText("Paste an audio stream link here...")
    audio_url_input.setStyleSheet("background-color: #333; border: 1px solid #555; padding: 5px; color: white;")
    audio_dl_btn = QPushButton("Download and Load")
    audio_dl_btn.setStyleSheet("background-color: #2ecc71; font-weight: bold; color: white;")
    audio_dl_btn.setFixedHeight(30)
    file_row.addWidget(audio_url_label)
    file_row.addWidget(audio_url_input)
    file_row.addWidget(audio_dl_btn)
    layout.addLayout(file_row)

    audio_file_status = QLabel("No file loaded")
    audio_file_status.setStyleSheet("color: #e67e22; font-style: italic; padding: 2px 5px; font-size: 10px;")
    layout.addWidget(audio_file_status)

    layout.addSpacing(10)

    tabs = QTabWidget()
    tabs.setFocusPolicy(Qt.StrongFocus)
    tabs.setStyleSheet(STUDIO_TAB_STYLESHEET)
    layout.addWidget(tabs)

    # Tab 1: Audio Trimming
    trim_tab = QWidget()
    trim_tab_layout = QVBoxLayout(trim_tab)
    trim_tab_layout.setContentsMargins(10, 10, 10, 10)

    # Trim controls (row-based like video trimming/playback window)
    trim_title = QLabel("<b>✂️ AUDIO TRIMMING</b>")
    trim_title.setFont(QFont("Segoe UI", 11, QFont.Bold))
    trim_tab_layout.addWidget(trim_title)

    trim_desc = QLabel("Set one or more keep-ranges to export. Ranges are concatenated in order.")
    trim_desc.setStyleSheet("color: #aaa; font-size: 9px; font-style: italic;")
    trim_desc.setWordWrap(True)
    trim_tab_layout.addWidget(trim_desc)

    trim_ranges_container, add_trim_range_row = create_range_row_section(lambda: audio_length_getter())

    add_trim_range_row(0, int(audio_length_getter()))

    trim_add_range_btn = QPushButton("Add Range")
    trim_add_range_btn.setFixedWidth(120)
    trim_add_range_btn.setStyleSheet("background-color: #0e639c; color: white;")

    trim_tab_layout.addWidget(QLabel("Trim Ranges (kept sequentially):"))
    trim_tab_layout.addWidget(trim_ranges_container)
    trim_add_row = QHBoxLayout()
    trim_add_row.addStretch(); trim_add_row.addWidget(trim_add_range_btn)
    trim_tab_layout.addLayout(trim_add_row)

    trim_export_row = QHBoxLayout()
    trim_export_row.addWidget(QLabel("Format:"))
    trim_format_combo = QComboBox()
    trim_format_combo.addItems(["MP3", "WAV", "AAC", "M4A"])
    trim_export_row.addWidget(trim_format_combo)
    trim_export_row.addStretch()
    trim_btn = QPushButton("Export Trimmed Audio")
    trim_btn.setStyleSheet("background-color: #2ecc71; height: 35px; font-weight: bold; color: white;")
    trim_clear_btn = QPushButton("Clear")
    trim_clear_btn.setStyleSheet("background-color: #555; color: white; height: 32px; min-width: 80px;")
    trim_export_row.addWidget(trim_btn)
    trim_export_row.addWidget(trim_clear_btn)
    trim_tab_layout.addLayout(trim_export_row)

    trim_status_label = QLabel("Ready to trim audio")
    trim_status_label.setStyleSheet("color: #888; font-size: 10px;")
    trim_tab_layout.addWidget(trim_status_label)
    trim_tab_layout.addStretch()

    tabs.addTab(trim_tab, "✂️ Audio Trimming")

    # Tab 2: Playback Window
    pw_tab = QWidget()
    pw_layout = QVBoxLayout(pw_tab)
    pw_layout.setContentsMargins(10, 10, 10, 10)

    pw_title = QLabel("<b>PLAYBACK WINDOW</b>")
    pw_title.setFont(QFont("Segoe UI", 11, QFont.Bold))
    pw_layout.addWidget(pw_title)

    pw_desc = QLabel("Set start/end points applied when Play is pressed. Cleared on each new song.")
    pw_desc.setStyleSheet("color: #aaa; font-size: 9px; font-style: italic;")
    pw_desc.setWordWrap(True)
    pw_layout.addWidget(pw_desc)
    pw_layout.addSpacing(6)

    pw_ranges_container, add_pw_range_row = create_range_row_section(lambda: audio_length_getter())

    add_pw_range_row(0, int(audio_length_getter()))

    pw_add_range_btn = QPushButton("Add Range")
    pw_add_range_btn.setFixedWidth(120)
    pw_add_range_btn.setStyleSheet("background-color: #0e639c; color: white;")

    pw_apply_btn, pw_clear_btn, pw_status_label = add_playback_window_controls(
        pw_layout, pw_ranges_container, pw_add_range_btn
    )

    tabs.addTab(pw_tab, "⏱ Playback Window")

    layout.addStretch()

    return {
        "page": page,
        "tabs": tabs,
        "audio_file_btn": audio_file_btn,
        "audio_file_status": audio_file_status,
        "audio_url_input": audio_url_input,
        "audio_dl_btn": audio_dl_btn,
        "trim_ranges_container": trim_ranges_container,
        "trim_add_range_btn": trim_add_range_btn,
        "trim_add_range": add_trim_range_row,
        "trim_format_combo": trim_format_combo,
        "trim_btn": trim_btn,
        "trim_clear_btn": trim_clear_btn,
        "trim_status_label": trim_status_label,
        "pw_ranges_container": pw_ranges_container,
        "pw_add_range_btn": pw_add_range_btn,
        "pw_add_range": add_pw_range_row,
        "pw_apply_btn": pw_apply_btn,
        "pw_clear_btn": pw_clear_btn,
        "pw_status_label": pw_status_label,
    }
