"""Pitch and speed control page UI component"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                               QLabel, QDoubleSpinBox, QFrame, QSizePolicy)
from PySide6.QtCore import Qt


def create_pitch_page():
    """Create and return the pitch and speed control page UI
    
    Returns:
        dict: Dictionary containing page widget and control references
    """
    page = QWidget()
    layout = QVBoxLayout(page)

    # ── LIVE PITCH PANEL ─────────────────────────────────────────────────────
    pitch_display_frame = QFrame()
    pitch_display_frame.setStyleSheet("""
        QFrame {
            background-color: #151515;
            border: 1px solid #2f2f2f;
            border-radius: 10px;
        }
    """)
    pitch_display_outer = QVBoxLayout(pitch_display_frame)
    pitch_display_outer.setContentsMargins(14, 10, 14, 10)

    pitch_header = QLabel("<b>SONG PITCH (LIVE)</b>")
    pitch_header.setStyleSheet("color: #ddd; font-size: 11px; letter-spacing: 1px;")
    pitch_display_outer.addWidget(pitch_header)

    # Two-column row: Sa/Pa/Sa panel (left) + technical details (right)
    cols = QHBoxLayout()
    cols.setSpacing(16)

    # ── LEFT: Singer's key panel ──────────────────────────────────────────────
    key_frame = QFrame()
    key_frame.setStyleSheet("""
        QFrame {
            background-color: #0d1f0d;
            border: 1px solid #1a4a1a;
            border-radius: 8px;
        }
    """)
    key_frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    key_layout = QVBoxLayout(key_frame)
    key_layout.setContentsMargins(12, 8, 12, 8)
    key_layout.setSpacing(2)

    key_header = QLabel("SONG KEY")
    key_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
    key_header.setStyleSheet("color: #2ecc71; font-size: 9px; letter-spacing: 2px; font-weight: bold;")
    key_layout.addWidget(key_header)

    def _make_key_row(syllable_text, color):
        row = QHBoxLayout()
        syllable = QLabel(syllable_text)
        syllable.setFixedWidth(60)
        syllable.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        syllable.setStyleSheet(f"color: #888; font-size: 13px;")
        note_lbl = QLabel("—")
        note_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        note_lbl.setStyleSheet(f"color: {color}; font-size: 36px; font-weight: bold; padding-left: 8px;")
        row.addWidget(syllable)
        row.addWidget(note_lbl)
        row.addStretch()
        key_layout.addLayout(row)
        return note_lbl

    sa_label   = _make_key_row("Sa  →", "#2ecc71")
    pa_label   = _make_key_row("Pa  →", "#3498db")
    hsa_label  = _make_key_row("Sa' →", "#9b59b6")

    key_status_label = QLabel("Detecting song key…")
    key_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    key_status_label.setStyleSheet("color: #e67e22; font-size: 9px; font-style: italic;")
    key_layout.addWidget(key_status_label)

    cols.addWidget(key_frame, stretch=3)

    # ── RIGHT: Technical details panel ───────────────────────────────────────
    tech_frame = QFrame()
    tech_frame.setStyleSheet("""
        QFrame {
            background-color: #1a1a1a;
            border: 1px solid #2f2f2f;
            border-radius: 8px;
        }
    """)
    tech_frame.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
    tech_layout = QVBoxLayout(tech_frame)
    tech_layout.setContentsMargins(10, 8, 10, 8)
    tech_layout.setSpacing(4)

    tech_header = QLabel("LIVE ANALYSIS")
    tech_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
    tech_header.setStyleSheet("color: #888; font-size: 9px; letter-spacing: 2px;")
    tech_layout.addWidget(tech_header)

    pitch_note_label = QLabel("—")
    pitch_note_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    pitch_note_label.setStyleSheet("color: #aaa; font-size: 28px; font-weight: bold; padding: 2px 0;")
    tech_layout.addWidget(pitch_note_label)

    pitch_frequency_label = QLabel("Waiting for audio…")
    pitch_frequency_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    pitch_frequency_label.setStyleSheet("color: #666; font-size: 9px;")
    pitch_frequency_label.setWordWrap(True)
    tech_layout.addWidget(pitch_frequency_label)

    pitch_lock_label = QLabel("Lock: searching")
    pitch_lock_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    pitch_lock_label.setStyleSheet("color: #e67e22; font-size: 9px; font-weight: bold;")
    tech_layout.addWidget(pitch_lock_label)

    pitch_source_label = QLabel("Playback loopback")
    pitch_source_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    pitch_source_label.setStyleSheet("color: #444; font-size: 8px; font-style: italic;")
    tech_layout.addWidget(pitch_source_label)

    cols.addWidget(tech_frame, stretch=2)

    pitch_display_outer.addLayout(cols)
    # Keep analyzer widgets instantiated for signal/update compatibility, but hide the panel in UI.
    pitch_display_frame.setVisible(False)
    layout.addWidget(pitch_display_frame)
    layout.addSpacing(8)
    
    # Pitch row
    p_row = QHBoxLayout()
    p_row.addWidget(QLabel("Pitch Shifter Matrix Shift:"))
    
    pitch_minus = QPushButton("-")
    pitch_minus.setFixedWidth(30)
    
    pitch_input = QDoubleSpinBox()
    pitch_input.setRange(-12.0, 12.0)
    pitch_input.setValue(0.0)
    pitch_input.setSuffix(" semitones")
    pitch_input.setSingleStep(0.5)
    
    pitch_plus = QPushButton("+")
    pitch_plus.setFixedWidth(30)
    
    pitch_reset = QPushButton("↺")
    pitch_reset.setFixedWidth(40)

    pitch_minus.clicked.connect(lambda: pitch_input.setValue(pitch_input.value() - 1.0))
    pitch_plus.clicked.connect(lambda: pitch_input.setValue(pitch_input.value() + 1.0))
    pitch_reset.clicked.connect(lambda: pitch_input.setValue(0.0))

    for w in [pitch_minus, pitch_input, pitch_plus, pitch_reset]:
        p_row.addWidget(w)
    p_row.addStretch()

    # Speed row
    s_row = QHBoxLayout()
    s_row.addWidget(QLabel("Playback Velocity Frequency:"))
    
    speed_minus = QPushButton("-")
    speed_minus.setFixedWidth(30)
    
    speed_input = QDoubleSpinBox()
    speed_input.setRange(0.5, 2.0)
    speed_input.setValue(1.0)
    speed_input.setSuffix("x Timeline")
    speed_input.setSingleStep(0.01)
    
    speed_plus = QPushButton("+")
    speed_plus.setFixedWidth(30)
    
    speed_reset = QPushButton("↺")
    speed_reset.setFixedWidth(40)

    speed_minus.clicked.connect(lambda: speed_input.setValue(round(speed_input.value() - 0.05, 2)))
    speed_plus.clicked.connect(lambda: speed_input.setValue(round(speed_input.value() + 0.05, 2)))
    speed_reset.clicked.connect(lambda: speed_input.setValue(1.0))

    for w in [speed_minus, speed_input, speed_plus, speed_reset]:
        s_row.addWidget(w)
    s_row.addStretch()

    export_btn = QPushButton("Export Unified Master Render File")
    export_btn.setStyleSheet("background-color: #0e639c; height: 45px; font-weight: bold; color: white;")

    layout.addLayout(p_row)
    layout.addLayout(s_row)
    layout.addWidget(export_btn)
    layout.addStretch()

    return {
        "page": page,
        "pitch_note_label": pitch_note_label,
        "pitch_frequency_label": pitch_frequency_label,
        "pitch_lock_label": pitch_lock_label,
        "pitch_source_label": pitch_source_label,
        "sa_label": sa_label,
        "pa_label": pa_label,
        "hsa_label": hsa_label,
        "key_status_label": key_status_label,
        "pitch_minus": pitch_minus,
        "pitch_input": pitch_input,
        "pitch_plus": pitch_plus,
        "pitch_reset": pitch_reset,
        "speed_minus": speed_minus,
        "speed_input": speed_input,
        "speed_plus": speed_plus,
        "speed_reset": speed_reset,
        "export_btn": export_btn
    }
