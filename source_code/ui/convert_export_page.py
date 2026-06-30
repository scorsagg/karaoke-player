"""Convert & Export page UI component - cross-media conversion and normalization"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton, QTabWidget, QCheckBox, QDoubleSpinBox, QButtonGroup
)
from PySide6.QtGui import QFont


def create_convert_export_page():
    page = QWidget()
    layout = QVBoxLayout(page)
    layout.setContentsMargins(10, 5, 10, 5)

    tabs = QTabWidget()
    tabs.setStyleSheet("""
        QTabWidget::pane { border: 1px solid #3a3a3a; }
        QTabBar::tab { background-color: #2a2a2a; color: #fff; padding: 8px 20px; }
        QTabBar::tab:selected { background-color: #0e639c; }
    """)
    layout.addWidget(tabs)

    # Tab 1: Format Conversion
    conv_tab = QWidget()
    conv_layout = QVBoxLayout(conv_tab)
    conv_layout.setContentsMargins(10, 10, 10, 10)

    conv_title = QLabel("<b>FORMAT CONVERSION</b>")
    conv_title.setFont(QFont("Segoe UI", 11, QFont.Bold))
    conv_layout.addWidget(conv_title)

    conversion_status_label = QLabel("Auto-detect mode active")
    conversion_status_label.setStyleSheet("color: #888; font-size: 10px;")
    conv_layout.addWidget(conversion_status_label)

    source_row = QHBoxLayout()
    source_row.addWidget(QLabel("Source Format:"))
    convert_source_combo = QComboBox()
    convert_source_combo.addItems([
        "Auto-detect",
        "MP3", "WAV", "M4A", "AAC", "FLAC", "OGG", "OPUS", "WMA", "AMR",
        "MP4", "MKV", "AVI", "WebM", "MOV", "MPEG", "MTS", "M2TS"
    ])
    source_row.addWidget(convert_source_combo)
    source_row.addStretch()
    conv_layout.addLayout(source_row)

    target_row = QHBoxLayout()
    target_row.addWidget(QLabel("Target Format:"))
    convert_target_combo = QComboBox()
    convert_target_combo.addItems(["MP3", "WAV", "M4A", "AAC", "MP4", "MKV"])
    target_row.addWidget(convert_target_combo)
    target_row.addStretch()
    conv_layout.addLayout(target_row)

    quality_row = QHBoxLayout()
    quality_row.addWidget(QLabel("Quality (lossy formats):"))
    convert_quality_combo = QComboBox()
    convert_quality_combo.addItems(["High (320kbps)", "Medium (192kbps)", "Low (128kbps)"])
    quality_row.addWidget(convert_quality_combo)
    quality_row.addStretch()
    conv_layout.addLayout(quality_row)

    convert_btn = QPushButton("Convert & Export")
    convert_btn.setStyleSheet("background-color: #0e639c; height: 35px; font-weight: bold; color: white;")
    conv_layout.addWidget(convert_btn)
    conv_layout.addStretch()

    tabs.addTab(conv_tab, "🔄 Format Conversion")

    # Tab 2: Loudness Normalization
    norm_tab = QWidget()
    norm_layout = QVBoxLayout(norm_tab)
    norm_layout.setContentsMargins(10, 10, 10, 10)

    norm_title = QLabel("<b>LOUDNESS NORMALIZATION</b>")
    norm_title.setFont(QFont("Segoe UI", 11, QFont.Bold))
    norm_layout.addWidget(norm_title)

    normalize_cb = QCheckBox("Normalize Loudness")
    normalize_cb.setChecked(True)
    norm_row = QHBoxLayout()
    norm_row.addWidget(normalize_cb)
    norm_row.addStretch()
    norm_layout.addLayout(norm_row)

    lufs_row = QHBoxLayout()
    lufs_row.addWidget(QLabel("Target LUFS:"))
    normalize_lufs_combo = QComboBox()
    normalize_lufs_combo.addItems(["-14 LUFS (Streaming)", "-16 LUFS (Broadcast)", "-18 LUFS (Loud)"])
    lufs_row.addWidget(normalize_lufs_combo)
    lufs_row.addStretch()
    norm_layout.addLayout(lufs_row)

    norm_info = QLabel("Supports both audio and video inputs. Output is normalized audio.")
    norm_info.setStyleSheet("color: #aaa; font-size: 11px;")
    norm_layout.addWidget(norm_info)

    normalize_btn = QPushButton("Normalize & Export")
    normalize_btn.setStyleSheet("background-color: #2ecc71; height: 35px; font-weight: bold; color: white;")
    norm_layout.addWidget(normalize_btn)
    norm_layout.addStretch()

    tabs.addTab(norm_tab, "📊 Normalization")

    # Tab 3: Amplify & Export
    amp_tab = QWidget()
    amp_layout = QVBoxLayout(amp_tab)
    amp_layout.setContentsMargins(10, 10, 10, 10)

    amp_title = QLabel("<b>AMPLIFY & EXPORT</b>")
    amp_title.setFont(QFont("Segoe UI", 11, QFont.Bold))
    amp_layout.addWidget(amp_title)

    amp_info = QLabel("Applies ffmpeg volume gain to the loaded file, exports a new file, and loads it automatically.")
    amp_info.setStyleSheet("color: #aaa; font-size: 11px;")
    amp_info.setWordWrap(True)
    amp_layout.addWidget(amp_info)

    amp_source_label = QLabel("Load an audio or video file first, then amplify and export.")
    amp_source_label.setStyleSheet("color: #e67e22; font-size: 10px; font-style: italic;")
    amp_layout.addWidget(amp_source_label)

    amp_mode_row = QHBoxLayout()
    amp_mode_row.addWidget(QLabel("Mode:"))
    amp_mode_group = QButtonGroup(amp_tab)
    amp_mode_group.setExclusive(True)

    amp_plus_btn = QPushButton("Amplification + ▲")
    amp_plus_btn.setCheckable(True)
    amp_plus_btn.setChecked(True)
    amp_plus_btn.setProperty("amp_mode", "amplify")
    amp_plus_btn.setStyleSheet("background-color: #0e639c; color: white; font-weight: bold; min-width: 140px;")

    amp_minus_btn = QPushButton("Reduce amplification - ▼")
    amp_minus_btn.setCheckable(True)
    amp_minus_btn.setProperty("amp_mode", "reduce")
    amp_minus_btn.setStyleSheet("background-color: #2f2f2f; color: #ddd; min-width: 160px;")

    amp_mode_group.addButton(amp_plus_btn)
    amp_mode_group.addButton(amp_minus_btn)
    amp_mode_row.addWidget(amp_plus_btn)
    amp_mode_row.addWidget(amp_minus_btn)
    amp_mode_row.addStretch()
    amp_layout.addLayout(amp_mode_row)

    active_mode_style = "background-color: #0e639c; color: white; font-weight: bold; min-width: 140px;"
    inactive_mode_style = "background-color: #2f2f2f; color: #ddd; min-width: 160px;"

    def update_amp_mode_styles():
        if amp_plus_btn.isChecked():
            amp_plus_btn.setStyleSheet(active_mode_style)
            amp_minus_btn.setStyleSheet(inactive_mode_style)
        else:
            amp_plus_btn.setStyleSheet("background-color: #2f2f2f; color: #ddd; font-weight: bold; min-width: 140px;")
            amp_minus_btn.setStyleSheet("background-color: #0e639c; color: white; min-width: 160px;")

    amp_row = QHBoxLayout()
    amp_row.addWidget(QLabel("Amount:"))
    amp_factor_spin = QDoubleSpinBox()
    amp_factor_spin.setRange(0.25, 10.0)
    amp_factor_spin.setSingleStep(0.25)
    amp_factor_spin.setDecimals(2)
    amp_factor_spin.setValue(1.0)
    amp_factor_spin.setSuffix("x")
    amp_factor_spin.setToolTip("Choose a positive amount. Use the + button to amplify, or the - button to reduce.")
    amp_row.addWidget(amp_factor_spin)
    amp_row.addStretch()
    amp_layout.addLayout(amp_row)

    amp_note = QLabel("Examples: Amplification + 5.00x -> volume=5.0, Reduce amplification - 5.00x -> volume=0.2. FFmpeg uses volume=<factor>.")
    amp_note.setStyleSheet("color: #888; font-size: 10px;")
    amp_layout.addWidget(amp_note)

    amp_preview_label = QLabel("Selected export: Amplification + 1.00x")
    amp_preview_label.setStyleSheet("color: #aaa; font-size: 10px; font-style: italic;")
    amp_layout.addWidget(amp_preview_label)

    def update_amp_preview():
        update_amp_mode_styles()
        mode_button = amp_mode_group.checkedButton()
        mode = mode_button.property("amp_mode") if mode_button is not None else "amplify"
        amount = float(amp_factor_spin.value())
        if mode == "reduce":
            factor = 1.0 / max(amount, 0.01)
            amp_preview_label.setText(f"Selected export: Reduce amplification - {amount:.2f}x -> volume={factor:.2f}")
        else:
            amp_preview_label.setText(f"Selected export: Amplification + {amount:.2f}x -> volume={amount:.2f}")

    amp_factor_spin.valueChanged.connect(lambda _value: update_amp_preview())
    amp_plus_btn.toggled.connect(lambda _checked: update_amp_preview())
    amp_minus_btn.toggled.connect(lambda _checked: update_amp_preview())
    update_amp_preview()

    amp_btn = QPushButton("Export Amplified")
    amp_btn.setStyleSheet("background-color: #f39c12; height: 35px; font-weight: bold; color: white;")
    amp_layout.addWidget(amp_btn)

    amp_status_label = QLabel("Ready to amplify")
    amp_status_label.setStyleSheet("color: #888; font-size: 10px;")
    amp_layout.addWidget(amp_status_label)
    amp_layout.addStretch()

    tabs.addTab(amp_tab, "🔊 Amplify & Export")

    return {
        "page": page,
        "tabs": tabs,
        "convert_source_combo": convert_source_combo,
        "convert_target_combo": convert_target_combo,
        "convert_quality_combo": convert_quality_combo,
        "convert_btn": convert_btn,
        "conversion_status_label": conversion_status_label,
        "normalize_cb": normalize_cb,
        "normalize_lufs_combo": normalize_lufs_combo,
        "normalize_btn": normalize_btn,
        "amp_mode_group": amp_mode_group,
        "amp_factor_spin": amp_factor_spin,
        "amp_btn": amp_btn,
        "amp_source_label": amp_source_label,
        "amp_status_label": amp_status_label,
    }
