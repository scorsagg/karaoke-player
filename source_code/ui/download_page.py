"""Download page UI component"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QGridLayout, QPushButton, QLabel, QLineEdit, QFrame
from PySide6.QtCore import Qt


def create_download_page():
    """Create and return the download page UI
    
    Returns:
        dict: Dictionary containing page widget and control references
    """
    page = QWidget()
    layout = QVBoxLayout(page)
    layout.setContentsMargins(10, 5, 10, 5)
    grid = QGridLayout()

    load_btn = QPushButton("📂 Open File...")
    load_btn.setFixedSize(110, 30)
    grid.addWidget(load_btn, 1, 0)

    sep = QFrame()
    sep.setFrameShape(QFrame.VLine)
    sep.setStyleSheet("color: #3a3a3a;")
    grid.addWidget(sep, 1, 1)

    grid.addWidget(QLabel("<b>YouTube / Stream Target URL:</b>"), 0, 2)
    url_input = QLineEdit()
    url_input.setPlaceholderText("Paste network audio/video stream links here...")
    url_input.setStyleSheet("background-color: #333; border: 1px solid #555; padding: 5px; color: white;")
    url_input.setFixedSize(700, 30)
    grid.addWidget(url_input, 1, 2)

    dl_btn = QPushButton("Download and Load")
    dl_btn.setFixedSize(140, 30)
    dl_btn.setStyleSheet("background-color: #2ecc71; font-weight: bold; color: white;")
    grid.addWidget(dl_btn, 1, 3)

    layout.addLayout(grid)
    layout.addStretch()

    return {
        "page": page,
        "load_btn": load_btn,
        "url_input": url_input,
        "dl_btn": dl_btn
    }
