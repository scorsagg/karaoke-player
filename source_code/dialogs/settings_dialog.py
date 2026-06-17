from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QCheckBox, QGroupBox, QComboBox, QFrame, QFileDialog, QWidget, QListWidget, QStackedWidget
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
import json
import os


class SettingsDialog(QDialog):
    """Unified Schema-Driven Settings Dialog Window"""
    def __init__(self, parent=None, settings_manager=None):
        super().__init__(parent)
        self.manager = settings_manager
        self.temp_states = dict(self.manager.settings)
        
        self.setWindowTitle("⚙️ Settings Configuration")
        self.resize(750, 500)
        self.setModal(True)
        self.setStyleSheet("background-color: #1e1e1e; color: #ffffff;")
        
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        self.sidebar = QFrame()
        self.sidebar.setFixedWidth(200)
        self.sidebar.setStyleSheet("background-color: #252526; border-right: 1px solid #333;")
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(0, 15, 0, 0)
        
        self.settings_list = QListWidget()
        self.settings_list.setStyleSheet("""
            QListWidget { border: none; background: transparent; outline: 0; color: #ccc; }
            QListWidget::item { height: 45px; padding-left: 15px; }
            QListWidget::item:selected { background-color: #37373d; color: white; border-left: 4px solid #2ecc71; }
        """)
        sidebar_layout.addWidget(self.settings_list)
        sidebar_layout.addStretch()
        
        self.right_panel = QFrame()
        self.right_panel.setStyleSheet("background-color: #1e1e1e;")
        self.right_layout = QVBoxLayout(self.right_panel)
        self.right_layout.setContentsMargins(25, 25, 25, 25)
        
        self.settings_stack = QStackedWidget()
        self.right_layout.addWidget(self.settings_stack)
        
        self.display_fields = {}
        
        self.schema = {
            "📁 Paths & Storage": [
                {"key": "base_directory", "label": "Base Workspace Library:", "type": "directory", "desc": "Default repository lookup target root path."},
                {"key": "download_directory", "label": "Media Download Directory:", "type": "directory", "desc": "Location where incoming media stream files are downloaded."}
            ],
            "🛠️ System Binaries": [
                {"key": "ffmpeg_path", "label": "FFmpeg Core Binary Path:", "type": "file", "desc": "Target path targeting local executable 'ffmpeg'."},
                {"key": "ffprobe_path", "label": "FFprobe Context Parser Path:", "type": "file", "desc": "Target location targeting local executable 'ffprobe'."},
                {"key": "ytdlp_path", "label": "YT-DLP Extract Target Path:", "type": "file", "desc": "Target location pointing to your engine binary 'yt-dlp'."}
            ]
        }
        
        self.build_pages()
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.ok_btn = QPushButton("Save"); self.ok_btn.setFixedSize(90, 35)
        self.cancel_btn = QPushButton("Cancel"); self.cancel_btn.setFixedSize(90, 35)
        self.ok_btn.setStyleSheet("background-color: #0e639c; color: white; font-weight: bold; border-radius: 3px;")
        self.cancel_btn.setStyleSheet("background-color: #444; color: white; border-radius: 3px;")
        
        self.ok_btn.clicked.connect(self.accept_changes)
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.ok_btn)
        btn_layout.addWidget(self.cancel_btn)
        self.right_layout.addLayout(btn_layout)
        
        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(self.right_panel)
        
        self.settings_list.setCurrentRow(0)
        self.settings_list.currentRowChanged.connect(self.settings_stack.setCurrentIndex)

    def build_pages(self):
        for page_title, properties in self.schema.items():
            self.settings_list.addItem(page_title)
            page_widget = QWidget()
            page_layout = QVBoxLayout(page_widget)
            page_layout.setContentsMargins(0, 0, 0, 0)
            page_layout.setAlignment(Qt.AlignTop)
            
            title_lbl = QLabel(f"<b>{page_title.upper()}</b>")
            title_lbl.setFont(QFont("Segoe UI", 12, QFont.Bold))
            page_layout.addWidget(title_lbl)
            page_layout.addSpacing(15)
            
            for prop in properties:
                row_container = QWidget()
                row_layout = QVBoxLayout(row_container)
                row_layout.setContentsMargins(0, 5, 0, 10)
                
                label = QLabel(prop["label"])
                label.setFont(QFont("Segoe UI", 9, QFont.Bold))
                row_layout.addWidget(label)
                
                input_row = QHBoxLayout()
                edit_field = QLineEdit(str(self.temp_states.get(prop["key"], "")))
                edit_field.setStyleSheet("background-color: #2d2d2d; border: 1px solid #444; padding: 6px; color: #90ee90; border-radius: 3px;")
                self.display_fields[prop["key"]] = edit_field
                
                browse_btn = QPushButton("📁 Browse...")
                browse_btn.setFixedSize(90, 28)
                browse_btn.setStyleSheet("background-color: #3a3a3a; color: white;")
                browse_btn.clicked.connect(lambda checked=False, k=prop["key"], t=prop["type"]: self.handle_browse(k, t))
                
                input_row.addWidget(edit_field)
                input_row.addWidget(browse_btn)
                row_layout.addLayout(input_row)
                
                desc_lbl = QLabel(f"<i>{prop['desc']}</i>")
                desc_lbl.setStyleSheet("color: #777; font-size: 11px;")
                row_layout.addWidget(desc_lbl)
                
                page_layout.addWidget(row_container)
                
            page_layout.addStretch()
            self.settings_stack.addWidget(page_widget)

    def handle_browse(self, key, path_type):
        current_val = self.display_fields[key].text()
        if path_type == "directory":
            res = QFileDialog.getExistingDirectory(self, "Select Folder Location", current_val)
        else:
            res, _ = QFileDialog.getOpenFileName(self, "Locate Binary Executable", current_val, "Executables (*.exe *.*)")
        
        if res:
            normalized = os.path.normpath(res)
            self.temp_states[key] = normalized
            self.display_fields[key].setText(normalized)

    def accept_changes(self):
        for key in self.display_fields.keys():
            self.temp_states[key] = self.display_fields[key].text().strip()
        self.manager.settings.update(self.temp_states)
        self.manager.save_settings()
        self.accept()