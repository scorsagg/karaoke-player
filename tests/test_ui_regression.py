"""Offscreen Qt interaction tests for the current application UI wiring."""

from pathlib import Path

import pytest
from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QScrollArea, QPushButton

from source_code import main as main_module
from source_code.controllers import media_controller, playback_controller
from source_code.ui import audio_studio_page, video_tools_page


class _FakeLogger:
    def __init__(self, log_dir):
        self.log_dir = Path(log_dir)

    def debug(self, _message):
        pass

    info = warning = error = debug

    def exception(self, _context, _exc):
        pass

    def get_logs_dir(self):
        return self.log_dir


class _FakePlayer:
    def __init__(self, parent=None):
        self.parent = parent
        self.volume = 80
        self.muted = False
        self.rate = 1.0
        self.length = 60_000
        self.calls = []

    def get_length(self):
        return self.length

    def get_mute(self):
        return self.muted

    def set_mute(self, muted):
        self.muted = muted

    def set_volume(self, volume):
        self.volume = volume

    def set_rate(self, rate):
        self.rate = rate

    def stop(self):
        self.calls.append(("stop",))


class _FakeAnalyzer(QObject):
    level_updated = Signal(float)
    pitch_updated = Signal(str)
    analyzer_error = Signal(str)

    def start(self):
        pass

    def stop(self):
        pass

    def wait(self, _milliseconds):
        return True

    def isRunning(self):
        return False


class _FakeAudioService:
    def __init__(self, *_args, **_kwargs):
        pass

    def cleanup(self):
        pass

    def pause_analyzer(self):
        return False

    def resume_analyzer(self):
        pass

    def set_display_mode(self, _mode):
        pass


class _FakeRealtimePitch:
    def __init__(self, *_args, **_kwargs):
        self.calls = []

    def stop(self):
        pass

    def set_gain(self, gain):
        self.calls.append(("gain", gain))

    def set_pitch(self, pitch):
        self.calls.append(("pitch", pitch))

    def set_speed(self, speed):
        self.calls.append(("speed", speed))

    def is_active(self):
        return False


def _record_calls(calls, name):
    def record(_self, *args, **kwargs):
        calls.setdefault(name, []).append((args, kwargs))

    return record


@pytest.fixture
def application(qapp, monkeypatch, tmp_path):
    """Construct the real shell with fake external services and observable action sinks."""
    calls = {}

    def init_settings_manager(app):
        app.settings = {
            "ffmpeg_path": "ffmpeg",
            "ffprobe_path": "ffprobe",
            "ytdlp_path": "yt-dlp",
            "measurement_mode": "dB Output (dBFS)",
            "auto_reduce_threshold": 90,
            "download_directory": str(tmp_path),
        }
        app.settings_file = tmp_path / "settings.json"
        app.logger = _FakeLogger(tmp_path / "logs")

    monkeypatch.setattr(main_module.KaraokeApp, "init_settings_manager", init_settings_manager)
    monkeypatch.setattr(main_module, "PlayerService", _FakePlayer)
    monkeypatch.setattr(main_module, "AudioAnalyzerThread", _FakeAnalyzer)
    monkeypatch.setattr(main_module, "AudioService", _FakeAudioService)
    monkeypatch.setattr(main_module, "RealtimePitchService", _FakeRealtimePitch)
    monkeypatch.setattr(audio_studio_page, "audio_length_getter", lambda: 0)
    monkeypatch.setattr(video_tools_page, "video_length_getter", lambda: 0)

    for name in (
        "load_video", "load_history_item", "load_history_from_disk",
    ):
        monkeypatch.setattr(
            media_controller.MediaController,
            name,
            _record_calls(calls, f"media.{name}"),
        )
    for name in ("handle_play", "handle_pause", "handle_stop", "jump_time"):
        monkeypatch.setattr(
            playback_controller.PlaybackController,
            name,
            _record_calls(calls, f"playback.{name}"),
        )

    for name in (
        "download_video", "download_audio", "load_audio_tools_file",
        "extract_audio_from_video", "widen_active_video_canvas",
        "trim_audio", "convert_audio_format", "normalize_audio",
        "start_audio_separator", "select_merge_input_a", "select_merge_input_b",
        "execute_join_merge", "amplify_export_media", "start_live_amplify_preview",
        "stop_live_amplify_preview", "trim_video", "export_video", "open_settings",
    ):
        monkeypatch.setattr(
            main_module.KaraokeApp,
            name,
            _record_calls(calls, f"app.{name}"),
        )

    app = main_module.KaraokeApp()
    app.show()
    qapp.processEvents()
    yield app, calls
    app.close()
    qapp.processEvents()


def _click_tab(qapp, tabs, index):
    tab_bar = tabs.tabBar()
    QTest.mouseClick(
        tab_bar,
        Qt.MouseButton.LeftButton,
        pos=tab_bar.tabRect(index).center(),
    )
    qapp.processEvents()


