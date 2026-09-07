"""Unit tests for source_code/controllers/navigation_controller.py"""

import pytest
from PySide6.QtCore import Qt

from source_code.controllers import navigation_controller as nav_module
from source_code.controllers.navigation_controller import NavigationController

PAGE_PLAYBACK = 0
PAGE_MEDIA_LOADER = 1
PAGE_AUDIO_STUDIO = 2
PAGE_VIDEO_STUDIO = 3
PAGE_CONVERT_EXPORT = 4


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


class FakeNavList:
    def __init__(self):
        self.signals_blocked = []
        self.current_row = 0
        self.cleared = False

    def blockSignals(self, flag):
        self.signals_blocked.append(flag)

    def clearSelection(self):
        self.cleared = True

    def setCurrentRow(self, row):
        self.current_row = row


class FakeFrame:
    def __init__(self):
        self.min_height = None
        self.max_height = None
        self.geometry_updates = 0

    def setMinimumHeight(self, value):
        self.min_height = value

    def setMaximumHeight(self, value):
        self.max_height = value

    def updateGeometry(self):
        self.geometry_updates += 1


class FakeButton:
    def __init__(self):
        self.visible = None

    def setVisible(self, flag):
        self.visible = flag


class FakeTabs:
    def __init__(self, index=0):
        self.index = index
        self.signals_blocked = []

    def currentIndex(self):
        return self.index

    def setCurrentIndex(self, index):
        self.index = index

    def blockSignals(self, flag):
        self.signals_blocked.append(flag)


class FakeScroll:
    def __init__(self):
        self.policy = None

    def setVerticalScrollBarPolicy(self, policy):
        self.policy = policy


class FakeLayout:
    def __init__(self):
        self.invalidated = 0
        self.activated = 0

    def invalidate(self):
        self.invalidated += 1

    def activate(self):
        self.activated += 1


class FakeStack:
    def __init__(self):
        self.index = None

    def setCurrentIndex(self, index):
        self.index = index


class FakeApp:
    PAGE_PLAYBACK = PAGE_PLAYBACK
    PAGE_MEDIA_LOADER = PAGE_MEDIA_LOADER
    PAGE_AUDIO_STUDIO = PAGE_AUDIO_STUDIO
    PAGE_VIDEO_STUDIO = PAGE_VIDEO_STUDIO
    PAGE_CONVERT_EXPORT = PAGE_CONVERT_EXPORT

    def __init__(self, **overrides):
        self.video_path = ""
        self.media_type = "unknown"
        self.realtime_pitch_enabled = False
        self.nav_list = FakeNavList()
        self.video_frame = FakeFrame()
        self.fullscreen_btn = FakeButton()
        self.stack = FakeStack()
        self.convert_export_tabs = FakeTabs()
        self.video_tools_tabs = FakeTabs()
        self.video_tools_scroll = FakeScroll()
        self.video_current_file_label = FakeLabel()
        self.widen_current_file_label = FakeLabel()
        self.amp_status_label = FakeLabel()
        self._live_amp_preview_active = False
        self._current_is_audio_only = False
        self._last_non_amplify_convert_export_tab_index = 0
        self.active_window_pages = []
        self.extraction_ui_calls = []
        self.refresh_targets_calls = 0
        self.pitch_status_refreshes = 0
        self.visualization_calls = 0
        self._layout = FakeLayout()
        for key, value in overrides.items():
            setattr(self, key, value)

    def classify_media_type(self, path):
        return self.media_type

    def _is_realtime_pitch_enabled(self):
        return self.realtime_pitch_enabled

    def _set_active_playback_window_controls(self, idx):
        self.active_window_pages.append(idx)

    def update_extraction_ui(self, flag):
        self.extraction_ui_calls.append(flag)

    def refresh_conversion_targets(self):
        self.refresh_targets_calls += 1

    def _refresh_realtime_pitch_status(self):
        self.pitch_status_refreshes += 1

    def show_audio_visualization(self):
        self.visualization_calls += 1

    def layout(self):
        return self._layout


