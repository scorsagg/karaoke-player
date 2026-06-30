"""Legacy helpers retained for active shared widgets."""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QSpinBox, QLabel


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
        self.hour_spin.setMinimumWidth(55)
        self.hour_spin.setMaximumWidth(65)
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
        self.min_spin.setMinimumWidth(55)
        self.min_spin.setMaximumWidth(65)
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
        self.sec_spin.setMinimumWidth(55)
        self.sec_spin.setMaximumWidth(65)
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