def _click_list_item(qapp, list_widget, index):
    item_index = list_widget.model().index(index, 0)
    QTest.mouseClick(
        list_widget.viewport(),
        Qt.MouseButton.LeftButton,
        pos=list_widget.visualRect(item_index).center(),
    )
    qapp.processEvents()


def _open_studios(app):
    if not app.extra_tools_container.isVisible():
        QTest.mouseClick(app.extra_tools_toggle_btn, Qt.MouseButton.LeftButton)


def _page_button(app, page_index, text):
    page = app.stack.widget(page_index)
    if hasattr(page, "widget"):
        page = page.widget()
    return next(button for button in page.findChildren(QPushButton) if button.text() == text)


def _reveal_widget(qapp, app, widget):
    for scroll_area in app.findChildren(QScrollArea):
        page = scroll_area.widget()
        if page is not None and page.isAncestorOf(widget):
            scroll_area.ensureWidgetVisible(widget)
    qapp.processEvents()


def test_main_navigation_and_studio_tabs_are_operable(application, qapp):
    app, _calls = application

    QTest.mouseClick(app.extra_tools_toggle_btn, Qt.MouseButton.LeftButton)
    assert app.extra_tools_container.isVisible()

    QTest.mouseClick(app.audio_tools_btn, Qt.MouseButton.LeftButton)
    assert app.stack.currentIndex() == app.PAGE_AUDIO_STUDIO
    assert app.pw_ranges_container is app.audio_pw_ranges_container
    _click_tab(qapp, app.audio_tools_tabs, 1)
    assert app.audio_tools_tabs.currentIndex() == 1

    QTest.mouseClick(app.video_tools_btn, Qt.MouseButton.LeftButton)
    assert app.stack.currentIndex() == app.PAGE_VIDEO_STUDIO
    _click_tab(qapp, app.video_tools_tabs, 3)
    assert app.video_tools_tabs.currentIndex() == 3
    assert app.video_frame.minimumHeight() == 420

    QTest.mouseClick(app.convert_export_btn, Qt.MouseButton.LeftButton)
    assert app.stack.currentIndex() == app.PAGE_CONVERT_EXPORT
    _click_tab(qapp, app.convert_export_tabs, 4)
    assert app.convert_export_tabs.currentIndex() == 4

    _click_list_item(qapp, app.nav_list, app.PAGE_PLAYBACK)
    assert app.stack.currentIndex() == app.PAGE_PLAYBACK


def test_media_loader_playback_and_pitch_controls_reach_their_handlers(application, qapp):
    app, calls = application

    QTest.mouseClick(app.load_btn, Qt.MouseButton.LeftButton)
    assert calls["media.load_video"][-1][0] == (app,)

    QTest.keyClicks(app.url_input, "https://example.invalid/audio")
    QTest.mouseClick(app.media_loader_download_btn, Qt.MouseButton.LeftButton)
    assert calls["app.download_video"][-1][0] == ()

    _click_list_item(qapp, app.nav_list, app.PAGE_PLAYBACK)
    QTest.mouseClick(app.play_btn, Qt.MouseButton.LeftButton)
    QTest.mouseClick(app.pause_btn, Qt.MouseButton.LeftButton)
    QTest.mouseClick(app.stop_btn, Qt.MouseButton.LeftButton)
    QTest.mouseClick(app.back_btn, Qt.MouseButton.LeftButton)
    QTest.mouseClick(app.fwd_btn, Qt.MouseButton.LeftButton)
    assert [call[0][0] for call in calls["playback.handle_play"]] == [app]
    assert [call[0][0] for call in calls["playback.handle_pause"]] == [app]
    assert [call[0][0] for call in calls["playback.handle_stop"]] == [app]
    assert [call[0][1] for call in calls["playback.jump_time"]] == [-10_000, 10_000]

    QTest.mouseClick(app.pitch_plus, Qt.MouseButton.LeftButton)
    assert app.pitch_input.value() == 1.0
    assert ("pitch", 1.0) in app.realtime_pitch.calls
    QTest.mouseClick(app.speed_plus, Qt.MouseButton.LeftButton)
    assert app.speed_input.value() == 1.05
    assert app.player.rate == pytest.approx(1.05)

    app.vol_slider.setFocus()
    QTest.keyClick(app.vol_slider, Qt.Key.Key_End)
    assert app.player.volume == app.vol_slider.maximum()
    QTest.mouseClick(app.mute_btn, Qt.MouseButton.LeftButton)
    assert app.player.muted is True

    history_path = Path(app.settings["download_directory"]) / "history-song.wav"
    history_path.write_bytes(b"fixture")
    app.media_controller.add_to_history(app, str(history_path))
    QTest.mouseClick(app.history_toggle_btn, Qt.MouseButton.LeftButton)
    assert app.history_container.isVisible()
    history_item = app.history_list.item(0)
    assert history_item.text() == "history-song.wav"


