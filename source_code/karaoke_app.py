from PySide6.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, QFileDialog, 
    QLabel, QLineEdit, QHBoxLayout, QFrame, QScrollArea, 
    QMessageBox, QDoubleSpinBox, QProgressBar, QSlider, QStackedWidget, 
    QListWidget, QGridLayout, QSplashScreen, QDialog
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer, QRect, QEvent, QPoint
from PySide6.QtGui import QFont, QPixmap, QColor, QCursor, QPainter, QPen
import numpy as np
import sounddevice as sd
from collections import deque
from .workers.process_thread import ProcessThread
from .services.download_service import DownloadService
from .services.player_service import PlayerService
class KaraokeApp(QWidget):
    def __init__(self):
        super().__init__()
        self.video_path = ""
        self.widen_tab_video_path = ""  
        self.active_tasks = {}
        self.is_video_fullscreen = False
        self.export_splash = None
        self.init_settings_manager()        
        self.setWindowTitle("Karaoke Studio Pro v2.0")
        self.resize(1150, 850)
        self.setStyleSheet("background-color: #1e1e1e; color: #ffffff; font-family: 'Segoe UI';")

        self.setup_ui()
        self.nav_list.setCurrentRow(0)
        
        self.timer = QTimer()
        self.timer.setInterval(200)
        self.timer.timeout.connect(self.update_ui)
        self.timer.start()
        self.is_user_sliding = False

        # Fullscreen Hover Controls Logic Setup
        self.hide_controls_timer = QTimer()
        self.hide_controls_timer.setInterval(2500)  # Auto-hide after 2.5 seconds
        self.hide_controls_timer.timeout.connect(self.hide_fullscreen_controls)

def create_process_thread(self, cmd, duration=0):
        from .workers.process_thread import ProcessThread # Local import to avoid circular dependency if needed
        return ProcessThread(cmd, duration)