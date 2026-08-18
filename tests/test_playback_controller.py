"""Unit tests for source_code/controllers/playback_controller.py"""

import pytest
from PySide6.QtWidgets import QVBoxLayout, QWidget

from source_code.controllers import playback_controller as pb_module
from source_code.controllers.playback_controller import PlaybackController
from source_code.ui.extra_page import TimePickerWidget

PAGE_PLAYBACK = 0
PAGE_AUDIO_STUDIO = 2


class FakeLabel:
    def __init__(self):
        self._text = ""
        self._style = ""

    def setText(self, text):
        self._text = text

    def text(self):
        return self._text

    def setStyleSheet(self, style):
        self._style = style

    def styleSheet(self):
        return self._style


class FakeSlider:
    def __init__(self):
        self._value = 50

    def setValue(self, value):
        self._value = value

    def value(self):
        return self._value


class FakePlayer:
    def __init__(self, time_ms=0, length_ms=60000, active=True, media=True, ended=False):
        self._time = time_ms
        self._length = length_ms
        self._active = active
        self._media = media
        self._ended = ended
        self.positions = []
        self.times = []
        self.calls = []
        self.muted = None
        self.set_media_error = None

    def is_active(self):
        return self._active

    def has_media(self):
        return self._media

    def is_ended(self):
        return self._ended

    def get_time(self):
        return self._time

    def get_length(self):
        return self._length

    def set_position(self, ratio):
        self.positions.append(ratio)

    def set_time(self, ms):
        self.times.append(ms)

    def set_media(self, path):
        if self.set_media_error:
            raise self.set_media_error
        self._media = True
        self.calls.append(("set_media", path))

    def set_mute(self, flag):
        self.muted = flag

    def play(self):
        self.calls.append(("play",))

    def pause(self):
        self.calls.append(("pause",))

    def stop(self):
        self.calls.append(("stop",))


class FakeRealtimePitch:
    def __init__(self, active=False):
        self.active = active
        self.stopped = False
        self.loaded = []

    def is_active(self):
        return self.active

    def stop(self):
        self.stopped = True

    def load_file(self, path):
        self.loaded.append(path)


class FakeState:
    def __init__(self):
        self._player_was_active = True
        self._pending_seek_ratio = None


class FakeApp:
    PAGE_PLAYBACK = PAGE_PLAYBACK
    PAGE_AUDIO_STUDIO = PAGE_AUDIO_STUDIO

    def __init__(self, **overrides):
        self.player = FakePlayer()
        self.realtime_pitch = FakeRealtimePitch()
        self.state = FakeState()
        self.realtime_pitch_enabled = False
        self.page_index = PAGE_PLAYBACK
        self.video_path = ""
        self.seek_slider = FakeSlider()
        self.time_label = FakeLabel()
        self.status_label = FakeLabel()
        self.pw_status_label = FakeLabel()
        self.pw_ranges_container = None
        self.debug_lines = []
        self.shifted_plays = []
        self.pitch_status_refreshes = 0
        self.cleared_preview = 0
        self.audio_service = type(
            "A", (), {"stop_audio_monitoring": lambda self_: None}
        )()
        self.duration_seconds = 0
        self.reset_rows_calls = []
        self.stack = type("S", (), {"currentIndex": lambda self_: self.page_index})()
        for key, value in overrides.items():
            setattr(self, key, value)

    def _is_realtime_pitch_enabled(self):
        return self.realtime_pitch_enabled

    def play_shifted(self, start_from_current=False):
        self.shifted_plays.append(start_from_current)

    def _refresh_realtime_pitch_status(self):
        self.pitch_status_refreshes += 1

    def _clear_live_amplify_preview_state(self):
        self.cleared_preview += 1

    def log_debug(self, message):
        self.debug_lines.append(message)

    def _get_current_video_duration_seconds(self):
        return self.duration_seconds

    def _reset_rows_to_single_range(self, container, add_range, start_s, total_s):
        self.reset_rows_calls.append((start_s, total_s))


@pytest.fixture
def controller():
    return PlaybackController()


@pytest.fixture
def app():
    return FakeApp()


