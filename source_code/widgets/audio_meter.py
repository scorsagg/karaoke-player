from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QColor, QFont, QPen


class AudioLevelMeter(QWidget):
    """Custom widget to display real-time audio output level in approximate SPL"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.db_level = -80.0
        self.level_percent = 0.0  # 0-100%
        self.measurement_mode = "dB Output (dBFS)"  # or "SPL Estimate (Room)"
        self.setFixedHeight(30)
        self.setMinimumWidth(150)
        self.setMaximumWidth(200)
        
    def set_level(self, db_value):
        # Smooth the change: 80% old value, 20% new value
        target_db = max(-80.0, min(0.0, db_value))
        if not hasattr(self, 'smoothed_db'): self.smoothed_db = -80.0
        self.smoothed_db = (self.smoothed_db * 0.8) + (target_db * 0.2)
        
        self.db_level = self.smoothed_db
        self.level_percent = ((self.db_level + 80.0) / 80.0) * 100.0
        self.update()

    def get_approximate_spl(self):
        """Convert dBFS to approximate SPL (Sound Pressure Level in dB)"""
        # Rough approximation: SPL ≈ 60 + (level_percent * 0.3)
        # This gives: 0% → 60 SPL, 80% → 84 SPL, 100% → 90 SPL (max safe karaoke)
        return 60 + (self.level_percent * 0.3)
    
    def set_measurement_mode(self, mode):
        """Set whether to display dB output or SPL estimate. Mode: 'dB Output (dBFS)' or 'SPL Estimate (Room)'"""
        self.measurement_mode = mode
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Background
        painter.fillRect(self.rect(), QColor("#2d2d2d"))
        
        # Border
        painter.setPen(QPen(QColor("#444"), 1))
        painter.drawRect(0, 0, self.width() - 1, self.height() - 1)
        
        # Draw meter
        meter_width = self.width() - 6
        meter_height = self.height() - 6
        meter_x = 3
        meter_y = 3
        
        # Fill based on actual dB level
        fill_ratio = max(0, self.level_percent / 100.0)
        fill_width = max(0, meter_width * fill_ratio)
        
        # Draw meter background
        painter.fillRect(meter_x, meter_y, meter_width, meter_height, QColor("#1a1a1a"))
        
        # Draw filled portion with color based on level
        if fill_width > 0:
            if self.level_percent < 50:
                color = QColor("#2ecc71")  # Green for low levels
            elif self.level_percent < 85:
                color = QColor("#f39c12")  # Orange for medium levels
            else:
                color = QColor("#e74c3c")  # Red for high levels (clipping risk)
                
            painter.fillRect(meter_x, meter_y, fill_width, meter_height, color)
        
        # Draw threshold lines at 50% and 85%
        painter.setPen(QPen(QColor("#666"), 1))
        line_50_x = meter_x + (meter_width * 0.5)
        line_85_x = meter_x + (meter_width * 0.85)
        painter.drawLine(int(line_50_x), meter_y - 2, int(line_50_x), meter_y + meter_height + 2)
        painter.drawLine(int(line_85_x), meter_y - 2, int(line_85_x), meter_y + meter_height + 2)
        
        # Draw text - always show SPL value, but label varies by mode
        painter.setPen(QColor("#ffffff"))
        painter.setFont(QFont("Segoe UI", 7, QFont.Bold))
        
        spl = self.get_approximate_spl()
        if self.measurement_mode == "dB Output (dBFS)":
            text = f"{spl:.0f} dB ({self.level_percent:.0f}%)"
        else:  # SPL Estimate (Room)
            text = f"{spl:.0f} dB SPL ({self.level_percent:.0f}%)"
        
        painter.drawText(self.rect(), Qt.AlignCenter, text)