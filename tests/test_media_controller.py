"""Unit tests for source_code/controllers/media_controller.py"""

import json
import time

import pytest
from PySide6.QtWidgets import QListWidget

from source_code.controllers import media_controller as mc_module
from source_code.controllers.media_controller import MediaController

PAGE_AUDIO_STUDIO = 2
PAGE_VIDEO_STUDIO = 3


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


class FakeToggleButton(FakeLabel):
    pass


class FakeContainer:
    def __init__(self):
        self.visible = None

    def setVisible(self, flag):
        self.visible = flag


class FakeCombo:
    def __init__(self):
        self.enabled = None

    def setEnabled(self, flag):
        self.enabled = flag


class FakeSpin:
    def __init__(self, value=0.0):
        self._value = value

    def setValue(self, value):
        self._value = value

    def value(self):
        return self._value


class FakeFrame:
    def __init__(self):
        self.min_height = None
        self.max_height = None

    def setMinimumHeight(self, value):
        self.min_height = value

    def setMaximumHeight(self, value):
        self.max_height = value

    def winId(self):
        return 4321


class FakeStack:
    def __init__(self, index=0):
        self.index = index

    def currentIndex(self):
        return self.index


class FakeLoader:
    def __init__(self):
        self.progress = []
        self.finished_for = None
        self.closed = False

    def set_progress(self, value, text=""):
        self.progress.append((value, text))

    def finish(self, widget):
        self.finished_for = widget

    def close(self):
        self.closed = True


class FakePlayer:
    def __init__(self, audio_track=0):
        self.audio_track = audio_track
        self.calls = []
        self.muted = None

    def set_mute(self, flag):
        self.muted = flag

    def set_media(self, path):
        self.calls.append(("set_media", path))

    def set_video_widget(self, widget_id):
        self.calls.append(("set_video_widget", widget_id))

    def play(self):
        self.calls.append(("play",))

    def get_audio_track(self):
        return self.audio_track


class FakeFileLoadingService:
    def __init__(self, was_playing=True):
        self.was_playing = was_playing
        self.finished_with = []

    def prepare_for_loading(self):
        return self.was_playing

    def finish_loading(self, resume_audio=True):
        self.finished_with.append(resume_audio)


class FakeRealtimePitch:
    def __init__(self, active=False):
        self.active = active
        self.stopped = False

    def is_active(self):
        return self.active

    def stop(self):
        self.stopped = True


class FakeState:
    def __init__(self):
        self.history_is_expanded = False
        self.extra_tools_is_expanded = False
        self._current_is_audio_only = False
        self._pending_video_path = None


class FakeApp:
    PAGE_AUDIO_STUDIO = PAGE_AUDIO_STUDIO
    PAGE_VIDEO_STUDIO = PAGE_VIDEO_STUDIO

    def __init__(self, tmp_path, **overrides):
        self.settings = {"base_directory": str(tmp_path)}
        self.settings_file = tmp_path / "settings.json"
        self.history_list = QListWidget()
        self.state = FakeState()
        self.history_container = FakeContainer()
        self.history_toggle_btn = FakeToggleButton()
        self.extra_tools_container = FakeContainer()
        self.extra_tools_toggle_btn = FakeToggleButton()
        self.status_label = FakeLabel()
        self.filename_label = FakeLabel()
        self.time_label = FakeLabel()
        self.audio_file_status = FakeLabel()
        self.video_extract_status_label = FakeLabel()
        self.extract_format_combo = FakeCombo()
        self.extract_btn = FakeCombo()
        self.pitch_input = FakeSpin()
        self.speed_input = FakeSpin()
        self.vol_slider = FakeSpin(80)
        self.video_frame = FakeFrame()
        self.stack = FakeStack()
        self.player = FakePlayer()
        self.realtime_pitch = FakeRealtimePitch()
        self.file_loading_service = FakeFileLoadingService()
        self.audio_service = type("A", (), {"start_audio_monitoring": lambda self_: None})()
        self.video_path = ""
        self.audio_tools_file_path = ""
        self.media_type = "video"
        self.volumes = []
        self.loaded = []
        self.navigations = []
        self.refresh_targets = []
        self.extraction_ui_calls = []
        self.visualization = []
        self.exceptions = []
        self.finish_loading_calls = []
        self.resets = []
        for key, value in overrides.items():
            setattr(self, key, value)

    def classify_media_type(self, path):
        return self.media_type

    def set_volume(self, value):
        self.volumes.append(value)

    def load_video(self, path, is_audio_only=None):
        self.loaded.append((path, is_audio_only))

    def handle_navigation_change(self, idx):
        self.navigations.append(idx)

    def refresh_conversion_targets(self, path=None):
        self.refresh_targets.append(path)

    def update_extraction_ui(self, is_video):
        self.extraction_ui_calls.append(is_video)

    def show_audio_visualization(self):
        self.visualization.append("show")

    def hide_audio_visualization(self):
        self.visualization.append("hide")

    def finish_loading(self, loader, is_audio_only):
        self.finish_loading_calls.append(is_audio_only)

    def _reset_pitch_display(self):
        self.resets.append("pitch_display")

    def _reset_all_page_timers_on_load(self):
        self.resets.append("timers")

    def _reset_all_page_controls_on_load(self, is_audio_only):
        self.resets.append(("controls", is_audio_only))

    def _sync_all_page_timer_defaults_from_media(self):
        self.resets.append("timer_defaults")

    def _refresh_realtime_pitch_status(self):
        self.resets.append("pitch_status")

    def _clear_live_amplify_preview_state(self):
        self.resets.append("amplify_preview")

    def log_exception(self, where, exc):
        self.exceptions.append((where, str(exc)))


