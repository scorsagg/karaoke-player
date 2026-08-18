"""Helpers for reading and resetting the Start/End time-picker rows used by trim and
playback-window controls on both the Audio Studio and Video Studio pages."""

from source_code.ui.extra_page import TimePickerWidget


def _row_layout(container):
    return container.layout() if container is not None else None


def iter_row_pickers(container):
    """Yield the (start, end) time pickers of every range row in a container."""
    layout = _row_layout(container)
    if layout is None:
        return

    for index in range(layout.count()):
        row = layout.itemAt(index).widget()
        if not row:
            continue
        pickers = row.findChildren(TimePickerWidget)
        if len(pickers) >= 2:
            yield pickers[0], pickers[1]


def collect_ranges_ms(container, duration_seconds=0, merge=True):
    """Collect row ranges as sorted (start_ms, end_ms) tuples.

    Ranges are clamped to `duration_seconds` when it is positive, empty/inverted ranges are
    dropped, and overlapping ranges are merged unless `merge` is False.
    """
    duration_ms = max(0, int(duration_seconds * 1000))
    ranges_ms = []

    for start_picker, end_picker in iter_row_pickers(container):
        start_ms = int(max(0, start_picker.get_total_seconds()) * 1000)
        end_ms = int(max(0, end_picker.get_total_seconds()) * 1000)

        if duration_ms > 0:
            start_ms = min(start_ms, duration_ms)
            end_ms = min(end_ms, duration_ms)

        if end_ms > start_ms:
            ranges_ms.append((start_ms, end_ms))

    ranges_ms.sort(key=lambda item: item[0])
    if not merge or not ranges_ms:
        return ranges_ms

    merged = [ranges_ms[0]]
    for start_ms, end_ms in ranges_ms[1:]:
        last_start, last_end = merged[-1]
        if start_ms <= last_end:
            merged[-1] = (last_start, max(last_end, end_ms))
        else:
            merged.append((start_ms, end_ms))

    return merged


def clear_rows(container):
    """Remove every range row from a container."""
    layout = _row_layout(container)
    if layout is None:
        return

    while layout.count() > 0:
        row = layout.takeAt(0).widget()
        if row:
            row.deleteLater()


def reset_rows_to_single_range(container, add_row_fn, start_seconds=0, end_seconds=0):
    """Replace all range rows with a single row using the provided defaults."""
    if container is None or not callable(add_row_fn):
        return

    if _row_layout(container) is None:
        return

    clear_rows(container)
    add_row_fn(int(start_seconds), int(end_seconds))


def set_first_row_range(container, end_seconds, start_seconds=0):
    """Point the first range row at start/end seconds, typically 00:00 -> media duration."""
    for start_picker, end_picker in iter_row_pickers(container):
        start_picker.set_total_seconds(max(0, int(start_seconds)))
        end_picker.set_total_seconds(max(0, int(end_seconds)))
        return


def last_row_end_seconds(container):
    """Return the End value (seconds) of the last range row, or 0 when there is none."""
    end_seconds = 0
    for _, end_picker in iter_row_pickers(container):
        end_seconds = int(end_picker.get_total_seconds())
    return end_seconds
