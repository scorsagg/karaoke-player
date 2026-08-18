"""Unit tests for the UI builder modules under source_code/ui."""

import pytest
from PySide6.QtWidgets import QScrollArea, QStackedWidget

from source_code.ui.audio_studio_page import create_audio_studio_page
from source_code.ui.convert_export_page import create_convert_export_page
from source_code.ui.main_layout import create_main_layout
from source_code.ui.media_loader_page import create_download_page, create_media_loader_page
from source_code.ui.pitch_page import create_pitch_page
from source_code.ui.playback_bar import create_playback_bar
from source_code.ui.sidebar import create_sidebar
from source_code.ui.video_tools_page import create_video_tools_page


class TestSidebar:
    @pytest.fixture
    def sidebar(self, qapp):
        return create_sidebar(None)

    def test_navigation_entries(self, sidebar):
        nav = sidebar["nav_list"]

        assert [nav.item(i).text() for i in range(nav.count())] == ["📥 Media Loader", "▶ Playback"]

    def test_collapsible_sections_start_hidden(self, sidebar):
        assert sidebar["extra_tools_container"].isVisible() is False
        assert sidebar["history_container"].isVisible() is False

    def test_status_starts_ready(self, sidebar):
        assert sidebar["status_label"].text() == "Status: Ready"

    def test_studio_buttons_are_exposed(self, sidebar):
        assert {"video_tools_btn", "audio_tools_btn", "convert_export_btn"} <= set(sidebar)


class TestPlaybackBar:
    @pytest.fixture
    def bar(self, qapp):
        return create_playback_bar({"measurement_mode": "SPL Estimate (Room)"})

    def test_transport_controls_exist(self, bar):
        assert bar["play_btn"].text() == "▶ Play"
        assert bar["pause_btn"].text() == "⏸ Pause"
        assert bar["stop_btn"].text() == "⏹ Stop"

    def test_seek_slider_uses_permille_range(self, bar):
        assert (bar["seek_slider"].minimum(), bar["seek_slider"].maximum()) == (0, 1000)

    def test_volume_defaults_to_eighty_percent(self, bar):
        assert bar["vol_slider"].value() == 80
        assert bar["vol_label"].text() == "80%"

    def test_meter_starts_silent_in_configured_mode(self, bar):
        meter = bar["audio_level_meter"]

        assert meter.db_level == -80.0
        assert meter.level_percent == 0.0
        assert meter.measurement_mode == "SPL Estimate (Room)"

    def test_meter_falls_back_to_dbfs_mode(self, qapp):
        bar = create_playback_bar({})

        assert bar["audio_level_meter"].measurement_mode == "dB Output (dBFS)"


class TestMediaLoaderPage:
    @pytest.fixture
    def page(self, qapp):
        return create_media_loader_page()

    def test_load_and_download_controls(self, page):
        assert page["load_btn"].text() == "📂 Open File..."
        assert page["dl_btn"].text() == "Download and Load"

    def test_url_input_starts_empty_with_hint(self, page):
        assert page["url_input"].text() == ""
        assert "stream links" in page["url_input"].placeholderText()

    def test_legacy_alias_builds_the_same_page(self, qapp):
        assert set(create_download_page()) == {"page", "load_btn", "url_input", "dl_btn"}


class TestPitchPage:
    @pytest.fixture
    def page(self, qapp):
        return create_pitch_page()

    def test_pitch_and_speed_controls_exist(self, page):
        assert {"pitch_minus", "pitch_input", "pitch_plus", "pitch_reset"} <= set(page)
        assert {"speed_minus", "speed_input", "speed_plus", "speed_reset"} <= set(page)

    def test_realtime_toggle_starts_disabled(self, page):
        assert page["realtime_pitch_toggle"].isChecked() is False


class TestAudioStudioPage:
    @pytest.fixture
    def page(self, qapp):
        return create_audio_studio_page()

    def test_tabs_are_created(self, page):
        assert page["tabs"].count() > 0

    def test_trim_and_playback_window_sections_exist(self, page):
        assert {"trim_ranges_container", "trim_add_range", "trim_btn"} <= set(page)
        assert {"pw_ranges_container", "pw_add_range", "pw_apply_btn"} <= set(page)

    def test_add_range_helper_appends_a_row(self, page):
        container = page["trim_ranges_container"]
        before = container.layout().count()

        page["trim_add_range"](0, 30)

        assert container.layout().count() == before + 1


class TestVideoToolsPage:
    @pytest.fixture
    def page(self, qapp):
        return create_video_tools_page()

    def test_tool_tabs_are_created(self, page):
        assert page["tabs"].count() > 0

    def test_extraction_and_widen_controls_exist(self, page):
        assert {"extract_btn", "extract_format_combo", "extract_status_label"} <= set(page)
        assert {"widen_crop_y_spin", "widen_exec_btn"} <= set(page)

    def test_playback_window_add_range_helper_appends_a_row(self, page):
        container = page["pw_ranges_container"]
        before = container.layout().count()

        page["pw_add_range"](5, 25)

        assert container.layout().count() == before + 1


class TestConvertExportPage:
    @pytest.fixture
    def page(self, qapp):
        return create_convert_export_page()

    def test_conversion_controls_exist(self, page):
        assert {"convert_source_combo", "convert_target_combo", "convert_quality_combo"} <= set(page)

    def test_vocal_separation_controls_exist(self, page):
        assert {"vocal_model_combo", "vocal_target_combo", "vocal_output_format_combo"} <= set(page)
        assert page["vocal_fast_cb"].isChecked() is False

    def test_merge_and_amplify_controls_exist(self, page):
        assert {"merge_input_a_btn", "merge_input_b_btn", "merge_execute_btn"} <= set(page)
        assert {"amp_factor_spin", "amp_live_btn", "amp_btn"} <= set(page)


class TestMainLayout:
    @pytest.fixture
    def layout(self, qapp):
        return create_main_layout({"measurement_mode": "dB Output (dBFS)"})

    def test_all_component_groups_are_returned(self, layout):
        components = layout["components"]

        assert {
            "sidebar_components",
            "video_frame",
            "filename_label",
            "playback_components",
            "media_loader_page_components",
            "pitch_page_components",
            "audio_tools_page_components",
            "video_tools_page_components",
            "convert_export_page_components",
            "stack",
        } <= set(components)

    def test_stack_holds_one_entry_per_page(self, layout):
        stack = layout["components"]["stack"]

        assert isinstance(stack, QStackedWidget)
        assert stack.count() == 5

    def test_scrollable_pages_are_wrapped_in_resizable_scroll_areas(self, layout):
        stack = layout["components"]["stack"]

        for index in (2, 3, 4):
            widget = stack.widget(index)
            assert isinstance(widget, QScrollArea)
            assert widget.widgetResizable() is True

    def test_video_frame_and_filename_label_defaults(self, layout):
        components = layout["components"]

        assert components["video_frame"].minimumHeight() == 80
        assert components["filename_label"].text() == "No file loaded"

    def test_download_page_alias_points_at_the_media_loader_page(self, layout):
        components = layout["components"]

        assert components["download_page_components"] is components["media_loader_page_components"]

    def test_extra_page_components_mirror_the_audio_studio(self, layout):
        components = layout["components"]

        assert set(components["extra_page_components"]) == set(components["audio_tools_page_components"])
