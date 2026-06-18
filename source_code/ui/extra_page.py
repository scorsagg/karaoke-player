"""Extra tools page UI component - video aspect ratio widening tool"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QGridLayout, QPushButton, QLabel, QLineEdit, QFrame
from PySide6.QtGui import QFont


def create_extra_page():
    """Create and return the extra tools page UI (aspect ratio widening tool)
    
    Returns:
        dict: Dictionary containing page widget and control references
    """
    page = QWidget()
    layout = QVBoxLayout(page)
    layout.setContentsMargins(10, 5, 10, 5)

    title = QLabel("<b>📐 ASPECT-RATIO LAYOUT PAD ENGINE</b>")
    title.setFont(QFont("Segoe UI", 11, QFont.Bold))
    layout.addWidget(title)

    grid = QGridLayout()
    
    widen_file_btn = QPushButton("📂 Open Widen File...")
    widen_file_btn.setFixedSize(140, 30)
    grid.addWidget(widen_file_btn, 1, 0)

    sep = QFrame()
    sep.setFrameShape(QFrame.VLine)
    sep.setStyleSheet("color: #3a3a3a;")
    grid.addWidget(sep, 1, 1)

    grid.addWidget(QLabel("<b>YouTube / Stream Link:</b>"), 0, 2)
    
    widen_url_input = QLineEdit()
    widen_url_input.setPlaceholderText("Paste target URL link here to download directly to Widen context...")
    widen_url_input.setStyleSheet("background-color: #333; border: 1px solid #555; padding: 5px; color: white;")
    widen_url_input.setFixedSize(540, 30)
    grid.addWidget(widen_url_input, 1, 2)

    widen_dl_btn = QPushButton("Download & Queue")
    widen_dl_btn.setFixedSize(140, 30)
    widen_dl_btn.setStyleSheet("background-color: #2ecc71; font-weight: bold; color: white;")
    grid.addWidget(widen_dl_btn, 1, 3)
    
    layout.addLayout(grid)

    widen_file_status_label = QLabel("Queued File for Widening: None (Will fallback to currently loaded player asset if blank)")
    widen_file_status_label.setStyleSheet("color: #e67e22; font-style: italic; padding: 5px 0px;")
    layout.addWidget(widen_file_status_label)
    layout.addSpacing(10)

    widen_exec_btn = QPushButton("Scale Active Video to Wide 16:9 Canvas")
    widen_exec_btn.setStyleSheet("background-color: #e67e22; height: 45px; font-weight: bold; font-size: 13px; color: white; border-radius: 4px;")
    layout.addWidget(widen_exec_btn)

    layout.addStretch()

    return {
        "page": page,
        "widen_file_btn": widen_file_btn,
        "widen_url_input": widen_url_input,
        "widen_dl_btn": widen_dl_btn,
        "widen_file_status_label": widen_file_status_label,
        "widen_exec_btn": widen_exec_btn
    }
