"""Playback controls UI component"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QSlider,
    QStyle, QStyleOptionSlider,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPainter
from source_code.utils.audio_activity import ACTIVITY_THRESHOLD_DBFS
from source_code.widgets.audio_meter import AudioLevelMeter


class AudioActivitySlider(QSlider):
    """Horizontal seek slider with painted, normalized audio-activity ranges."""

    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        self._activity_ranges = []

    def set_activity_ranges(self, ranges):
        normalized = []
        for start, end in ranges:
            start = max(0.0, min(float(start), 1.0))
            end = max(start, min(float(end), 1.0))
            if end > start:
                normalized.append((start, end))
        self._activity_ranges = normalized
        self.update()

    def activity_ranges(self):
        return list(self._activity_ranges)

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self._activity_ranges:
            return

        option = QStyleOptionSlider()
        self.initStyleOption(option)
        groove = self.style().subControlRect(
            QStyle.ComplexControl.CC_Slider,
            option,
            QStyle.SubControl.SC_SliderGroove,
            self,
        )
        handle = self.style().subControlRect(
            QStyle.ComplexControl.CC_Slider,
            option,
            QStyle.SubControl.SC_SliderHandle,
            self,
        )
        left = groove.left() + handle.width() / 2
        right = groove.right() - handle.width() / 2
        if right <= left:
            return

        painter = QPainter(self)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(72, 175, 105, 190))
        bar_height = max(3, min(6, groove.height()))
        y = groove.center().y() - bar_height / 2
        for start, end in self._activity_ranges:
            x1 = round(left + (right - left) * start)
            x2 = round(left + (right - left) * end)
            if x1 < handle.left():
                painter.drawRoundedRect(
                    x1,
                    round(y),
                    max(0, min(x2, handle.left()) - x1),
                    bar_height,
                    2,
                    2,
                )
            if x2 > handle.right():
                segment_start = max(x1, handle.right() + 1)
                painter.drawRoundedRect(
                    segment_start,
                    round(y),
                    max(0, x2 - segment_start),
                    bar_height,
                    2,
                    2,
                )
        painter.end()


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
    seek_slider = AudioActivitySlider(Qt.Horizontal)
    seek_slider.setRange(0, 1000)
    seek_slider.setMinimumHeight(24)
    seek_slider.setStyleSheet("""
        QSlider::groove:horizontal {
            height: 8px;
            background: #555555;
            border: 1px solid #777777;
            border-radius: 4px;
        }
        QSlider::sub-page:horizontal {
            background: #0e639c;
            border-radius: 4px;
        }
        QSlider::handle:horizontal {
            width: 16px;
            margin: -6px 0;
            background: #ffffff;
            border: 2px solid #0e639c;
            border-radius: 9px;
        }
    """)
    duration_label = QLabel("00:00")
    activity_threshold_label = QLabel(f"Activity: >= {ACTIVITY_THRESHOLD_DBFS} dBFS")
    activity_threshold_label.setStyleSheet("color: #aaa; font-size: 10px;")
    activity_threshold_label.setToolTip(
        "Highlights 100 ms source-file RMS windows at or above the dBFS threshold. "
        "This is not the live playback meter's room-level estimate."
    )
    seek_row.addWidget(time_label)
    seek_row.addWidget(seek_slider)
    seek_row.addWidget(duration_label)
    seek_row.addWidget(activity_threshold_label)

    # Control row
    ctrl_row = QHBoxLayout()
    back_btn = QPushButton("⏪ -10s")
    play_btn = QPushButton("▶ Play")
    pause_btn = QPushButton("⏸ Pause")
    stop_btn = QPushButton("⏹ Stop")
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

    for w in [back_btn, play_btn, pause_btn, stop_btn, fwd_btn]:
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
        "activity_threshold_label": activity_threshold_label,
        "back_btn": back_btn,
        "play_btn": play_btn,
        "pause_btn": pause_btn,
        "stop_btn": stop_btn,
        "fwd_btn": fwd_btn,
        "mute_btn": mute_btn,
        "vol_slider": vol_slider,
        "vol_label": vol_label,
        "audio_level_meter": audio_level_meter,
        "audio_level_label": audio_level_label,
        "fullscreen_btn": fullscreen_btn
    }