@pytest.fixture
def controller():
    return MediaController()


@pytest.fixture
def app(tmp_path, qapp):
    return FakeApp(tmp_path)


@pytest.fixture
def dialogs(monkeypatch):
    """Capture QMessageBox usage instead of showing modal dialogs."""
    calls = {"information": [], "warning": []}

    class FakeMessageBox:
        @staticmethod
        def information(parent, title, text):
            calls["information"].append((title, text))

        @staticmethod
        def warning(parent, title, text):
            calls["warning"].append((title, text))

    monkeypatch.setattr(mc_module, "QMessageBox", FakeMessageBox)
    return calls


@pytest.fixture
def file_dialog(monkeypatch):
    """Control the file chooser return value."""
    selection = {"path": ""}

    class FakeFileDialog:
        @staticmethod
        def getOpenFileName(parent, caption, directory, filters):
            return selection["path"], ""

    monkeypatch.setattr(mc_module, "QFileDialog", FakeFileDialog)
    return selection


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(time, "sleep", lambda *_: None)


def _make_media(tmp_path, name="song.mp4"):
    media = tmp_path / name
    media.write_bytes(b"data")
    return str(media)


class TestHistory:
    def test_missing_files_are_not_added(self, controller, app):
        controller.add_to_history(app, "/does/not/exist.mp4")
        controller.add_to_history(app, "")

        assert app.history_list.count() == 0

    def test_entry_is_added_with_path_tooltip(self, controller, app, tmp_path):
        path = _make_media(tmp_path)

        controller.add_to_history(app, path)

        assert app.history_list.item(0).text() == "song.mp4"
        assert app.history_list.item(0).toolTip() == path

    def test_re_added_entry_moves_to_top_without_duplicating(self, controller, app, tmp_path):
        first = _make_media(tmp_path, "a.mp4")
        second = _make_media(tmp_path, "b.mp4")

        controller.add_to_history(app, first)
        controller.add_to_history(app, second)
        controller.add_to_history(app, first)

        assert app.history_list.count() == 2
        assert app.history_list.item(0).toolTip() == first

    def test_history_is_capped_at_ten_entries(self, controller, app, tmp_path):
        for i in range(12):
            controller.add_to_history(app, _make_media(tmp_path, f"track{i}.mp4"))

        assert app.history_list.count() == 10
        assert app.history_list.item(0).text() == "track11.mp4"

    def test_history_is_persisted_to_disk(self, controller, app, tmp_path):
        path = _make_media(tmp_path)

        controller.add_to_history(app, path)

        saved = json.loads((tmp_path / "history.json").read_text(encoding="utf-8"))
        assert saved == [path]

    def test_save_ignores_unwritable_location(self, controller, app, tmp_path):
        app.settings_file = tmp_path / "missing-dir" / "settings.json"

        controller.save_history_to_disk(app)

    def test_existing_history_is_restored_in_order(self, controller, app, tmp_path):
        first = _make_media(tmp_path, "a.mp4")
        second = _make_media(tmp_path, "b.mp4")
        (tmp_path / "history.json").write_text(json.dumps([first, second]), encoding="utf-8")

        controller.load_history_from_disk(app)

        assert [app.history_list.item(i).toolTip() for i in range(2)] == [first, second]

    def test_restored_history_skips_deleted_files(self, controller, app, tmp_path):
        path = _make_media(tmp_path)
        (tmp_path / "history.json").write_text(json.dumps([path, "/gone.mp4"]), encoding="utf-8")

        controller.load_history_from_disk(app)

        assert app.history_list.count() == 1

    def test_corrupt_history_file_is_ignored(self, controller, app, tmp_path):
        (tmp_path / "history.json").write_text("not json", encoding="utf-8")

        controller.load_history_from_disk(app)

        assert app.history_list.count() == 0

    def test_missing_history_file_is_ignored(self, controller, app):
        controller.load_history_from_disk(app)

        assert app.history_list.count() == 0

    def test_clear_history_empties_list_and_removes_file(self, controller, app, tmp_path):
        controller.add_to_history(app, _make_media(tmp_path))

        controller.clear_history(app)

        assert app.history_list.count() == 0
        assert not (tmp_path / "history.json").exists()

    def test_clear_history_without_file(self, controller, app):
        controller.clear_history(app)

        assert app.history_list.count() == 0