@pytest.fixture
def dialogs(monkeypatch):
    """Capture QMessageBox.warning calls instead of showing modal dialogs."""
    warnings = []

    class FakeMessageBox:
        @staticmethod
        def warning(parent, title, text):
            warnings.append((title, text))

    monkeypatch.setattr(pb_module, "QMessageBox", FakeMessageBox)
    return warnings


@pytest.fixture
def deferred_calls(monkeypatch):
    """Capture QTimer.singleShot callbacks so retries can be driven explicitly."""
    scheduled = []

    class FakeTimer:
        @staticmethod
        def singleShot(msec, callback):
            scheduled.append(callback)

    monkeypatch.setattr(pb_module, "QTimer", FakeTimer)
    return scheduled


def _ranges_container(qapp, ranges_seconds):
    """Build a Playback Window container holding one row of time pickers per range."""
    container = QWidget()
    layout = QVBoxLayout(container)
    for start_s, end_s in ranges_seconds:
        row = QWidget()
        row_layout = QVBoxLayout(row)
        start_picker = TimePickerWidget()
        start_picker.set_total_seconds(start_s)
        end_picker = TimePickerWidget()
        end_picker.set_total_seconds(end_s)
        row_layout.addWidget(start_picker)
        row_layout.addWidget(end_picker)
        layout.addWidget(row)
    return container


class TestJumpTime:
    def test_seeks_relative_to_current_time(self, controller, app):
        app.player = FakePlayer(time_ms=10000, length_ms=60000)

        controller.jump_time(app, 5000)

        assert app.player.positions == [pytest.approx(15000 / 60000)]

    def test_seek_is_clamped_to_media_bounds(self, controller, app):
        app.player = FakePlayer(time_ms=59000, length_ms=60000)

        controller.jump_time(app, 10000)

        assert app.player.positions == [pytest.approx(59999 / 60000)]

    def test_backwards_seek_never_goes_negative(self, controller, app):
        app.player = FakePlayer(time_ms=1000, length_ms=60000)

        controller.jump_time(app, -5000)

        assert app.player.positions == [0.0]

    def test_unknown_duration_is_ignored(self, controller, app):
        app.player = FakePlayer(length_ms=0)

        controller.jump_time(app, 5000)

        assert app.player.positions == []

    def test_inactive_player_without_media_cannot_seek(self, controller, app):
        app.player = FakePlayer(active=False, media=False)

        controller.jump_time(app, 5000)

        assert app.player.positions == []

    def test_stopped_player_rebinds_media_before_seeking(self, controller, app, tmp_path):
        media = tmp_path / "song.mp4"
        media.write_bytes(b"data")
        app.video_path = str(media)
        app.player = FakePlayer(active=False, media=False)

        controller.jump_time(app, 5000)

        assert ("set_media", str(media)) in app.player.calls
        assert app.player.positions


class TestMediaRebind:
    def test_bound_media_needs_no_rebind(self, controller, app):
        assert controller._ensure_media_loaded_for_playback(app) is True
        assert app.player.calls == []

    def test_ended_media_is_rebound(self, controller, app, tmp_path):
        media = tmp_path / "song.mp4"
        media.write_bytes(b"data")
        app.video_path = str(media)
        app.player = FakePlayer(ended=True)

        assert controller._ensure_media_loaded_for_playback(app) is True
        assert app.player.calls == [("set_media", str(media))]

    def test_broken_player_state_triggers_rebind(self, controller, app, tmp_path):
        media = tmp_path / "song.mp4"
        media.write_bytes(b"data")
        app.video_path = str(media)

        def _boom():
            raise RuntimeError("vlc gone")

        app.player.has_media = _boom

        assert controller._ensure_media_loaded_for_playback(app) is True

    def test_rebind_fails_without_existing_file(self, controller, app):
        app.player = FakePlayer(media=False)
        app.video_path = "/gone.mp4"

        assert controller._ensure_media_loaded_for_playback(app) is False

    def test_rebind_failure_is_logged(self, controller, app, tmp_path):
        media = tmp_path / "song.mp4"
        media.write_bytes(b"data")
        app.video_path = str(media)
        app.player = FakePlayer(media=False)
        app.player.set_media_error = RuntimeError("vlc refused")

        assert controller._ensure_media_loaded_for_playback(app) is False
        assert "playback_rebind" in app.debug_lines[0]


