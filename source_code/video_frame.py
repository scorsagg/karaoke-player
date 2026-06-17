import sys, os, vlc, subprocess, re, time, json
from pathlib import Path
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


class VideoFrame(QFrame):
    """Custom QFrame that propagates drag/drop events up to the application controller."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
    
    def dragEnterEvent(self, event):
        parent = self.parent()
        while parent and parent.parent(): parent = parent.parent()
        if parent and parent != self and hasattr(parent, 'dragEnterEvent'):
            parent.dragEnterEvent(event)
        else:
            event.ignore()
    
    def dropEvent(self, event):
        parent = self.parent()
        while parent and parent.parent(): parent = parent.parent()
        if parent and parent != self and hasattr(parent, 'dropEvent'):
            parent.dropEvent(event)
        else:
            event.ignore()

