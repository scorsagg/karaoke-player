from PySide6.QtWidgets import QFrame
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QEvent


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