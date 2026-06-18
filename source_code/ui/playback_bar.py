"""Playback controls UI component"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QSlider
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from source_code.widgets.audio_meter import AudioLevelMeter


def create_playback_bar(settings):
    """Create and return the playback control bar
    
    Args:
        settings: Settings dict to get audio display mode
    
    Returns:
        dict: Dictionary containing all playback control widgets
    """
    container = QVBoxLayout()
    container.setContentsMargins(15, 5, 15, 5)
    
    # Seek row
    seek_row = QHBoxLayout()
    time_label = QLabel("00:00")
    seek_slider = QSlider(Qt.Horizontal)
    seek_slider.setRange(0, 1000)
    duration_label = QLabel("00:00")
    seek_row.addWidget(time_label)
    seek_row.addWidget(seek_slider)
    seek_row.addWidget(duration_label)

    # Control row
    ctrl_row = QHBoxLayout()
    back_btn = QPushButton("⏪ -10s")
    play_btn = QPushButton("▶ Play")
    pause_btn = QPushButton("⏸ Pause")
    fwd_btn = QPushButton("+10s ⏩")

    mute_btn = QPushButton("🔊")
    mute_btn.setFixedWidth(35)
    vol_slider = QSlider(Qt.Horizontal)
    vol_slider.setRange(0, 100)
    vol_slider.setValue(80)
    vol_slider.setFixedWidth(120)
    vol_label = QLabel("80%")
    vol_label.setFixedWidth(40)

    # Add audio level meter
    audio_level_meter = AudioLevelMeter()
    audio_level_meter.set_level(-80.0)  # Initialize to silent
    audio_level_meter.set_measurement_mode(settings.get("measurement_mode", "dB Output (dBFS)"))
    audio_level_label = QLabel("Audio:")
    audio_level_label.setStyleSheet("color: #ccc; font-size: 10px;")

    for w in [back_btn, play_btn, pause_btn, fwd_btn]:
        ctrl_row.addWidget(w)
    ctrl_row.addStretch()

    # Add audio level meter to control row
    ctrl_row.addWidget(audio_level_label)
    ctrl_row.addWidget(audio_level_meter)
    ctrl_row.addSpacing(10)

    fullscreen_btn = QPushButton("🖥 Full Video")
    fullscreen_btn.setMinimumWidth(115)
    fullscreen_btn.setToolTip("Enter fullscreen mode (controls auto-hide)")
    ctrl_row.addWidget(fullscreen_btn)

    for w in [mute_btn, vol_slider, vol_label]:
        ctrl_row.addWidget(w)

    container.addLayout(seek_row)
    container.addSpacing(5)
    container.addLayout(ctrl_row)

    playback_widget = QWidget()
    playback_widget.setLayout(container)
    playback_widget.setFixedHeight(95)

    return {
        "playback_widget": playback_widget,
        "time_label": time_label,
        "seek_slider": seek_slider,
        "duration_label": duration_label,
        "back_btn": back_btn,
        "play_btn": play_btn,
        "pause_btn": pause_btn,
        "fwd_btn": fwd_btn,
        "mute_btn": mute_btn,
        "vol_slider": vol_slider,
        "vol_label": vol_label,
        "audio_level_meter": audio_level_meter,
        "audio_level_label": audio_level_label,
        "fullscreen_btn": fullscreen_btn
    }