@pytest.fixture
def controller():
    return NavigationController()


@pytest.fixture
def dialogs(monkeypatch):
    """Capture QMessageBox.information calls instead of showing modal dialogs."""
    shown = []

    class FakeMessageBox:
        @staticmethod
        def information(parent, title, text):
            shown.append((title, text))

    monkeypatch.setattr(nav_module, "QMessageBox", FakeMessageBox)
    return shown


@pytest.fixture
def deferred_calls(monkeypatch):
    """Capture QTimer.singleShot callbacks so they can be run explicitly."""
    scheduled = []

    class FakeTimer:
        @staticmethod
        def singleShot(msec, callback):
            scheduled.append(callback)

    monkeypatch.setattr(nav_module, "QTimer", FakeTimer)
    return scheduled


class TestNavigationGuards:
    def test_video_media_blocks_audio_studio(self, controller, dialogs, deferred_calls):
        app = FakeApp(video_path="/media/song.mp4", media_type="video")

        controller.handle_navigation_change(app, PAGE_AUDIO_STUDIO)

        assert dialogs[0][0] == "Audio Studio Restricted"
        assert app.stack.index is None

    def test_audio_media_blocks_video_studio(self, controller, dialogs, deferred_calls):
        app = FakeApp(video_path="/media/song.mp3", media_type="audio")

        controller.handle_navigation_change(app, PAGE_VIDEO_STUDIO)

        assert dialogs[0][0] == "Video Studio Restricted"
        assert app.stack.index is None

    def test_unclassifiable_media_does_not_block_navigation(self, controller, dialogs, deferred_calls):
        app = FakeApp(video_path="/media/song.mp4")
        app.classify_media_type = lambda path: (_ for _ in ()).throw(RuntimeError("probe failed"))

        controller.handle_navigation_change(app, PAGE_AUDIO_STUDIO)

        assert dialogs == []
        assert app.stack.index == PAGE_AUDIO_STUDIO

    def test_live_amplify_preview_blocks_playback_page(self, controller, dialogs, deferred_calls):
        app = FakeApp(_live_amp_preview_active=True)

        controller.handle_navigation_change(app, PAGE_PLAYBACK)

        assert dialogs[0][0] == "Live Amplify Preview Active"
        assert "Stop Live Preview" in app.amp_status_label.text()
        assert app.stack.index is None

    def test_live_amplify_guard_without_status_label(self, controller, dialogs, deferred_calls):
        app = FakeApp(_live_amp_preview_active=True, amp_status_label=None)

        controller.handle_navigation_change(app, PAGE_PLAYBACK)

        assert app.stack.index is None

    def test_realtime_pitch_blocks_amplify_tab(self, controller, dialogs, deferred_calls):
        app = FakeApp(realtime_pitch_enabled=True, convert_export_tabs=FakeTabs(index=4))

        controller.handle_navigation_change(app, PAGE_CONVERT_EXPORT)

        assert dialogs[0][0] == "Real-time Pitch Active"
        assert app.pitch_status_refreshes == 1
        assert app.stack.index is None

    def test_realtime_pitch_allows_other_convert_tabs(self, controller, dialogs, deferred_calls):
        app = FakeApp(realtime_pitch_enabled=True, convert_export_tabs=FakeTabs(index=1))

        controller.handle_navigation_change(app, PAGE_CONVERT_EXPORT)

        assert dialogs == []
        assert app.stack.index == PAGE_CONVERT_EXPORT

    def test_missing_convert_tabs_defaults_to_first_tab(self, controller, dialogs, deferred_calls):
        app = FakeApp(realtime_pitch_enabled=True, convert_export_tabs=None)

        controller.handle_navigation_change(app, PAGE_CONVERT_EXPORT)

        assert app.stack.index == PAGE_CONVERT_EXPORT


