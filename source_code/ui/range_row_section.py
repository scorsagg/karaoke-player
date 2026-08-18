"""Reusable Start/End range-row section and tab styling shared by the studio pages."""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton

from source_code.ui.extra_page import TimePickerWidget

STUDIO_TAB_STYLESHEET = """
    QTabWidget::pane { border: 1px solid #3a3a3a; }
    QTabBar::tab {
        background-color: #2a2a2a;
        color: #fff;
        padding: 8px 20px;
        border: 1px solid #3a3a3a;
        margin-right: 1px;
    }
    QTabBar::tab:hover { background-color: #145a86; }
    QTabBar::tab:selected {
        background-color: #0e639c;
        font-weight: bold;
        border-bottom: 2px solid #2ecc71;
    }
    QTabBar::tab:focus {
        border: 1px solid #2ecc71;
    }
"""


def add_playback_window_controls(pw_layout, ranges_container, add_range_btn):
    """Append the shared Playback Window block to `pw_layout`.

    Returns (apply_btn, clear_btn, status_label).
    """
    pw_layout.addWidget(QLabel("Playback Ranges (played sequentially):"))
    pw_layout.addWidget(ranges_container)

    add_row = QHBoxLayout()
    add_row.addStretch()
    add_row.addWidget(add_range_btn)
    pw_layout.addLayout(add_row)

    pw_layout.addSpacing(8)
    btn_row = QHBoxLayout()
    apply_btn = QPushButton("▶  Apply & Play")
    apply_btn.setStyleSheet("background-color: #2ecc71; color: black; font-weight: bold; height: 32px;")
    clear_btn = QPushButton("Clear")
    clear_btn.setStyleSheet("QPushButton { background-color: #c0392b; color: white; height: 32px; min-width: 80px; font-weight: bold; } QPushButton:disabled { background-color: #555; color: #aaa; }")
    btn_row.addWidget(apply_btn)
    btn_row.addWidget(clear_btn)
    pw_layout.addLayout(btn_row)

    status_label = QLabel("No playback window active")
    status_label.setStyleSheet("color: #888; font-size: 10px;")
    pw_layout.addWidget(status_label)
    pw_layout.addStretch()

    return apply_btn, clear_btn, status_label


def create_range_row_section(length_getter, sync_single_row_end=False):
    """Build a container of removable Start/End time-picker rows.

    `length_getter` supplies the current media length in seconds, used as the End default when
    the last row is removed. With `sync_single_row_end`, removing a row while exactly one
    remains also stretches that row's End to the media length.

    Returns (container, add_row) where add_row(start_seconds=None, end_seconds=None) appends a row.
    """
    container = QWidget()
    rows_layout = QVBoxLayout(container)
    rows_layout.setContentsMargins(0, 0, 0, 0)
    rows_layout.setSpacing(8)

    def media_length_seconds():
        try:
            return int(length_getter())
        except Exception:
            return 0

    def make_row(default_start=None, default_end=None):
        row = QWidget()
        row_layout = QHBoxLayout(row)
        start_picker = TimePickerWidget()
        end_picker = TimePickerWidget()

        try:
            if default_start is not None:
                start_picker.set_total_seconds(int(default_start))
            if default_end is not None:
                end_picker.set_total_seconds(int(default_end))
        except Exception:
            pass

        remove_btn = QPushButton("Remove")
        remove_btn.setFixedWidth(80)
        remove_btn.setStyleSheet("background-color: #b00020; color: white;")

        row_layout.addWidget(QLabel("Start:"))
        row_layout.addWidget(start_picker)
        row_layout.addSpacing(10)
        row_layout.addWidget(QLabel("End:"))
        row_layout.addWidget(end_picker)
        row_layout.addWidget(remove_btn)
        row_layout.addStretch()

        def _remove():
            for index in range(rows_layout.count()):
                if rows_layout.itemAt(index).widget() is row:
                    removed = rows_layout.takeAt(index).widget()
                    if removed:
                        removed.deleteLater()
                    break

            try:
                remaining = rows_layout.count()
                if remaining == 0:
                    add_row(0, media_length_seconds())
                elif remaining == 1 and sync_single_row_end:
                    last_row = rows_layout.itemAt(0).widget()
                    if last_row:
                        pickers = last_row.findChildren(TimePickerWidget)
                        if len(pickers) >= 2:
                            pickers[1].set_total_seconds(media_length_seconds())
            except Exception:
                pass

        remove_btn.clicked.connect(_remove)
        return row

    def add_row(start_seconds=None, end_seconds=None):
        rows_layout.addWidget(make_row(start_seconds, end_seconds))

    return container, add_row
