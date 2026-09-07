"""Unit tests for source_code/services/player_service.py"""

import sys
import time
from unittest.mock import MagicMock

import pytest
import vlc

from source_code.services import player_service as player_service_module
from source_code.services.player_service import PlayerService, _configure_vlc_runtime_windows


@pytest.fixture
def service(qapp):
    player = PlayerService()
    player._instance = MagicMock(name="instance")
    player._player = MagicMock(name="player")
    return player


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(time, "sleep", lambda *_: None)


class TestVlcRuntimeBootstrap:
    def test_non_windows_platforms_are_skipped(self, monkeypatch):
        monkeypatch.setattr(player_service_module.os.environ, "setdefault", lambda *a: pytest.fail("touched env"))

        _configure_vlc_runtime_windows()

    def test_windows_without_runtime_files_leaves_env_untouched(self, monkeypatch):
        monkeypatch.setattr(player_service_module.sys, "platform", "win32")
        before = dict(player_service_module.os.environ)

        _configure_vlc_runtime_windows()

        assert dict(player_service_module.os.environ) == before


class TestEventWiring:
    def test_vlc_events_are_attached_on_construction(self, qapp):
        service = PlayerService()

        attached = {call.args[0] for call in service._event_manager.event_attach.call_args_list}
        assert attached == {
            vlc.EventType.MediaPlayerTimeChanged,
            vlc.EventType.MediaPlayerPositionChanged,
            vlc.EventType.MediaPlayerPlaying,
            vlc.EventType.MediaPlayerPaused,
            vlc.EventType.MediaPlayerStopped,
            vlc.EventType.MediaPlayerEndReached,
        }

    def test_time_and_position_handlers_emit_player_values(self, service):
        service._player.get_time.return_value = 4200
        service._player.get_position.return_value = 0.42
        times, positions = [], []
        service.time_changed.connect(times.append)
        service.position_changed.connect(positions.append)

        service._handle_time_changed(None)
        service._handle_position_changed(None)

        assert times == [4200]
        assert positions == [pytest.approx(0.42)]

    def test_state_handlers_emit_matching_signals(self, service):
        events = []
        service.playback_started.connect(lambda: events.append("started"))
        service.playback_paused.connect(lambda: events.append("paused"))
        service.playback_stopped.connect(lambda: events.append("stopped"))

        service._handle_playing(None)
        service._handle_paused(None)
        service._handle_stopped(None)
        service._handle_end_reached(None)

        assert events == ["started", "paused", "stopped", "stopped"]


class TestMediaLifecycle:
    def test_set_media_binds_new_media_and_emits(self, service):
        service._instance.media_new.return_value = "media-handle"
        service._stopped = True
        emitted = []
        service.media_changed.connect(emitted.append)

        service.set_media("/media/song.mp4")

        service._instance.media_new.assert_called_once_with("/media/song.mp4")
        service._player.set_media.assert_called_once_with("media-handle")
        assert service._stopped is False
        assert emitted == ["/media/song.mp4"]

    def test_set_media_replaces_previous_media(self, service):
        service._media = "old"
        service._instance.media_new.return_value = "new"

        service.set_media("/media/other.mp4")

        assert service._media == "new"

    def test_clear_media_releases_reference_and_marks_stopped(self, service):
        service._media = "media-handle"

        service.clear_media()

        service._player.set_media.assert_called_once_with(None)
        assert service._media is None
        assert service._stopped is True

    def test_clear_media_tolerates_unsupported_set_media(self, service):
        service._player.set_media.side_effect = RuntimeError("unsupported")

        service.clear_media()

        assert service._stopped is True

    def test_has_media_uses_player_binding(self, service):
        service._player.get_media.return_value = "media-handle"

        assert service.has_media() is True

    def test_has_media_falls_back_to_local_reference(self, service):
        service._player.get_media.side_effect = RuntimeError("no binding")
        service._media = "media-handle"

        assert service.has_media() is True

    def test_has_media_is_false_when_nothing_is_loaded(self, service):
        service._player.get_media.return_value = None
        service._media = None

        assert service.has_media() is False


class TestPlaybackControls:
    def test_play_clears_stopped_flag(self, service):
        service._player.play.return_value = 0
        service._stopped = True

        service.play()

        assert service._stopped is False
        service._player.play.assert_called_once_with()

    def test_play_reattaches_detached_video_widget(self, service, monkeypatch):
        monkeypatch.setattr(player_service_module.sys, "platform", "linux")
        service._video_widget_id = 1234
        service._video_widget_detached = True
        service._player.play.return_value = 0

        service.play()

        service._player.set_xwindow.assert_called_once_with(1234)
        assert service._video_widget_detached is False

    def test_play_reports_vlc_failure(self, service):
        service._player.play.return_value = -1

        service.play()

        assert service._stopped is False

    def test_pause_delegates_to_player(self, service):
        service.pause()

        service._player.pause.assert_called_once_with()

    def test_pause_without_player_is_noop(self, service):
        service._player = None

        service.pause()

    def test_stop_rewinds_detaches_and_restores_mute(self, service):
        service._player.audio_get_mute.return_value = True
        service._video_widget_id = 99

        service.stop()

        service._player.set_time.assert_any_call(0)
        service._player.set_position.assert_any_call(0.0)
        service._player.audio_set_mute.assert_any_call(True)
        assert service._video_widget_detached is True
        assert service._media is None
        assert service._stopped is True

    def test_stop_survives_player_errors(self, service):
        service._player.pause.side_effect = RuntimeError("vlc gone")

        service.stop()

        assert service._stopped is False