class TestToggles:
    def test_history_toggle_flips_visibility_and_caret(self, controller, app):
        controller.toggle_history(app)

        assert app.state.history_is_expanded is True
        assert app.history_container.visible is True
        assert app.history_toggle_btn.text() == "▼ History"

        controller.toggle_history(app)

        assert app.history_container.visible is False
        assert app.history_toggle_btn.text() == "▶ History"

    def test_extra_tools_toggle_flips_visibility_and_caret(self, controller, app):
        controller.toggle_extra_tools(app)

        assert app.state.extra_tools_is_expanded is True
        assert app.extra_tools_toggle_btn.text() == "▼ 🧭 Studios"

        controller.toggle_extra_tools(app)

        assert app.extra_tools_container.visible is False
        assert app.extra_tools_toggle_btn.text() == "▶ 🧭 Studios"


class TestExtractionUi:
    def test_video_enables_extraction_controls(self, controller, app):
        app.video_path = "/media/song.mp4"

        controller.update_extraction_ui(app, True)

        assert app.video_extract_status_label.text() == "✅ Ready to extract from: song.mp4"
        assert app.extract_format_combo.enabled is True
        assert app.extract_btn.enabled is True

    def test_audio_disables_extraction_controls(self, controller, app):
        app.video_path = "/media/song.mp3"

        controller.update_extraction_ui(app, False)

        assert "Load a video" in app.video_extract_status_label.text()
        assert app.extract_format_combo.enabled is False
        assert app.extract_btn.enabled is False

    def test_video_flag_without_loaded_path_disables_controls(self, controller, app):
        controller.update_extraction_ui(app, True)

        assert app.extract_btn.enabled is False


class TestFinishLoading:
    def test_resets_controls_and_finishes_splash(self, controller, app):
        app.video_path = "/media/song.mp4"
        loader = FakeLoader()

        controller.finish_loading(app, loader, is_audio_only=False)

        assert app.pitch_input.value() == 0.0
        assert app.speed_input.value() == 1.0
        assert app.filename_label.text() == "Playing: song.mp4"
        assert loader.progress[-1] == (100, "Ready")
        assert loader.finished_for is app
        assert app.state._current_is_audio_only is False
        assert app.visualization == ["hide"]
        assert app.resets[-1] == "timer_defaults"

    def test_audio_only_shows_visualization(self, controller, app):
        controller.finish_loading(app, FakeLoader(), is_audio_only=True)

        assert app.state._current_is_audio_only is True
        assert app.visualization == ["show"]

    def test_audio_studio_page_shrinks_frame_for_audio_only(self, controller, app):
        app.stack = FakeStack(PAGE_AUDIO_STUDIO)

        controller.finish_loading(app, FakeLoader(), is_audio_only=True)

        assert (app.video_frame.min_height, app.video_frame.max_height) == (80, 100)

    def test_audio_studio_page_keeps_larger_frame_for_video(self, controller, app):
        app.stack = FakeStack(PAGE_AUDIO_STUDIO)

        controller.finish_loading(app, FakeLoader(), is_audio_only=False)

        assert (app.video_frame.min_height, app.video_frame.max_height) == (280, 320)

    def test_video_studio_page_refreshes_extraction_ui(self, controller, app):
        app.stack = FakeStack(PAGE_VIDEO_STUDIO)
        app.video_path = "/media/song.mp4"

        controller.finish_loading(app, FakeLoader(), is_audio_only=False)

        assert app.extraction_ui_calls == [True]


class TestLoadAudioToolsFile:
    def test_cancelled_dialog_does_nothing(self, controller, app, dialogs, file_dialog):
        controller.load_audio_tools_file(app)

        assert app.loaded == []
        assert dialogs["warning"] == []

    def test_video_selection_is_rejected(self, controller, app, dialogs, file_dialog, tmp_path):
        file_dialog["path"] = _make_media(tmp_path)
        app.media_type = "video"

        controller.load_audio_tools_file(app)

        assert dialogs["warning"][0][0] == "Audio Studio Only"
        assert app.loaded == []

    def test_audio_selection_is_loaded_as_audio_only(self, controller, app, dialogs, file_dialog, tmp_path):
        path = _make_media(tmp_path, "song.mp3")
        file_dialog["path"] = path
        app.media_type = "audio"

        controller.load_audio_tools_file(app)

        assert app.audio_tools_file_path == path
        assert app.audio_file_status.text() == "✅ song.mp3 (Audio)"
        assert app.loaded == [(path, True)]


