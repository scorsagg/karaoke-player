"""Unit tests for source_code/services/file_loading_service.py"""

import pytest

from source_code.services import file_loading_service as fls_module
from source_code.services.file_loading_service import FileLoadingService


class FakeAudioService:
    def __init__(self, was_playing=True):
        self.was_playing = was_playing
        self.calls = []

    def disconnect_audio_signals(self):
        self.calls.append("disconnect")

    def reconnect_audio_signals(self):
        self.calls.append("reconnect")

    def pause_analyzer(self):
        self.calls.append("pause_analyzer")
        return self.was_playing

    def resume_analyzer(self):
        self.calls.append("resume_analyzer")


class FakePlayerService:
    def __init__(self, active=False, playing=False):
        self.active = active
        self.playing = playing
        self._media = "old-media"
        self.calls = []

    def is_active(self):
        return self.active

    def is_playing(self):
        return self.playing

    def pause(self):
        self.calls.append("pause")
        self.playing = False


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(fls_module.time, "sleep", lambda *_: None)


@pytest.fixture
def audio_service():
    return FakeAudioService()


class TestPrepareForLoading:
    def test_idle_player_only_pauses_analyzer(self, audio_service):
        player = FakePlayerService(active=False)
        service = FileLoadingService(audio_service, player)

        assert service.prepare_for_loading() is True
        assert audio_service.calls == ["disconnect", "pause_analyzer"]
        assert player.calls == []
        assert service.is_currently_loading() is True

    def test_active_paused_player_is_not_paused_again(self, audio_service):
        player = FakePlayerService(active=True, playing=False)
        service = FileLoadingService(audio_service, player)

        service.prepare_for_loading()

        assert player.calls == []
        assert player._media is None

    def test_playing_player_is_paused_and_media_released(self, audio_service):
        player = FakePlayerService(active=True, playing=True)
        service = FileLoadingService(audio_service, player)

        service.prepare_for_loading()

        assert player.calls == ["pause"]
        assert player._media is None
        assert audio_service.calls == ["disconnect", "pause_analyzer"]

    def test_reports_analyzer_idle_state(self):
        audio_service = FakeAudioService(was_playing=False)
        service = FileLoadingService(audio_service, FakePlayerService())

        assert service.prepare_for_loading() is False

    def test_overlapping_load_is_rejected(self, audio_service):
        service = FileLoadingService(audio_service, FakePlayerService())
        service.is_loading = True

        assert service.prepare_for_loading() is False
        assert audio_service.calls == []


class TestFinishLoading:
    def test_resumes_analyzer_and_clears_loading_flag(self, audio_service, qapp):
        service = FileLoadingService(audio_service, FakePlayerService())
        service.is_loading = True

        service.finish_loading(resume_audio=True)

        assert audio_service.calls == ["resume_analyzer", "reconnect"]
        assert service.is_currently_loading() is False

    def test_can_skip_analyzer_resume(self, audio_service, qapp):
        service = FileLoadingService(audio_service, FakePlayerService())

        service.finish_loading(resume_audio=False)

        assert audio_service.calls == ["reconnect"]
        assert service.is_currently_loading() is False


class TestSafeLoadVideo:
    def test_runs_callback_between_prepare_and_finish(self, audio_service, qapp):
        service = FileLoadingService(audio_service, FakePlayerService())
        loaded = []

        assert service.safe_load_video(loaded.append, "/media/song.mp4") is True
        assert loaded == ["/media/song.mp4"]
        assert audio_service.calls == ["disconnect", "pause_analyzer", "resume_analyzer", "reconnect"]

    def test_skips_resume_when_analyzer_was_idle(self, qapp):
        audio_service = FakeAudioService(was_playing=False)
        service = FileLoadingService(audio_service, FakePlayerService())

        service.safe_load_video(lambda path: None, "/media/song.mp4")

        assert "resume_analyzer" not in audio_service.calls

    def test_callback_failure_clears_loading_flag(self, audio_service, qapp):
        service = FileLoadingService(audio_service, FakePlayerService())

        def _boom(path):
            raise RuntimeError("load failed")

        assert service.safe_load_video(_boom, "/media/song.mp4") is False
        assert service.is_currently_loading() is False
        assert "reconnect" not in audio_service.calls
