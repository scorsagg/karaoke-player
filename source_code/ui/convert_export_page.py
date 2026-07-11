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

    # Tab 3: Vocal Separator
    vocal_tab = QWidget()
    vocal_layout = QVBoxLayout(vocal_tab)
    vocal_layout.setContentsMargins(10, 10, 10, 10)

    vocal_title = QLabel("<b>VOCAL SEPARATOR</b>")
    vocal_title.setFont(QFont("Segoe UI", 11, QFont.Bold))
    vocal_layout.addWidget(vocal_title)

    vocal_info = QLabel(
        "Defaults to Demucs for higher quality vocal separation on Python 3.13. "
        "A faster audio-separator UVR path is still available when speed matters more than quality."
    )
    vocal_info.setStyleSheet("color: #aaa; font-size: 11px;")
    vocal_info.setWordWrap(True)
    vocal_layout.addWidget(vocal_info)

    vocal_source_label = QLabel(
        "Demucs works best from the Python 3.13 environment. UVR/audio-separator remains available as a faster alternative."
    )
    vocal_source_label.setStyleSheet("color: #e67e22; font-size: 10px; font-style: italic;")
    vocal_source_label.setWordWrap(True)
    vocal_layout.addWidget(vocal_source_label)

    vocal_offline_warning_label = QLabel(
        "Vocal Separator is not included in the offline team build. "
        "This feature may require internet access and additional model/backend downloads on first use."
    )
    vocal_offline_warning_label.setStyleSheet(
        "color: #f5c26b; font-size: 10px; font-weight: bold; "
        "background-color: #3a2412; border: 1px solid #8a5a2b; padding: 8px; border-radius: 4px;"
    )
    vocal_offline_warning_label.setWordWrap(True)
    vocal_layout.addWidget(vocal_offline_warning_label)

    model_row = QHBoxLayout()
    model_row.addWidget(QLabel("Backend / Model:"))
    vocal_model_combo = QComboBox()
    vocal_model_combo.addItems([
        "Demucs: htdemucs_ft (High Quality Default)",
        "Demucs: htdemucs (Faster)",
        "audio-separator: UVR-MDX-NET-Voc_FT.onnx (Fast)",
        "audio-separator: UVR_MDXNET_KARA_2.onnx",
    ])
    model_row.addWidget(vocal_model_combo)
    model_row.addStretch()
    vocal_layout.addLayout(model_row)

    target_row = QHBoxLayout()
    target_row.addWidget(QLabel("Export:"))
    vocal_target_combo = QComboBox()
    vocal_target_combo.addItems([
        "Instrumental only (Recommended)",
        "Vocals only",
        "Vocals + Instrumental",
    ])
    target_row.addWidget(vocal_target_combo)
    target_row.addStretch()
    vocal_layout.addLayout(target_row)

    format_row = QHBoxLayout()
    format_row.addWidget(QLabel("Output Format:"))
    vocal_output_format_combo = QComboBox()
    vocal_output_format_combo.addItems(["WAV", "FLAC", "MP3"])
    format_row.addWidget(vocal_output_format_combo)
    format_row.addStretch()
    vocal_layout.addLayout(format_row)

    vocal_fast_cb = QCheckBox("Fast mode (backend-specific speed tuning, lower quality)")
    vocal_layout.addWidget(vocal_fast_cb)

    recovery_row = QHBoxLayout()
    recovery_row.addWidget(QLabel("Demucs Music Recovery:"))
    vocal_recovery_combo = QComboBox()
    vocal_recovery_combo.addItems([
        "0% (Cleanest Vocal Removal)",
        "3% (Very Light)",
        "5% (Subtle)",
        "7% (Light)",
        "10% (Balanced)",
        "15% (Stronger)",
        "20% (More Music Under Vocals)",
        "30% (Maximum Music Recovery)",
    ])
    default_recovery_index = vocal_recovery_combo.findText("5% (Subtle)")
    if default_recovery_index >= 0:
        vocal_recovery_combo.setCurrentIndex(default_recovery_index)
    recovery_row.addWidget(vocal_recovery_combo)
    recovery_row.addStretch()
    vocal_layout.addLayout(recovery_row)

    recovery_mode_row = QHBoxLayout()
    recovery_mode_row.addWidget(QLabel("Recovery Mode:"))
    vocal_recovery_mode_combo = QComboBox()
    vocal_recovery_mode_combo.addItems([
        "Standard blend (legacy)",
        "Side-heavy recovery (less center vocal bleed)",
        "Center-aware recovery (guard center vocals)",
    ])
    recovery_mode_row.addWidget(vocal_recovery_mode_combo)
    recovery_mode_row.addStretch()
    vocal_layout.addLayout(recovery_mode_row)

    recovery_info = QLabel("Applies only to Demucs instrumental output. 3-7% is usually the sweet spot. Side-heavy and center-aware modes aim to keep accompaniment while reducing vocal bleed.")
    recovery_info.setStyleSheet("color: #888; font-size: 10px;")
    recovery_info.setWordWrap(True)
    vocal_layout.addWidget(recovery_info)

    vocal_sep_btn = QPushButton("Separate Vocals")
    vocal_sep_btn.setStyleSheet("background-color: #d35400; height: 35px; font-weight: bold; color: white;")
    vocal_layout.addWidget(vocal_sep_btn)

    vocal_status_label = QLabel("Ready. Load a file, then separate with Demucs or the faster UVR path.")
    vocal_status_label.setStyleSheet("color: #888; font-size: 10px;")
    vocal_layout.addWidget(vocal_status_label)
    vocal_layout.addStretch()

    tabs.addTab(vocal_tab, "🎤 Vocal Separator")

    # Tab 4: Join & Merge
    merge_tab = QWidget()
    merge_layout = QVBoxLayout(merge_tab)
    merge_layout.setContentsMargins(10, 10, 10, 10)

    merge_title = QLabel("<b>JOIN & MERGE</b>")
    merge_title.setFont(QFont("Segoe UI", 11, QFont.Bold))
    merge_layout.addWidget(merge_title)

    merge_info = QLabel(
        "Supports: video+audio merge (karaoke mux), audio+audio join, and video+video join. "
        "Pick two input files and export a combined output."
    )
    merge_info.setStyleSheet("color: #aaa; font-size: 11px;")
    merge_info.setWordWrap(True)
    merge_layout.addWidget(merge_info)

    merge_input_a_btn = QPushButton("Input A: Click to select")
    merge_input_a_btn.setStyleSheet("background-color: #3a3a3a; color: white; height: 36px; font-weight: bold;")
    merge_layout.addWidget(merge_input_a_btn)

    merge_input_a_label = QLabel("Input A: Not selected")
    merge_input_a_label.setStyleSheet("color: #bcbcbc; font-size: 11px; font-weight: bold;")
    merge_input_a_label.setWordWrap(True)
    merge_layout.addWidget(merge_input_a_label)

    merge_input_b_btn = QPushButton("Input B: Click to select")
    merge_input_b_btn.setStyleSheet("background-color: #3a3a3a; color: white; height: 36px; font-weight: bold;")
    merge_layout.addWidget(merge_input_b_btn)

    merge_input_b_label = QLabel("Input B: Not selected")
    merge_input_b_label.setStyleSheet("color: #bcbcbc; font-size: 11px; font-weight: bold;")
    merge_input_b_label.setWordWrap(True)
    merge_layout.addWidget(merge_input_b_label)

    merge_fmt_row = QHBoxLayout()
    merge_fmt_row.addWidget(QLabel("Output Format:"))
    merge_output_format_combo = QComboBox()
    merge_output_format_combo.addItems(["Auto (Recommended)", "MP4", "MKV", "WAV", "MP3"])
    merge_fmt_row.addWidget(merge_output_format_combo)
    merge_fmt_row.addStretch()
    merge_layout.addLayout(merge_fmt_row)

    merge_mode_row = QHBoxLayout()
    merge_mode_row.addWidget(QLabel("Join Behaviour:"))
    merge_mode_combo = QComboBox()
    merge_mode_combo.addItems([
        "Auto (Type-based Default)",
        "Append (A then B)",
        "Overlay (A + B at same time)",
    ])
    merge_mode_row.addWidget(merge_mode_combo)
    merge_mode_row.addStretch()
    merge_layout.addLayout(merge_mode_row)

    merge_mode_info = QLabel(
        "Auto default: same-type inputs (audio+audio, video+video) use Append. "
        "Mixed video+audio uses Overlay (karaoke mux)."
    )
    merge_mode_info.setStyleSheet("color: #888; font-size: 10px;")
    merge_mode_info.setWordWrap(True)
    merge_layout.addWidget(merge_mode_info)

    merge_offset_row = QHBoxLayout()
    merge_offset_row.addWidget(QLabel("Overlay Audio Start Offset (sec):"))
    merge_audio_offset_spin = QDoubleSpinBox()
    merge_audio_offset_spin.setDecimals(2)
    merge_audio_offset_spin.setSingleStep(0.10)
    merge_audio_offset_spin.setRange(0.0, 30.0)
    merge_audio_offset_spin.setValue(0.0)
    merge_audio_offset_spin.setSuffix(" s")
    merge_audio_offset_spin.setToolTip("Used only for video+audio Overlay mode. Delays merged audio start.")
    merge_offset_row.addWidget(merge_audio_offset_spin)
    merge_offset_row.addStretch()
    merge_layout.addLayout(merge_offset_row)

    merge_offset_info = QLabel(
        "Applies only to video+audio Overlay. Use this to delay song cue so lyrics appear first."
    )
    merge_offset_info.setStyleSheet("color: #888; font-size: 10px;")
    merge_offset_info.setWordWrap(True)
    merge_layout.addWidget(merge_offset_info)

    merge_execute_btn = QPushButton("Join / Merge Now")
    merge_execute_btn.setStyleSheet("background-color: #16a085; height: 35px; font-weight: bold; color: white;")
    merge_layout.addWidget(merge_execute_btn)

    merge_status_label = QLabel("Ready. Select two files to begin.")
    merge_status_label.setStyleSheet("color: #888; font-size: 10px;")
    merge_layout.addWidget(merge_status_label)
    merge_layout.addStretch()

    tabs.addTab(merge_tab, "🔗 Join & Merge")

    # Tab 5: Amplify & Export
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

    amp_note = QLabel("Examples: Amplification + 5.00x -> volume=5.0 with peak limiter, Reduce amplification - 5.00x -> volume=0.2. FFmpeg uses volume=<factor>.")
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

    # Keep Amplify controls alive for existing wiring, but hide tab from the UI.
    amp_tab_index = tabs.addTab(amp_tab, "🔊 Amplify & Export")
    tabs.setTabVisible(amp_tab_index, False)

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
        "vocal_model_combo": vocal_model_combo,
        "vocal_target_combo": vocal_target_combo,
        "vocal_output_format_combo": vocal_output_format_combo,
        "vocal_fast_cb": vocal_fast_cb,
        "vocal_recovery_combo": vocal_recovery_combo,
        "vocal_recovery_mode_combo": vocal_recovery_mode_combo,
        "vocal_offline_warning_label": vocal_offline_warning_label,
        "vocal_sep_btn": vocal_sep_btn,
        "vocal_status_label": vocal_status_label,
        "merge_input_a_btn": merge_input_a_btn,
        "merge_input_a_label": merge_input_a_label,
        "merge_input_b_btn": merge_input_b_btn,
        "merge_input_b_label": merge_input_b_label,
        "merge_output_format_combo": merge_output_format_combo,
        "merge_mode_combo": merge_mode_combo,
        "merge_audio_offset_spin": merge_audio_offset_spin,
        "merge_execute_btn": merge_execute_btn,
        "merge_status_label": merge_status_label,
        "amp_mode_group": amp_mode_group,
        "amp_factor_spin": amp_factor_spin,
        "amp_btn": amp_btn,
        "amp_source_label": amp_source_label,
        "amp_status_label": amp_status_label,
    }