class TestNavigationSelection:
    @pytest.mark.parametrize("idx", [PAGE_AUDIO_STUDIO, PAGE_VIDEO_STUDIO, PAGE_CONVERT_EXPORT])
    def test_studio_pages_clear_sidebar_selection(self, controller, dialogs, deferred_calls, idx):
        app = FakeApp()

        controller.handle_navigation_change(app, idx)

        assert app.nav_list.cleared is True
        assert app.nav_list.current_row == -1
        assert app.nav_list.signals_blocked == [True, False]

    def test_regular_pages_sync_sidebar_row(self, controller, dialogs, deferred_calls):
        app = FakeApp()

        controller.handle_navigation_change(app, PAGE_MEDIA_LOADER)

        assert app.nav_list.cleared is False
        assert app.nav_list.current_row == PAGE_MEDIA_LOADER

    def test_playback_window_controls_follow_page(self, controller, dialogs, deferred_calls):
        app = FakeApp()

        controller.handle_navigation_change(app, PAGE_MEDIA_LOADER)

        assert app.active_window_pages == [PAGE_MEDIA_LOADER]
        assert app._layout.invalidated == 1


class TestVideoFrameSizing:
    def test_audio_studio_with_audio_only_media_uses_short_frame(self, controller, dialogs, deferred_calls):
        app = FakeApp()

        controller.handle_navigation_change(app, PAGE_AUDIO_STUDIO, is_audio_only=True)

        assert (app.video_frame.min_height, app.video_frame.max_height) == (80, 100)
        assert app.fullscreen_btn.visible is False

    def test_audio_studio_with_video_media_allows_taller_frame(self, controller, dialogs, deferred_calls):
        app = FakeApp()

        controller.handle_navigation_change(app, PAGE_AUDIO_STUDIO, is_audio_only=False)

        assert (app.video_frame.min_height, app.video_frame.max_height) == (80, 220)

    def test_audio_only_flag_falls_back_to_app_state(self, controller, dialogs, deferred_calls):
        app = FakeApp(_current_is_audio_only=True)

        controller.handle_navigation_change(app, PAGE_AUDIO_STUDIO)

        assert app.video_frame.max_height == 100

    def test_convert_export_refreshes_targets(self, controller, dialogs, deferred_calls):
        app = FakeApp()

        controller.handle_navigation_change(app, PAGE_CONVERT_EXPORT)

        assert app.refresh_targets_calls == 1
        assert (app.video_frame.min_height, app.video_frame.max_height) == (80, 220)
        assert app.fullscreen_btn.visible is False

    def test_other_pages_use_full_height_frame(self, controller, dialogs, deferred_calls):
        app = FakeApp()

        controller.handle_navigation_change(app, PAGE_MEDIA_LOADER)

        assert (app.video_frame.min_height, app.video_frame.max_height) == (420, 16777215)
        assert app.fullscreen_btn.visible is True


class TestVideoStudioLabels:
    def test_loaded_media_is_shown_in_labels(self, controller, dialogs, deferred_calls):
        app = FakeApp(video_path="/media/song.mp4", media_type="video")

        controller.handle_navigation_change(app, PAGE_VIDEO_STUDIO)

        assert app.video_current_file_label.text() == "✅ Working on: song.mp4"
        assert app.widen_current_file_label.text() == "✅ Working on: song.mp4"
        assert app.extraction_ui_calls == [True]
        assert "#2ecc71" in app.video_current_file_label.styleSheet()

    def test_missing_media_shows_prompt(self, controller, dialogs, deferred_calls):
        app = FakeApp()

        controller.handle_navigation_change(app, PAGE_VIDEO_STUDIO)

        assert "No video loaded" in app.video_current_file_label.text()
        assert app.extraction_ui_calls == [False]
        assert "#e67e22" in app.widen_current_file_label.styleSheet()


