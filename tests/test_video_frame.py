"""Unit tests for source_code/widgets/video_frame.py"""

import pytest
from PySide6.QtCore import QMimeData, QPoint, QSize, Qt
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QResizeEvent
from PySide6.QtWidgets import QWidget

from source_code.widgets.video_frame import VideoFrame


def _drag_enter_event():
    mime = QMimeData()
    mime.setText("/media/song.mp4")
    return QDragEnterEvent(QPoint(1, 1), Qt.CopyAction, mime, Qt.LeftButton, Qt.NoModifier)


def _drop_event():
    mime = QMimeData()
    mime.setText("/media/song.mp4")
    return QDropEvent(QPoint(1, 1), Qt.CopyAction, mime, Qt.LeftButton, Qt.NoModifier)


class RecordingWindow(QWidget):
    """Top-level window that records forwarded drag/drop events."""

    def __init__(self):
        super().__init__()
        self.drag_enters = 0
        self.drops = 0

    def dragEnterEvent(self, event):
        self.drag_enters += 1
        event.accept()

    def dropEvent(self, event):
        self.drops += 1
        event.accept()


@pytest.fixture
def frame(qapp):
    widget = VideoFrame()
    yield widget
    widget.deleteLater()


class TestConstruction:
    def test_tracks_mouse_and_has_no_resize_callback(self, frame):
        assert frame.hasMouseTracking() is True
        assert frame._resize_callback is None


class TestResizeCallback:
    def test_callback_runs_on_resize(self, frame):
        calls = []
        frame.set_resize_callback(lambda: calls.append(1))

        frame.resizeEvent(QResizeEvent(QSize(320, 240), QSize(100, 100)))

        assert calls == [1]

    def test_resize_without_callback_is_safe(self, frame):
        frame.resizeEvent(QResizeEvent(QSize(320, 240), QSize(100, 100)))


class TestDragAndDropForwarding:
    def test_drag_enter_is_forwarded_to_top_level_window(self, qapp):
        window = RecordingWindow()
        middle = QWidget(window)
        frame = VideoFrame(middle)

        frame.dragEnterEvent(_drag_enter_event())

        assert window.drag_enters == 1

    def test_drop_is_forwarded_to_top_level_window(self, qapp):
        window = RecordingWindow()
        middle = QWidget(window)
        frame = VideoFrame(middle)

        frame.dropEvent(_drop_event())

        assert window.drops == 1

    def test_parentless_frame_ignores_drag_enter(self, frame):
        event = _drag_enter_event()
        event.accept()

        frame.dragEnterEvent(event)

        assert event.isAccepted() is False

    def test_parentless_frame_ignores_drop(self, frame):
        event = _drop_event()
        event.accept()

        frame.dropEvent(event)

        assert event.isAccepted() is False
