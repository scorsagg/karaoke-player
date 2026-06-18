"""Pitch and speed control page UI component"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QDoubleSpinBox


def create_pitch_page():
    """Create and return the pitch and speed control page UI
    
    Returns:
        dict: Dictionary containing page widget and control references
    """
    page = QWidget()
    layout = QVBoxLayout(page)
    
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
