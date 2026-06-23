"""Sidebar UI component - navigation and settings"""

from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QPushButton, QListWidget, QLabel
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt


def create_sidebar(parent):
    """Create and return the sidebar frame with navigation and settings
    
    Args:
        parent: Parent widget (typically the main window)
    
    Returns:
        QFrame: Configured sidebar widget
    """
    sidebar = QFrame()
    sidebar.setFixedWidth(200)
    sidebar.setStyleSheet("background-color: #252526; border-right: 1px solid #333;")
    side_layout = QVBoxLayout(sidebar)
    side_layout.setContentsMargins(0, 0, 0, 0)

    logo = QLabel("KARAOKE STUDIO PRO")
    logo.setFont(QFont("Segoe UI", 12, QFont.Bold))
    logo.setContentsMargins(15, 20, 10, 20)
    side_layout.addWidget(logo)

    nav_list = QListWidget()
    nav_list.setFixedHeight(110)
    nav_list.setStyleSheet("""
        QListWidget { border: none; background: transparent; outline: 0; color: #ccc; }
        QListWidget::item { height: 50px; padding-left: 15px; }
        QListWidget::item:selected { background-color: #37373d; color: white; border-left: 4px solid #2ecc71; }
    """)
    nav_list.addItems(["📥 Downloader", "🎬 Pitch & Speed"])
    side_layout.addWidget(nav_list)

    extra_tools_toggle_btn = QPushButton("▶ 🛠 Extra Tools")
    extra_tools_toggle_btn.setStyleSheet("background-color: #37373d; color: #ccc; padding: 10px; border: 1px solid #444; border-radius: 3px; text-align: left;")
    side_layout.addWidget(extra_tools_toggle_btn)

    extra_tools_container = QFrame()
    extra_tools_container.setVisible(False)
    extra_tools_container_layout = QVBoxLayout(extra_tools_container)
    extra_tools_container_layout.setContentsMargins(0, 5, 0, 0)

    video_tools_btn = QPushButton("🎬 Video Tools")
    video_tools_btn.setStyleSheet("background-color: #2d2d2d; color: #aaa; padding: 8px 15px; border: none; text-align: left; margin-left: 15px; margin-right: 10px;")
    extra_tools_container_layout.addWidget(video_tools_btn)

    audio_tools_btn = QPushButton("🎵 Audio Tools")
    audio_tools_btn.setStyleSheet("background-color: #2d2d2d; color: #aaa; padding: 8px 15px; border: none; text-align: left; margin-left: 15px; margin-right: 10px;")
    extra_tools_container_layout.addWidget(audio_tools_btn)
    side_layout.addWidget(extra_tools_container)

    line = QFrame()
    line.setFrameShape(QFrame.HLine)
    line.setStyleSheet("color: #333; margin: 5px 15px;")
    side_layout.addWidget(line)

    history_toggle_btn = QPushButton("▶ History")
    history_toggle_btn.setStyleSheet("background-color: #37373d; color: #ccc; padding: 10px; border: 1px solid #444; border-radius: 3px; text-align: left;")
    side_layout.addWidget(history_toggle_btn)

    history_container = QFrame()
    history_container.setVisible(False)
    history_container_layout = QVBoxLayout(history_container)
    history_container_layout.setContentsMargins(0, 0, 0, 0)

    hist_header = QHBoxLayout()
    history_label = QLabel("RECENT FILES")
    history_label.setFont(QFont("Segoe UI", 8, QFont.Bold))
    history_label.setStyleSheet("color: #666; margin-left: 15px;")

    clear_hist_btn = QPushButton("Clear")
    clear_hist_btn.setFixedSize(45, 18)
    clear_hist_btn.setStyleSheet("font-size: 9px; background-color: #333; color: #888; border-radius: 2px;")

    hist_header.addWidget(history_label)
    hist_header.addStretch()
    hist_header.addWidget(clear_hist_btn)
    hist_header.addSpacing(10)
    history_container_layout.addLayout(hist_header)

    history_list = QListWidget()
    history_list.setStyleSheet("""
        QListWidget { border: none; background: transparent; outline: 0; color: #aaa; font-size: 10px; }
        QListWidget::item { height: 30px; padding-left: 15px; border-bottom: 1px solid #2d2d2d; }
        QListWidget::item:hover { background-color: #37373d; color: white; }
    """)
    history_container_layout.addWidget(history_list)
    side_layout.addWidget(history_container)

    side_layout.addStretch(1)

    settings_btn = QPushButton("⚙️ Settings")
    settings_btn.setStyleSheet("background-color: #37373d; color: #ccc; padding: 10px; border: 1px solid #444; border-radius: 3px;")
    side_layout.addWidget(settings_btn)

    status_label = QLabel("Status: Ready")
    status_label.setStyleSheet("color: #ffffff; padding: 5px 10px; font-size: 12px; font-weight: bold; border-top: 1px solid #333;")
    status_label.setWordWrap(True)
    side_layout.addWidget(status_label)

    # Return all sidebar components as a dict for easy access in main.py
    return {
        "sidebar": sidebar,
        "nav_list": nav_list,
        "extra_tools_toggle_btn": extra_tools_toggle_btn,
        "extra_tools_container": extra_tools_container,
        "video_tools_btn": video_tools_btn,
        "audio_tools_btn": audio_tools_btn,
        "history_toggle_btn": history_toggle_btn,
        "history_container": history_container,
        "clear_hist_btn": clear_hist_btn,
        "history_list": history_list,
        "settings_btn": settings_btn,
        "status_label": status_label
    }