class TestVideoWidget:
    @pytest.mark.parametrize(
        "platform, setter",
        [("linux", "set_xwindow"), ("win32", "set_hwnd"), ("darwin", "set_nsobject")],
    )
    def test_video_widget_is_bound_per_platform(self, service, monkeypatch, platform, setter):
        monkeypatch.setattr(player_service_module.sys, "platform", platform)

        service.set_video_widget(4321)

        getattr(service._player, setter).assert_called_once_with(4321)
        assert service._video_widget_detached is False

    def test_unsupported_platform_does_not_bind(self, service, monkeypatch):
        monkeypatch.setattr(player_service_module.sys, "platform", "sunos")

        service.set_video_widget(4321)

        service._player.set_xwindow.assert_not_called()
        assert service._video_widget_id == 4321

    @pytest.mark.parametrize(
        "platform, setter",
        [("linux", "set_xwindow"), ("win32", "set_hwnd"), ("darwin", "set_nsobject")],
    )
    def test_detach_clears_output_per_platform(self, service, monkeypatch, platform, setter):
        monkeypatch.setattr(player_service_module.sys, "platform", platform)
        service._video_widget_id = 4321

        service.detach_video_widget()

        getattr(service._player, setter).assert_called_once_with(0)
        assert service._video_widget_detached is True

    def test_detach_without_widget_is_noop(self, service):
        service.detach_video_widget()

        assert service._video_widget_detached is False

    def test_detach_marks_detached_even_when_vlc_errors(self, service, monkeypatch):
        monkeypatch.setattr(player_service_module.sys, "platform", "linux")
        service._video_widget_id = 4321
        service._player.set_xwindow.side_effect = RuntimeError("vlc gone")

        service.detach_video_widget()

        assert service._video_widget_detached is True


class TestPassthroughAccessors:
    def test_time_and_position_accessors(self, service):
        service._player.get_time.return_value = 1000
        service._player.get_length.return_value = 60000
        service._player.get_position.return_value = 0.5

        assert service.get_time() == 1000
        assert service.get_length() == 60000
        assert service.get_position() == pytest.approx(0.5)

        service.set_time(2000)
        service.set_position(0.75)
        service.set_rate(1.5)

        service._player.set_time.assert_called_once_with(2000)
        service._player.set_position.assert_called_once_with(0.75)
        service._player.set_rate.assert_called_once_with(1.5)

    def test_is_playing_delegates_to_player(self, service):
        service._player.is_playing.return_value = True

        assert service.is_playing() is True

    def test_set_volume_emits_change(self, service):
        emitted = []
        service.volume_changed.connect(emitted.append)

        service.set_volume(70)

        service._player.audio_set_volume.assert_called_once_with(70)
        assert emitted == [70]

    def test_volume_and_mute_accessors(self, service):
        service._player.audio_get_volume.return_value = 55
        service._player.audio_get_mute.return_value = False
        service._player.audio_get_track.return_value = 2

        assert service.get_volume() == 55
        assert service.get_mute() is False
        assert service.get_audio_track() == 2

        service.set_mute(True)
        service._player.audio_set_mute.assert_called_once_with(True)


class TestStateQueries:
    def test_get_state_returns_player_state(self, service):
        service._player.get_state.return_value = vlc.State.Playing

        assert service.get_state() == vlc.State.Playing

    def test_get_state_returns_none_on_error(self, service):
        service._player.get_state.side_effect = RuntimeError("vlc gone")

        assert service.get_state() is None

    def test_is_ended_detects_end_state(self, service):
        service._player.get_state.return_value = vlc.State.Ended

        assert service.is_ended() is True

    def test_is_ended_is_false_on_error(self, service):
        service._player.get_state.side_effect = RuntimeError("vlc gone")

        assert service.is_ended() is False

    @pytest.mark.parametrize("state", [vlc.State.Playing, vlc.State.Paused])
    def test_active_states(self, service, state):
        service._player.get_state.return_value = state

        assert service.is_active() is True

    @pytest.mark.parametrize("state", [vlc.State.Stopped, vlc.State.Ended, vlc.State.NothingSpecial])
    def test_inactive_states(self, service, state):
        service._player.get_state.return_value = state

        assert service.is_active() is False

    def test_stopped_flag_short_circuits_active_check(self, service):
        service._stopped = True
        service._player.get_state.return_value = vlc.State.Playing

        assert service.is_active() is False


class TestRelease:
    def test_release_detaches_events_and_frees_resources(self, service):
        event_manager = MagicMock(name="event_manager")
        service._event_manager = event_manager

        service.release()

        assert event_manager.event_detach.call_count == 6
        service._player.release.assert_called_once_with()
        service._instance.release.assert_called_once_with()

    def test_release_tolerates_failures_at_every_step(self, service):
        service._event_manager = MagicMock()
        service._event_manager.event_detach.side_effect = RuntimeError("gone")
        service._player.release.side_effect = RuntimeError("gone")
        service._instance.release.side_effect = RuntimeError("gone")

        service.release()


class TestVideoSpeedCommand:
    def test_slow_motion_stretches_presentation_timestamps(self, service):
        cmd = service.get_video_speed_adjustment_command("/usr/bin/ffmpeg", "in.mp4", "out.mp4", 0.5)

        assert cmd[cmd.index("-filter_complex") + 1] == "[0:v]setpts=2.0*PTS[v];[0:a]atempo=1.0[a]"
        assert cmd[:2] == ["/usr/bin/ffmpeg", "-y"]
        assert cmd[-1] == "out.mp4"

    def test_speed_up_compresses_presentation_timestamps(self, service):
        cmd = service.get_video_speed_adjustment_command("/usr/bin/ffmpeg", "in.mp4", "out.mp4", 2.0)

        assert "setpts=0.5*PTS[v]" in cmd[cmd.index("-filter_complex") + 1]
        assert cmd.count("-map") == 2


def test_module_imports_stubbed_vlc():
    assert sys.modules["vlc"] is vlc