class TestLoadHistoryItem:
    def test_missing_file_warns(self, controller, app, dialogs):
        controller.load_history_item(app, "/gone.mp4")

        assert dialogs["warning"][0][0] == "File Not Found"
        assert app.loaded == []

    def test_audio_file_loads_as_audio_only(self, controller, app, dialogs, tmp_path):
        path = _make_media(tmp_path, "song.mp3")
        app.media_type = "audio"

        controller.load_history_item(app, path)

        assert app.loaded == [(path, True)]
        assert app.refresh_targets == [path]

    def test_video_file_from_audio_studio_is_routed_to_video_studio(self, controller, app, dialogs, tmp_path):
        path = _make_media(tmp_path)
        app.stack = FakeStack(PAGE_AUDIO_STUDIO)
        app.media_type = "video"

        controller.load_history_item(app, path)

        assert dialogs["information"][0][0] == "Routed to Video Studio"
        assert app.loaded == [(path, False)]
        assert app.navigations == [PAGE_VIDEO_STUDIO]
        assert app.refresh_targets == []

    def test_audio_file_from_audio_studio_updates_studio_status(self, controller, app, dialogs, tmp_path):
        path = _make_media(tmp_path, "song.mp3")
        app.stack = FakeStack(PAGE_AUDIO_STUDIO)
        app.media_type = "audio"

        controller.load_history_item(app, path)

        assert app.audio_tools_file_path == path
        assert app.audio_file_status.text() == "✅ song.mp3 (Audio)"


class TestLoadVideo:
    def test_full_load_sequence(self, controller, app, dialogs, tmp_path):
        path = _make_media(tmp_path)
        loader = FakeLoader()

        controller.load_video(app, path, splash_screen=loader)

        assert app.video_path == path
        assert ("set_media", str(tmp_path / "song.mp4")) in app.player.calls
        assert ("set_video_widget", 4321) in app.player.calls
        assert ("play",) in app.player.calls
        assert app.volumes == [80]
        assert app.finish_loading_calls == [False]
        assert app.status_label.text() == "Status: Playing song.mp4"
        assert app.file_loading_service.finished_with == [True]
        assert app.history_list.count() == 1

    def test_audio_media_is_detected_automatically(self, controller, app, dialogs, tmp_path):
        path = _make_media(tmp_path, "song.mp3")
        app.media_type = "audio"

        controller.load_video(app, path, splash_screen=FakeLoader())

        assert app.finish_loading_calls == [True]

    def test_audio_detection_overrides_caller_hint(self, controller, app, dialogs, tmp_path):
        path = _make_media(tmp_path, "song.mp3")
        app.media_type = "audio"

        controller.load_video(app, path, splash_screen=FakeLoader(), is_audio_only=False)

        assert app.finish_loading_calls == [True]

    def test_active_realtime_pitch_is_stopped_first(self, controller, app, dialogs, tmp_path):
        app.realtime_pitch = FakeRealtimePitch(active=True)

        controller.load_video(app, _make_media(tmp_path), splash_screen=FakeLoader())

        assert app.realtime_pitch.stopped is True
        assert app.player.muted is False

    def test_dialog_cancellation_aborts_load(self, controller, app, dialogs, file_dialog):
        controller.load_video(app, None, splash_screen=FakeLoader())

        assert app.video_path == ""
        assert app.player.calls == []

    def test_file_chosen_from_dialog_is_loaded(self, controller, app, dialogs, file_dialog, tmp_path):
        path = _make_media(tmp_path)
        file_dialog["path"] = path

        controller.load_video(app, None, splash_screen=FakeLoader())

        assert app.video_path == path

    def test_missing_audio_track_is_retried(self, controller, app, dialogs, tmp_path):
        app.player = FakePlayer(audio_track=-1)

        controller.load_video(app, _make_media(tmp_path), splash_screen=FakeLoader())

        assert app.volumes == [80]

    def test_loading_failure_is_logged_and_reported(self, controller, app, dialogs, tmp_path):
        loader = FakeLoader()

        def _boom(path):
            raise RuntimeError("vlc exploded")

        app.player.set_media = _boom

        controller.load_video(app, _make_media(tmp_path), splash_screen=loader)

        assert app.exceptions[0][0] == "main.load_video"
        assert loader.closed is True
        assert app.status_label.text() == "Status: Load failed"
        assert app.file_loading_service.finished_with == [True]