class TestDeferredActivation:
    def test_deferred_callback_activates_layout(self, controller, dialogs, deferred_calls):
        app = FakeApp()

        controller.handle_navigation_change(app, PAGE_MEDIA_LOADER)
        deferred_calls[0]()

        assert app._layout.activated == 1
        assert app.visualization_calls == 0

    def test_deferred_callback_syncs_video_tools_tab(self, controller, dialogs, deferred_calls):
        app = FakeApp(video_tools_tabs=FakeTabs(index=2))

        controller.handle_navigation_change(app, PAGE_VIDEO_STUDIO)
        deferred_calls[0]()

        assert app.video_frame.max_height == 460

    def test_deferred_callback_shows_visualization_for_audio_only(self, controller, dialogs, deferred_calls):
        app = FakeApp(_current_is_audio_only=True)

        controller.handle_navigation_change(app, PAGE_MEDIA_LOADER)
        deferred_calls[0]()

        assert app.visualization_calls == 1

    def test_layoutless_window_is_tolerated(self, controller, dialogs, deferred_calls):
        app = FakeApp()
        app.layout = lambda: None

        controller.handle_navigation_change(app, PAGE_MEDIA_LOADER)
        deferred_calls[0]()

        assert app.stack.index == PAGE_MEDIA_LOADER


class TestVideoToolsTabChanged:
    @pytest.mark.parametrize("tab_idx", [2, 3])
    def test_preview_tabs_use_tall_frame_without_scrollbar(self, controller, tab_idx):
        app = FakeApp()

        controller._on_video_tools_tab_changed(app, tab_idx)

        assert (app.video_frame.min_height, app.video_frame.max_height) == (420, 460)
        assert app.video_tools_scroll.policy == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        assert app.fullscreen_btn.visible is True
        assert app.video_frame.geometry_updates == 1

    @pytest.mark.parametrize("tab_idx", [0, 1, 4])
    def test_other_tabs_use_short_frame_with_scrollbar(self, controller, tab_idx):
        app = FakeApp()

        controller._on_video_tools_tab_changed(app, tab_idx)

        assert (app.video_frame.min_height, app.video_frame.max_height) == (80, 160)
        assert app.video_tools_scroll.policy == Qt.ScrollBarPolicy.ScrollBarAsNeeded

    def test_missing_scroll_area_is_tolerated(self, controller):
        app = FakeApp(video_tools_scroll=None)

        controller._on_video_tools_tab_changed(app, 0)

        assert app.video_frame.min_height == 80


class TestConvertExportTabChanged:
    def test_amplify_tab_is_blocked_while_realtime_pitch_is_on(self, controller, dialogs):
        app = FakeApp(realtime_pitch_enabled=True, _last_non_amplify_convert_export_tab_index=2)
        app.convert_export_tabs = FakeTabs(index=4)

        controller._on_convert_export_tab_changed(app, 4)

        assert dialogs[0][0] == "Real-time Pitch Active"
        assert app.convert_export_tabs.index == 2
        assert app.convert_export_tabs.signals_blocked == [True, False]
        assert app.pitch_status_refreshes == 1

    def test_amplify_tab_block_without_tab_widget(self, controller, dialogs):
        app = FakeApp(realtime_pitch_enabled=True, convert_export_tabs=None)

        controller._on_convert_export_tab_changed(app, 4)

        assert app.pitch_status_refreshes == 1

    def test_amplify_tab_is_allowed_when_realtime_pitch_is_off(self, controller, dialogs):
        app = FakeApp()

        controller._on_convert_export_tab_changed(app, 4)

        assert dialogs == []
        assert app._last_non_amplify_convert_export_tab_index == 0

    def test_other_tabs_are_remembered(self, controller, dialogs):
        app = FakeApp()

        controller._on_convert_export_tab_changed(app, 3)

        assert app._last_non_amplify_convert_export_tab_index == 3