class TestPendingSeek:
    def test_no_pending_seek_is_a_noop(self, controller, app, deferred_calls):
        controller._apply_pending_seek_after_play(app)

        assert app.player.times == []

    def test_pending_ratio_is_converted_to_milliseconds(self, controller, app, deferred_calls):
        app._pending_seek_ratio = 0.5

        controller._apply_pending_seek_after_play(app)

        assert app.player.times == [30000]
        assert app.state._pending_seek_ratio is None

    def test_pending_ratio_is_clamped(self, controller, app, deferred_calls):
        app._pending_seek_ratio = 3.0

        controller._apply_pending_seek_after_play(app)

        assert app.player.times == [60000]

    def test_unknown_duration_retries_before_falling_back(self, controller, app, deferred_calls):
        app._pending_seek_ratio = 0.25
        app.player = FakePlayer(length_ms=0)

        controller._apply_pending_seek_after_play(app, retries=1)
        assert app.player.times == []
        assert len(deferred_calls) == 1

        deferred_calls[0]()

        assert app.player.positions == [pytest.approx(0.25)]

    def test_seek_errors_are_swallowed(self, controller, app, deferred_calls):
        app._pending_seek_ratio = 0.5

        def _boom(ms):
            raise RuntimeError("vlc gone")

        app.player.set_time = _boom

        controller._apply_pending_seek_after_play(app)

        assert app.state._pending_seek_ratio is None


class TestRealtimeResync:
    def test_active_realtime_pitch_restarts_from_new_position(self, controller, app):
        app.realtime_pitch_enabled = True
        app.realtime_pitch = FakeRealtimePitch(active=True)
        app.video_path = "/media/song.mp4"

        controller._resync_realtime_audio_after_seek(app)

        assert app.realtime_pitch.stopped is True
        assert app.realtime_pitch.loaded == ["/media/song.mp4"]
        assert app.shifted_plays == [True]

    def test_disabled_realtime_pitch_is_untouched(self, controller, app):
        controller._resync_realtime_audio_after_seek(app)

        assert app.shifted_plays == []

    def test_inactive_stream_is_not_restarted(self, controller, app):
        app.realtime_pitch_enabled = True

        controller._resync_realtime_audio_after_seek(app)

        assert app.shifted_plays == []

    def test_inactive_player_is_not_restarted(self, controller, app):
        app.realtime_pitch_enabled = True
        app.realtime_pitch = FakeRealtimePitch(active=True)
        app.player = FakePlayer(active=False)

        controller._resync_realtime_audio_after_seek(app)

        assert app.shifted_plays == []


class TestPlayPauseStop:
    def test_realtime_pitch_on_playback_page_plays_shifted_stream(self, controller, app, dialogs, deferred_calls):
        app.realtime_pitch_enabled = True

        controller.handle_play(app)

        assert app.shifted_plays == [True]
        assert app.player.calls == []

    def test_play_without_media_warns(self, controller, app, dialogs, deferred_calls):
        app.player = FakePlayer(media=False)
        app.video_path = "/gone.mp4"

        controller.handle_play(app)

        assert dialogs[0][0] == "Playback"
        assert app.player.calls == []

    def test_play_unmutes_and_starts_playback(self, controller, app, dialogs, deferred_calls):
        controller.handle_play(app)

        assert app.player.muted is False
        assert ("play",) in app.player.calls
        assert app.pitch_status_refreshes == 1

    def test_play_stops_active_shifted_stream(self, controller, app, dialogs, deferred_calls):
        app.realtime_pitch = FakeRealtimePitch(active=True)

        controller.handle_play(app)

        assert app.realtime_pitch.stopped is True
        assert app.cleared_preview == 1

    def test_pause_stops_shifted_stream_too(self, controller, app):
        app.realtime_pitch = FakeRealtimePitch(active=True)

        controller.handle_pause(app)

        assert app.player.calls == [("pause",)]
        assert app.realtime_pitch.stopped is True
        assert app.pitch_status_refreshes == 1

    def test_stop_resets_transport_ui(self, controller, app):
        app.video_path = "/media/song.mp4"
        app.seek_slider.setValue(42)

        controller.handle_stop(app)

        assert app.player.calls == [("stop",)]
        assert app.seek_slider.value() == 0
        assert app.time_label.text() == "00:00"
        assert app.status_label.text() == "Status: Stopped song.mp4"
        assert app.state._player_was_active is False

    def test_stop_without_media_shows_generic_status(self, controller, app):
        controller.handle_stop(app)

        assert app.status_label.text() == "Status: Stopped"


