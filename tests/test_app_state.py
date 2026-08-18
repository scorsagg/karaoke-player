"""Unit tests for source_code/models/app_state.py"""

from dataclasses import MISSING, fields

from source_code.models.app_state import AppState


class TestDefaults:
    def test_paths_default_to_empty_strings(self):
        state = AppState()

        assert state.video_path == ""
        assert state.audio_tools_file_path == ""
        assert state.merge_input_a_path == ""
        assert state.merge_input_b_path == ""

    def test_flags_default_to_false(self):
        state = AppState()

        assert state.is_video_fullscreen is False
        assert state._download_ui_busy is False
        assert state._download_from_audio_tools is False
        assert state._vocal_offline_dialog_shown is False
        assert state.auto_reduce_active is False
        assert state._player_was_active is False
        assert state._current_is_audio_only is False
        assert state._tonic_locked is False
        assert state.extra_tools_is_expanded is False
        assert state.history_is_expanded is False
        assert state._live_amp_preview_active is False

    def test_optional_fields_default_to_none(self):
        state = AppState()

        assert state.download_splash is None
        assert state.export_splash is None
        assert state._pending_seek_ratio is None
        assert state._smoothed_pitch_hz is None
        assert state._tonic_note_class is None
        assert state._realtime_pitch_apply_timer is None
        assert state._pre_amplify_base_volume is None

    def test_numeric_defaults(self):
        state = AppState()

        assert state._last_pitch_confidence == 0.0
        assert state._tonic_frames_collected == 0
        assert state._live_amplify_factor == 1.0
        assert state._live_amplify_step == 0
        assert state._last_non_amplify_convert_export_tab_index == 0

    def test_media_kind_defaults_to_unknown(self):
        state = AppState()

        assert state._current_export_media_kind == "unknown"
        assert state._last_merge_cmd_text == ""


class TestMutableDefaults:
    def test_dict_fields_are_not_shared_between_instances(self):
        first = AppState()
        second = AppState()

        first.active_tasks["export"] = object()
        first._tonic_note_counts[3] = 7

        assert second.active_tasks == {}
        assert second._tonic_note_counts == {}

    def test_dict_fields_use_default_factories(self):
        factory_fields = {
            field.name for field in fields(AppState) if field.default_factory is not MISSING
        }

        assert {"active_tasks", "_tonic_note_counts"} <= factory_fields


class TestConstruction:
    def test_fields_can_be_set_via_constructor(self):
        state = AppState(video_path="/media/song.mp4", auto_reduce_active=True, _live_amplify_factor=1.5)

        assert state.video_path == "/media/song.mp4"
        assert state.auto_reduce_active is True
        assert state._live_amplify_factor == 1.5

    def test_fields_are_mutable_at_runtime(self):
        state = AppState()

        state.video_path = "/media/other.mp4"
        state._pending_seek_ratio = 0.25

        assert state.video_path == "/media/other.mp4"
        assert state._pending_seek_ratio == 0.25