def test_audio_and_video_studio_actions_are_clickable(application, qapp):
    app, calls = application

    _open_studios(app)
    QTest.mouseClick(app.audio_tools_btn, Qt.MouseButton.LeftButton)
    _reveal_widget(qapp, app, app.audio_trim_add_range_btn)
    audio_rows = app.audio_trim_ranges_container.layout().count()
    QTest.mouseClick(app.audio_trim_add_range_btn, Qt.MouseButton.LeftButton)
    assert app.audio_trim_ranges_container.layout().count() == audio_rows + 1
    app.trim_format_combo.setCurrentIndex(1)
    QTest.mouseClick(
        _page_button(app, app.PAGE_AUDIO_STUDIO, "Export Trimmed Audio"),
        Qt.MouseButton.LeftButton,
    )
    assert calls["app.trim_audio"]
    QTest.mouseClick(app.audio_dl_btn, Qt.MouseButton.LeftButton)
    assert calls["app.download_audio"]
    _click_tab(qapp, app.audio_tools_tabs, 1)
    audio_window_rows = app.audio_pw_ranges_container.layout().count()
    QTest.mouseClick(app.audio_pw_add_range_btn, Qt.MouseButton.LeftButton)
    assert app.audio_pw_ranges_container.layout().count() == audio_window_rows + 1
    QTest.mouseClick(app.audio_pw_apply_btn, Qt.MouseButton.LeftButton)
    assert calls["playback.handle_play"]
    QTest.mouseClick(app.audio_pw_clear_btn, Qt.MouseButton.LeftButton)

    QTest.mouseClick(app.video_tools_btn, Qt.MouseButton.LeftButton)
    _reveal_widget(qapp, app, app.video_trim_add_range_btn)
    video_rows = app.video_trim_ranges_container.layout().count()
    QTest.mouseClick(app.video_trim_add_range_btn, Qt.MouseButton.LeftButton)
    assert app.video_trim_ranges_container.layout().count() == video_rows + 1
    app.video_trim_format_combo.setCurrentIndex(1)
    QTest.mouseClick(
        _page_button(app, app.PAGE_VIDEO_STUDIO, "Export Trimmed Video"),
        Qt.MouseButton.LeftButton,
    )
    assert calls["app.trim_video"]
    app.video_path = "synthetic-video.mp4"
    app.update_extraction_ui(True)
    _click_tab(qapp, app.video_tools_tabs, 2)
    _reveal_widget(qapp, app, app.extract_btn)
    QTest.mouseClick(app.extract_btn, Qt.MouseButton.LeftButton)
    assert calls["app.extract_audio_from_video"]
    _click_tab(qapp, app.video_tools_tabs, 3)
    _reveal_widget(qapp, app, app.widen_exec_btn)
    QTest.mouseClick(app.widen_exec_btn, Qt.MouseButton.LeftButton)
    assert calls["app.widen_active_video_canvas"]
    _click_tab(qapp, app.video_tools_tabs, 1)
    video_window_rows = app.video_pw_ranges_container.layout().count()
    QTest.mouseClick(app.video_pw_add_range_btn, Qt.MouseButton.LeftButton)
    assert app.video_pw_ranges_container.layout().count() == video_window_rows + 1
    QTest.mouseClick(app.video_pw_apply_btn, Qt.MouseButton.LeftButton)
    assert calls["playback.handle_play"]


def test_convert_export_actions_and_settings_are_reachable(application, qapp):
    app, calls = application

    _open_studios(app)
    QTest.mouseClick(app.convert_export_btn, Qt.MouseButton.LeftButton)
    convert_btn = _page_button(app, app.PAGE_CONVERT_EXPORT, "Convert & Export")
    normalize_btn = _page_button(app, app.PAGE_CONVERT_EXPORT, "Normalize & Export")
    merge_execute_btn = _page_button(app, app.PAGE_CONVERT_EXPORT, "Join / Merge Now")
    workflows = (
        (0, convert_btn, "app.convert_audio_format"),
        (1, normalize_btn, "app.normalize_audio"),
        (2, app.vocal_sep_btn, "app.start_audio_separator"),
        (3, app.merge_input_a_btn, "app.select_merge_input_a"),
        (3, app.merge_input_b_btn, "app.select_merge_input_b"),
        (3, merge_execute_btn, "app.execute_join_merge"),
        (4, app.amp_btn, "app.amplify_export_media"),
        (4, app.amp_live_btn, "app.start_live_amplify_preview"),
    )
    for tab_index, button, callback in workflows:
        _click_tab(qapp, app.convert_export_tabs, tab_index)
        QTest.mouseClick(button, Qt.MouseButton.LeftButton)
        assert calls[callback], callback

    assert not app.amp_live_stop_btn.isEnabled()
    QTest.mouseClick(app.settings_btn, Qt.MouseButton.LeftButton)
    assert calls["app.open_settings"]


def test_generated_media_fixture_is_available_for_integration_tests(generated_media_files):
    assert generated_media_files["audio"].is_file()
    assert generated_media_files["video"].is_file()