class TestPlaybackWindow:
    def test_no_rows_means_no_active_window(self, controller, app, qapp):
        app.pw_ranges_container = _ranges_container(qapp, [])

        controller.apply_playback_window(app)

        assert controller._pw_ranges == []
        assert app.pw_status_label.text() == "No playback window active"

    def test_missing_container_is_tolerated(self, controller, app):
        controller.apply_playback_window(app)

        assert controller._pw_ranges == []

    def test_ranges_are_sorted_and_summarized(self, controller, app, qapp):
        app.pw_ranges_container = _ranges_container(qapp, [(90, 120), (10, 20)])

        controller.apply_playback_window(app)

        assert controller._pw_ranges == [(10000, 20000), (90000, 120000)]
        assert app.pw_status_label.text() == "Ranges: 00:10-00:20, 01:30-02:00"
        assert app.player.times == [10000]
        assert controller._pw_end_ms == 20000
        assert app._pw_range_idx == 0

    def test_invalid_range_is_dropped(self, controller, app, qapp):
        app.pw_ranges_container = _ranges_container(qapp, [(30, 10)])

        controller.apply_playback_window(app)

        assert controller._pw_ranges == []

    def test_full_length_single_range_is_treated_as_no_window(self, controller, app, qapp):
        app.pw_ranges_container = _ranges_container(qapp, [(0, 60)])

        controller.apply_playback_window(app)

        assert controller._pw_ranges == []
        assert app.pw_status_label.text() == "No playback window active"

    def test_range_starting_at_zero_does_not_seek(self, controller, app, qapp):
        app.pw_ranges_container = _ranges_container(qapp, [(0, 30)])

        controller.apply_playback_window(app)

        assert controller._pw_ranges == [(0, 30000)]
        assert app.player.times == []

    def test_clear_resets_state_and_rows(self, controller, app):
        controller._pw_ranges = [(0, 1000)]
        controller._pw_end_ms = 1000
        app.duration_seconds = 90

        controller.clear_playback_window(app)

        assert controller._pw_ranges == []
        assert controller._pw_end_ms is None
        assert app._pw_ranges == []
        assert app.reset_rows_calls == [(0, 90)]
        assert app.pw_status_label.text() == "No playback window active"

    def test_clear_tolerates_row_reset_failures(self, controller, app):
        def _boom(*args):
            raise RuntimeError("no rows")

        app._reset_rows_to_single_range = _boom

        controller.clear_playback_window(app)

        assert app.pw_status_label.text() == "No playback window active"


class TestAddRange:
    def test_new_range_starts_after_previous_end(self, controller, app, qapp):
        app.pw_ranges_container = _ranges_container(qapp, [(0, 20)])
        added = []
        app.pw_add_range = lambda start, end: added.append((start, end))

        controller._on_pw_add_range(app)

        assert added == [(21, 60)]

    def test_first_range_spans_whole_media(self, controller, app, qapp):
        app.pw_ranges_container = _ranges_container(qapp, [])
        added = []
        app.pw_add_range = lambda start, end: added.append((start, end))

        controller._on_pw_add_range(app)

        assert added == [(1, 60)]

    def test_range_covering_end_is_rejected(self, controller, app, qapp):
        app.pw_ranges_container = _ranges_container(qapp, [(0, 60)])
        added = []
        app.pw_add_range = lambda start, end: added.append((start, end))

        controller._on_pw_add_range(app)

        assert added == []
        assert app.pw_status_label.text() == "Cannot add range — already covers to video end"

    def test_missing_container_is_tolerated(self, controller, app):
        added = []
        app.pw_add_range = lambda start, end: added.append((start, end))

        controller._on_pw_add_range(app)

        assert added == [(1, 60)]

    def test_player_failure_is_swallowed(self, controller, app):
        def _boom():
            raise RuntimeError("vlc gone")

        app.player.get_length = _boom

        controller._on_pw_add_range(app)
