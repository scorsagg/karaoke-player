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


class AudioAnalyzerThread(QThread):
    """Thread to capture and analyze real-time audio output levels"""
    level_updated = Signal(float)  # Emit dB value
    clip_warning = Signal()  # Emit when level exceeds 90%
    
    def __init__(self):
        super().__init__()
        self.running = True
        self.is_playing = False
        self.audio_buffer = np.array([], dtype=np.float32)
        self.buffer_size = 4410 
        self.high_level_counter = 0 # Track how long it's been loud
        
    def set_playing(self, is_playing):
        """Set whether audio should be monitored"""
        self.is_playing = is_playing
        self.silence_count = 0
        
    def audio_callback(self, indata, frames, time, status):
        """Callback for audio stream - capture audio data"""
        if status or not self.is_playing:
            return
        try:
            # Get mono mix of audio
            if indata.shape[1] > 1:
                audio_data = np.mean(indata, axis=1)
            else:
                audio_data = indata[:, 0]
            
            # Add to buffer
            self.audio_buffer = np.append(self.audio_buffer, audio_data)
            
            # Keep buffer size manageable
            if len(self.audio_buffer) > self.buffer_size * 2:
                self.audio_buffer = self.audio_buffer[-self.buffer_size:]
        except Exception as e:
            print(f"Audio callback error: {e}")
    
    def run(self):
        with sd.InputStream(callback=self.audio_callback, channels=2, samplerate=44100, blocksize=2048):
            while self.running:
                if self.is_playing and len(self.audio_buffer) >= self.buffer_size // 2:
                    recent_audio = self.audio_buffer[-self.buffer_size:]
                    rms = np.sqrt(np.mean(recent_audio ** 2))
                    db_level = 20 * np.log10(rms + 1e-10)
                    
                    # Clamp
                    db_level = max(-80.0, min(0.0, db_level))
                    self.level_updated.emit(db_level)
                
                self.msleep(100) # Throttled to 10Hz for smoother UI updates
    
    def stop(self):
        """Stop the audio analyzer"""
        self.running = False
        self.wait(500)

