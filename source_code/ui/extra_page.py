"""Extra tools pages UI component - video widening and audio tools (separate pages)"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QGridLayout, QPushButton, QLabel, QLineEdit, QFrame,
                               QTabWidget, QCheckBox, QDoubleSpinBox, QComboBox, QHBoxLayout, QSpinBox, QScrollArea, QSizePolicy)
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt


class TimePickerWidget(QWidget):
    """Custom widget with separate hour/minute/second spinners"""
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        # Style for vertically stacked buttons (up on top, down on bottom)
        spinbox_style = """
            QSpinBox {
                padding-right: 3px;
            }
            QSpinBox::up-button {
                subcontrol-origin: margin;
                subcontrol-position: top right;
                width: 22px;
                height: 22px;
                margin-top: 0px;
                margin-right: 0px;
            }
            QSpinBox::down-button {
                subcontrol-origin: margin;
                subcontrol-position: bottom right;
                width: 22px;
                height: 22px;
                margin-bottom: 0px;
                margin-right: 0px;
            }
        """
        
        # Hour spinbox
        self.hour_spin = QSpinBox()
        self.hour_spin.setRange(0, 59)
        self.hour_spin.setValue(0)
        self.hour_spin.setSingleStep(1)
        self.hour_spin.setMinimumWidth(45)
        self.hour_spin.setMaximumWidth(48)
        self.hour_spin.setMinimumHeight(40)
        self.hour_spin.setStyleSheet(spinbox_style)
        layout.addWidget(QLabel("H:"))
        layout.addWidget(self.hour_spin)
        layout.addSpacing(10)
        
        # Minute spinbox
        self.min_spin = QSpinBox()
        self.min_spin.setRange(0, 59)
        self.min_spin.setValue(0)
        self.min_spin.setSingleStep(1)
        self.min_spin.setMinimumWidth(45)
        self.min_spin.setMaximumWidth(48)
        self.min_spin.setMinimumHeight(40)
        self.min_spin.setStyleSheet(spinbox_style)
        layout.addWidget(QLabel("M:"))
        layout.addWidget(self.min_spin)
        layout.addSpacing(10)
        
        # Second spinbox
        self.sec_spin = QSpinBox()
        self.sec_spin.setRange(0, 59)
        self.sec_spin.setValue(0)
        self.sec_spin.setSingleStep(1)
        self.sec_spin.setMinimumWidth(45)
        self.sec_spin.setMaximumWidth(48)
        self.sec_spin.setMinimumHeight(40)
        self.sec_spin.setStyleSheet(spinbox_style)
        layout.addWidget(QLabel("S:"))
        layout.addWidget(self.sec_spin)
    
    def get_total_seconds(self):
        """Return total seconds as float"""
        return self.hour_spin.value() * 3600 + self.min_spin.value() * 60 + self.sec_spin.value()
    
    def set_total_seconds(self, seconds):
        """Set time from total seconds"""
        seconds = int(seconds)
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        
        self.hour_spin.setValue(hours)
        self.min_spin.setValue(minutes)
        self.sec_spin.setValue(secs)
    
    def get_display_text(self):
        """Return display as HH:MM:SS"""
        return f"{self.hour_spin.value():02d}:{self.min_spin.value():02d}:{self.sec_spin.value():02d}"




def create_widen_page():
    """Create and return the video widening page
    
    Returns:
        dict: Dictionary containing page widget and control references
    """
    widen_content = QWidget()
    layout = QVBoxLayout(widen_content)
    layout.setContentsMargins(10, 5, 10, 5)

    title = QLabel("<b>📐 ASPECT-RATIO LAYOUT PAD ENGINE</b>")
    title.setFont(QFont("Segoe UI", 11, QFont.Bold))
    layout.addWidget(title)

    grid = QGridLayout()
    
    widen_file_btn = QPushButton("📂 Open Widen File...")
    widen_file_btn.setFixedSize(140, 30)
    grid.addWidget(widen_file_btn, 1, 0)

    sep = QFrame()
    sep.setFrameShape(QFrame.VLine)
    sep.setStyleSheet("color: #3a3a3a;")
    grid.addWidget(sep, 1, 1)

    grid.addWidget(QLabel("<b>YouTube / Stream Link:</b>"), 0, 2)
    
    widen_url_input = QLineEdit()
    widen_url_input.setPlaceholderText("Paste target URL link here to download directly to Widen context...")
    widen_url_input.setStyleSheet("background-color: #333; border: 1px solid #555; padding: 5px; color: white;")
    widen_url_input.setFixedSize(540, 30)
    grid.addWidget(widen_url_input, 1, 2)

    widen_dl_btn = QPushButton("Download & Queue")
    widen_dl_btn.setFixedSize(140, 30)
    widen_dl_btn.setStyleSheet("background-color: #2ecc71; font-weight: bold; color: white;")
    grid.addWidget(widen_dl_btn, 1, 3)
    
    layout.addLayout(grid)

    widen_file_status_label = QLabel("Queued File for Widening: None (Will fallback to currently loaded player asset if blank)")
    widen_file_status_label.setStyleSheet("color: #e67e22; font-style: italic; padding: 5px 0px;")
    layout.addWidget(widen_file_status_label)
    layout.addSpacing(10)

    widen_exec_btn = QPushButton("Scale Active Video to Wide 16:9 Canvas")
    widen_exec_btn.setStyleSheet("background-color: #e67e22; height: 45px; font-weight: bold; font-size: 13px; color: white; border-radius: 4px;")
    layout.addWidget(widen_exec_btn)

    layout.addStretch()

    return {
        "page": widen_content,
        "widen_file_btn": widen_file_btn,
        "widen_url_input": widen_url_input,
        "widen_dl_btn": widen_dl_btn,
        "widen_file_status_label": widen_file_status_label,
        "widen_exec_btn": widen_exec_btn
    }


def create_audio_tools_page():
    """Create the audio tools page with file loading controls at top and tabs for extraction/trimming/conversion
    
    Returns:
        dict: Dictionary containing page widget and control references
    """
    page = QWidget()
    layout = QVBoxLayout(page)
    layout.setContentsMargins(10, 5, 10, 5)

    # ===== FILE LOADING CONTROLS (top section - like downloader page) =====
    loader_grid = QGridLayout()
    
    audio_file_btn = QPushButton("📂 Open Audio/Video File...")
    audio_file_btn.setFixedSize(180, 35)
    audio_file_btn.setStyleSheet("background-color: #2ecc71; font-weight: bold; color: white;")
    loader_grid.addWidget(audio_file_btn, 1, 0)

    sep = QFrame()
    sep.setFrameShape(QFrame.VLine)
    sep.setStyleSheet("color: #3a3a3a;")
    loader_grid.addWidget(sep, 1, 1)

    # URL input
    loader_grid.addWidget(QLabel("<b>YouTube / Stream URL:</b>"), 0, 2)
    audio_url_input = QLineEdit()
    audio_url_input.setPlaceholderText("Paste audio/video stream links here...")
    audio_url_input.setStyleSheet("background-color: #333; border: 1px solid #555; padding: 5px; color: white;")
    audio_url_input.setFixedSize(500, 30)
    loader_grid.addWidget(audio_url_input, 1, 2)

    audio_dl_btn = QPushButton("Download and Load")
    audio_dl_btn.setFixedSize(140, 30)
    audio_dl_btn.setStyleSheet("background-color: #2ecc71; font-weight: bold; color: white;")
    loader_grid.addWidget(audio_dl_btn, 1, 3)

    layout.addLayout(loader_grid)
    layout.addSpacing(5)

    # File status label
    audio_file_status = QLabel("No file loaded")
    audio_file_status.setStyleSheet("color: #e67e22; font-style: italic; padding: 2px 5px; font-size: 10px;")
    layout.addWidget(audio_file_status)
    layout.addSpacing(10)

    # Tab widget for internal sections
    tab_widget = QTabWidget()
    tab_widget.setStyleSheet("""
        QTabWidget::pane { border: 1px solid #3a3a3a; }
        QTabBar::tab { background-color: #2a2a2a; color: #fff; padding: 8px 20px; }
        QTabBar::tab:selected { background-color: #0e639c; }
    """)

    # ===== TAB 1: AUDIO EXTRACTION (from video files) =====
    extract_tab_page = QWidget()
    extract_layout = QVBoxLayout(extract_tab_page)
    extract_layout.setContentsMargins(10, 10, 10, 10)

    extract_title = QLabel("<b>🎬 AUDIO EXTRACTION</b>")
    extract_title.setFont(QFont("Segoe UI", 11, QFont.Bold))
    extract_layout.addWidget(extract_title)

    # Message shown when audio-only file is loaded
    extract_no_video_msg = QLabel("Load a video file to extract audio")
    extract_no_video_msg.setFont(QFont("Segoe UI", 13, QFont.Bold))
    extract_no_video_msg.setAlignment(Qt.AlignCenter)
    extract_no_video_msg.setStyleSheet("color: #888; padding: 40px;")
    extract_no_video_msg.setVisible(False)
    extract_layout.addWidget(extract_no_video_msg)

    extract_section = QLabel("<b>VIDEO FILE DETECTED</b>")
    extract_section.setFont(QFont("Segoe UI", 10, QFont.Bold))
    extract_section.setStyleSheet("color: #2ecc71;")
    extract_section.setVisible(False)
    extract_layout.addWidget(extract_section)

    extract_row = QHBoxLayout()
    extract_cb = QCheckBox("Extract audio from video")
    extract_cb.setVisible(False)
    extract_row.addWidget(extract_cb)
    extract_row.addStretch()
    extract_layout.addLayout(extract_row)

    # Format selection for extraction
    format_row = QHBoxLayout()
    format_label = QLabel("Format:")
    format_label.setStyleSheet("font-weight: bold;")
    extract_format_combo = QComboBox()
    extract_format_combo.addItems(["WAV", "MP3", "AAC"])
    extract_format_combo.setMaximumWidth(120)
    extract_format_combo.setVisible(False)
    format_row.addWidget(format_label)
    format_row.addWidget(extract_format_combo)
    format_row.addStretch()
    extract_layout.addLayout(format_row)

    extract_btn = QPushButton("Extract & Load Audio")
    extract_btn.setStyleSheet("background-color: #2ecc71; height: 35px; font-weight: bold; color: white;")
    extract_btn.setVisible(False)
    extract_layout.addWidget(extract_btn)

    extract_layout.addSpacing(20)
    extract_desc = QLabel("💡 Extract audio track from video files")
    extract_desc.setStyleSheet("color: #aaa; font-size: 11px;")
    extract_layout.addWidget(extract_desc)
    
    # Wrap in scroll area
    extract_scroll = QScrollArea()
    extract_scroll.setWidget(extract_tab_page)
    extract_scroll.setWidgetResizable(True)
    extract_scroll.setStyleSheet("QScrollArea { background-color: #1e1e1e; border: none; }")
    tab_widget.addTab(extract_scroll, "🎬 Audio Extraction")

    # Tab 2: Audio Trimming
    trim_tab_page = QWidget()
    trim_layout = QVBoxLayout(trim_tab_page)
    trim_layout.setContentsMargins(10, 10, 10, 10)

    # ===== TRIMMING CONTROLS =====
    trim_title = QLabel("<b>✂️ AUDIO TRIMMING</b>")
    trim_title.setFont(QFont("Segoe UI", 11, QFont.Bold))
    trim_layout.addWidget(trim_title)

    # Trim First
    trim_first_cb = QCheckBox("Trim First X seconds:")
    trim_first_spin = TimePickerWidget()
    trim_first_row = QHBoxLayout()
    trim_first_row.addWidget(trim_first_cb)
    trim_first_row.addWidget(trim_first_spin)
    trim_first_row.addStretch()
    trim_layout.addLayout(trim_first_row)

    # Trim Last
    trim_last_cb = QCheckBox("Trim Last X seconds:")
    trim_last_spin = TimePickerWidget()
    trim_last_row = QHBoxLayout()
    trim_last_row.addWidget(trim_last_cb)
    trim_last_row.addWidget(trim_last_spin)
    trim_last_row.addStretch()
    trim_layout.addLayout(trim_last_row)

    # Trim Range
    trim_range_cb = QCheckBox("Keep Range (from A to B):")
    trim_range_start = TimePickerWidget()
    trim_range_end = TimePickerWidget()
    trim_range_end.set_total_seconds(60)  # Default to 1 minute end
    trim_range_row = QHBoxLayout()
    trim_range_row.addWidget(trim_range_cb)
    trim_range_row.addWidget(QLabel("Start:"))
    trim_range_row.addWidget(trim_range_start)
    trim_range_row.addWidget(QLabel("End:"))
    trim_range_row.addWidget(trim_range_end)
    trim_range_row.addStretch()
    trim_layout.addLayout(trim_range_row)

    # Trim Export
    trim_format_combo = QComboBox()
    trim_format_combo.addItems(["MP3", "WAV", "AAC", "M4A"])
    trim_export_btn = QPushButton("Export Trimmed Audio")
    trim_export_btn.setStyleSheet("background-color: #2ecc71; height: 35px; font-weight: bold; color: white;")
    trim_export_row = QHBoxLayout()
    trim_export_row.addWidget(QLabel("Format:"))
    trim_export_row.addWidget(trim_format_combo)
    trim_export_row.addStretch()
    trim_export_row.addWidget(trim_export_btn)
    trim_layout.addLayout(trim_export_row)
    
    # Wrap in scroll area
    trim_scroll = QScrollArea()
    trim_scroll.setWidget(trim_tab_page)
    trim_scroll.setWidgetResizable(True)
    trim_scroll.setStyleSheet("QScrollArea { background-color: #1e1e1e; border: none; }")
    tab_widget.addTab(trim_scroll, "✂️ Audio Trimming")

    # Tab 3: Format Conversion
    conv_tab_page = QWidget()
    conv_layout = QVBoxLayout(conv_tab_page)
    conv_layout.setContentsMargins(10, 10, 10, 10)

    # ===== CONVERSION CONTROLS =====
    convert_title = QLabel("<b>🔄 FORMAT CONVERTER</b>")
    convert_title.setFont(QFont("Segoe UI", 11, QFont.Bold))
    conv_layout.addWidget(convert_title)

    # Source Format
    source_label = QLabel("Source Format:")
    convert_source_combo = QComboBox()
    convert_source_combo.addItems(["Auto-detect", "MP3", "WAV", "M4A", "AAC", "DAT", "MP4", "MKV", "AVI", "WebM"])
    source_row = QHBoxLayout()
    source_row.addWidget(source_label)
    source_row.addWidget(convert_source_combo)
    source_row.addStretch()
    conv_layout.addLayout(source_row)

    # Target Format
    target_label = QLabel("Target Format:")
    convert_target_combo = QComboBox()
    convert_target_combo.addItems(["MP3", "WAV", "M4A", "AAC", "MP4", "MKV"])
    target_row = QHBoxLayout()
    target_row.addWidget(target_label)
    target_row.addWidget(convert_target_combo)
    target_row.addStretch()
    conv_layout.addLayout(target_row)

    # Quality (for lossy formats)
    quality_label = QLabel("Quality (lossy formats):")
    convert_quality_combo = QComboBox()
    convert_quality_combo.addItems(["High (320kbps)", "Medium (192kbps)", "Low (128kbps)"])
    quality_row = QHBoxLayout()
    quality_row.addWidget(quality_label)
    quality_row.addWidget(convert_quality_combo)
    quality_row.addStretch()
    conv_layout.addLayout(quality_row)

    # Convert Button
    convert_btn = QPushButton("Convert & Export")
    convert_btn.setStyleSheet("background-color: #0e639c; height: 35px; font-weight: bold; color: white;")
    conv_layout.addWidget(convert_btn)
    
    # Wrap in scroll area
    conv_scroll = QScrollArea()
    conv_scroll.setWidget(conv_tab_page)
    conv_scroll.setWidgetResizable(True)
    conv_scroll.setStyleSheet("QScrollArea { background-color: #1e1e1e; border: none; }")
    tab_widget.addTab(conv_scroll, "🔄 Format Conversion")

    # Tab 4: Loudness Normalization
    norm_tab_page = QWidget()
    norm_layout = QVBoxLayout(norm_tab_page)
    norm_layout.setContentsMargins(10, 10, 10, 10)

    # ===== NORMALIZATION CONTROLS =====
    norm_title = QLabel("<b>📊 LOUDNESS NORMALIZATION</b>")
    norm_title.setFont(QFont("Segoe UI", 11, QFont.Bold))
    norm_layout.addWidget(norm_title)

    # Normalize checkbox
    normalize_cb = QCheckBox("Normalize Loudness")
    normalize_cb.setChecked(True)
    norm_layout.addWidget(normalize_cb)

    # Target LUFS selector
    lufs_row = QHBoxLayout()
    lufs_label = QLabel("Target LUFS:")
    lufs_label.setStyleSheet("font-weight: bold;")
    normalize_lufs_combo = QComboBox()
    normalize_lufs_combo.addItems(["-14 LUFS (Streaming)", "-16 LUFS (Broadcast)", "-18 LUFS (Loud)"])
    normalize_lufs_combo.setCurrentIndex(0)  # Default to -14
    normalize_lufs_combo.setMaximumWidth(220)
    lufs_row.addWidget(lufs_label)
    lufs_row.addWidget(normalize_lufs_combo)
    lufs_row.addStretch()
    norm_layout.addLayout(lufs_row)

    # Info text
    norm_info = QLabel("💡 Normalizes audio to consistent loudness level using two-pass analysis")
    norm_info.setStyleSheet("color: #aaa; font-size: 11px; margin: 10px 0px;")
    norm_layout.addWidget(norm_info)

    # Loudness details
    details_text = QLabel(
        "• -14 LUFS: Recommended for streaming platforms (Spotify, Apple Music)\n"
        "• -16 LUFS: Broadcast standard (TV, Radio)\n"
        "• -18 LUFS: Louder output, use with caution"
    )
    details_text.setStyleSheet("color: #999; font-size: 10px; margin: 5px 5px; padding: 5px; background-color: #2a2a2a; border-left: 2px solid #2ecc71;")
    norm_layout.addWidget(details_text)

    # Normalize button
    normalize_btn = QPushButton("Normalize & Export")
    normalize_btn.setStyleSheet("background-color: #2ecc71; height: 35px; font-weight: bold; color: white;")
    norm_layout.addWidget(normalize_btn)

    norm_layout.addSpacing(10)

    # Wrap in scroll area
    norm_scroll = QScrollArea()
    norm_scroll.setWidget(norm_tab_page)
    norm_scroll.setWidgetResizable(True)
    norm_scroll.setStyleSheet("QScrollArea { background-color: #1e1e1e; border: none; }")
    tab_widget.addTab(norm_scroll, "📊 Normalization")

    # Tab 5: DAT/WhatsApp File Conversion (Feature 19)
    dat_tab_page = QWidget()
    dat_layout = QVBoxLayout(dat_tab_page)
    dat_layout.setContentsMargins(10, 10, 10, 10)

    # ===== DAT CONVERSION CONTROLS =====
    dat_title = QLabel("<b>📱 DAT/WhatsApp Converter</b>")
    dat_title.setFont(QFont("Segoe UI", 11, QFont.Bold))
    dat_layout.addWidget(dat_title)

    # Info about DAT files
    dat_info = QLabel(
        "💡 Convert DAT files from WhatsApp, karaoke machines, or other sources\n"
        "Supported input formats: .dat, .opus, .amr, .aac, and more"
    )
    dat_info.setStyleSheet("color: #aaa; font-size: 10px; margin: 5px; padding: 8px; background-color: #2a2a2a; border-left: 2px solid #f39c12;")
    dat_layout.addWidget(dat_info)
    dat_layout.addSpacing(10)

    # Source Format (with auto-detect)
    dat_source_row = QHBoxLayout()
    dat_source_label = QLabel("Source Format:")
    dat_source_label.setStyleSheet("font-weight: bold;")
    dat_source_combo = QComboBox()
    dat_source_combo.addItems(["Auto-detect (Recommended)", ".dat (Generic)", ".opus (Audio Codec)", 
                                ".amr (Narrow-band)", ".aac (Audio Codec)", ".m4a (Audio MPEG-4)"])
    dat_source_combo.setCurrentIndex(0)
    dat_source_row.addWidget(dat_source_label)
    dat_source_row.addWidget(dat_source_combo)
    dat_source_row.addStretch()
    dat_layout.addLayout(dat_source_row)

    # Target Format
    dat_target_row = QHBoxLayout()
    dat_target_label = QLabel("Convert To:")
    dat_target_label.setStyleSheet("font-weight: bold;")
    dat_target_combo = QComboBox()
    dat_target_combo.addItems(["WAV (Lossless, CD Quality)", "MP3 (High Quality, Smaller)", 
                                "MP4 (Video Container)", "M4A (Audio MPEG-4)"])
    dat_target_combo.setCurrentIndex(0)  # Default to WAV
    dat_target_row.addWidget(dat_target_label)
    dat_target_row.addWidget(dat_target_combo)
    dat_target_row.addStretch()
    dat_layout.addLayout(dat_target_row)

    # Quality selector (for lossy formats)
    dat_quality_row = QHBoxLayout()
    dat_quality_label = QLabel("Quality (MP3/M4A):")
    dat_quality_label.setStyleSheet("font-weight: bold;")
    dat_quality_combo = QComboBox()
    dat_quality_combo.addItems(["High (320kbps)", "Medium (192kbps)", "Low (128kbps)"])
    dat_quality_combo.setCurrentIndex(0)  # Default to High
    dat_quality_row.addWidget(dat_quality_label)
    dat_quality_row.addWidget(dat_quality_combo)
    dat_quality_row.addStretch()
    dat_layout.addLayout(dat_quality_row)

    # Analysis option (for codec detection)
    dat_analyze_row = QHBoxLayout()
    dat_analyze_cb = QCheckBox("Auto-detect codec before conversion")
    dat_analyze_cb.setChecked(True)
    dat_analyze_row.addWidget(dat_analyze_cb)
    dat_analyze_row.addStretch()
    dat_layout.addLayout(dat_analyze_row)

    dat_layout.addSpacing(15)

    # Convert button
    dat_convert_btn = QPushButton("🚀 Convert DAT File")
    dat_convert_btn.setStyleSheet("background-color: #f39c12; height: 35px; font-weight: bold; color: white;")
    dat_layout.addWidget(dat_convert_btn)

    # Status/Log area
    dat_status_label = QLabel("Ready to convert")
    dat_status_label.setStyleSheet("color: #2ecc71; font-size: 10px; padding: 5px;")
    dat_layout.addWidget(dat_status_label)

    # WhatsApp formats note
    whatsapp_note = QLabel(
        "📋 Common WhatsApp formats detected:\n"
        "• .dat files (audio/video from WhatsApp Media/temp)\n"
        "• .opus files (WhatsApp voice messages)\n"
        "• .aac files (WhatsApp audio files)"
    )
    whatsapp_note.setStyleSheet("color: #999; font-size: 9px; margin: 10px; padding: 8px; background-color: #1a1a1a; border: 1px solid #333;")
    dat_layout.addWidget(whatsapp_note)

    dat_layout.addSpacing(10)

    # Wrap in scroll area
    dat_scroll = QScrollArea()
    dat_scroll.setWidget(dat_tab_page)
    dat_scroll.setWidgetResizable(True)
    dat_scroll.setStyleSheet("QScrollArea { background-color: #1e1e1e; border: none; }")
    tab_widget.addTab(dat_scroll, "📱 DAT Converter")

    # Add tab widget to main layout
    layout.addWidget(tab_widget)
    layout.addStretch()  # Allow tabs to expand and fill remaining space

    return {
        "page": page,
        # File/URL loading controls
        "audio_file_btn": audio_file_btn,
        "audio_file_status": audio_file_status,
        "audio_url_input": audio_url_input,
        "audio_dl_btn": audio_dl_btn,
        # Audio Extraction Tab controls
        "extract_section": extract_section,
        "extract_no_video_msg": extract_no_video_msg,
        "extract_cb": extract_cb,
        "extract_format_combo": extract_format_combo,
        "extract_btn": extract_btn,
        # Audio Trimming controls
        "trim_first_cb": trim_first_cb,
        "trim_first_spin": trim_first_spin,
        "trim_last_cb": trim_last_cb,
        "trim_last_spin": trim_last_spin,
        "trim_range_cb": trim_range_cb,
        "trim_range_start": trim_range_start,
        "trim_range_end": trim_range_end,
        "trim_format_combo": trim_format_combo,
        "trim_export_btn": trim_export_btn,
        # Audio Conversion controls
        "convert_source_combo": convert_source_combo,
        "convert_target_combo": convert_target_combo,
        "convert_quality_combo": convert_quality_combo,
        "convert_btn": convert_btn,
        # Audio Normalization controls
        "normalize_cb": normalize_cb,
        "normalize_lufs_combo": normalize_lufs_combo,
        "normalize_btn": normalize_btn,
        # DAT/WhatsApp Conversion controls (Feature 19)
        "dat_source_combo": dat_source_combo,
        "dat_target_combo": dat_target_combo,
        "dat_quality_combo": dat_quality_combo,
        "dat_analyze_cb": dat_analyze_cb,
        "dat_convert_btn": dat_convert_btn,
        "dat_status_label": dat_status_label,
    }
