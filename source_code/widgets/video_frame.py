from PySide6.QtWidgets import QFrame
from PySide6.QtCore import Qt, QPoint, QEvent


class VideoFrame(QFrame):
    """Custom QFrame that propagates drag/drop events up to the application controller."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self._resize_callback = None  # Optional callback called on resize

    def set_resize_callback(self, callback):
        """Register a callback to be called whenever this frame is resized."""
        self._resize_callback = callback

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._resize_callback:
            self._resize_callback()

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