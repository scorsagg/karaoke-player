"""Unit tests for source_code/services/realtime_pitch_service.py"""

import threading

import pytest

from source_code.services.realtime_pitch_service import RealtimePitchService


@pytest.fixture
def service():
    return RealtimePitchService(ffmpeg_path="/usr/bin/ffmpeg")


class TestDefaultsAndSetters:
    def test_defaults(self, service):
        assert service.ffmpeg_path == "/usr/bin/ffmpeg"
        assert service.current_path == ""
        assert service.pitch_semitones == 0.0
        assert service.playback_speed == 1.0
        assert service.gain_factor == 1.0
        assert service.is_active() is False

    def test_load_file_records_path(self, service):
        service.load_file("/media/song.mp3")

        assert service.current_path == "/media/song.mp3"

    def test_set_pitch_coerces_to_float(self, service):
        service.set_pitch(3)

        assert service.pitch_semitones == 3.0

    @pytest.mark.parametrize("value, expected", [(1.5, 1.5), (0.1, 0.5), (5.0, 2.0), ("1.25", 1.25)])
    def test_set_speed_clamps_to_supported_range(self, service, value, expected):
        service.set_speed(value)

        assert service.playback_speed == pytest.approx(expected)

    def test_set_speed_falls_back_on_invalid_input(self, service):
        service.set_speed("fast")

        assert service.playback_speed == 1.0

    @pytest.mark.parametrize("value, expected", [(2.0, 2.0), (0.0, 0.01), (50.0, 10.0), ("3", 3.0)])
    def test_set_gain_clamps_to_supported_range(self, service, value, expected):
        service.set_gain(value)

        assert service.gain_factor == pytest.approx(expected)

    def test_set_gain_falls_back_on_invalid_input(self, service):
        service.set_gain(None)

        assert service.gain_factor == 1.0


class TestAtempoChain:
    def test_in_range_value_is_single_filter(self, service):
        assert service._build_atempo_chain(1.25) == "atempo=1.250000"

    def test_fast_value_is_split_into_multiple_filters(self, service):
        assert service._build_atempo_chain(4.0) == "atempo=2.000000,atempo=2.000000"

    def test_slow_value_is_split_into_multiple_filters(self, service):
        assert service._build_atempo_chain(0.25) == "atempo=0.500000,atempo=0.500000"

    def test_non_power_of_two_fast_value(self, service):
        assert service._build_atempo_chain(3.0) == "atempo=2.000000,atempo=1.500000"

    def test_zero_is_clamped_to_minimum(self, service):
        chain = service._build_atempo_chain(0.0)

        assert chain.startswith("atempo=0.500000")
        assert chain.endswith("atempo=0.640000")


class TestPlaybackLifecycle:
    def test_play_without_loaded_file_raises(self, service):
        with pytest.raises(ValueError, match="No media file loaded"):
            service.play_shifted()

    def test_play_starts_worker_thread_and_marks_active(self, service, monkeypatch):
        started = {}

        def fake_worker():
            started["ran"] = True

        monkeypatch.setattr(service, "_play_worker", fake_worker)
        service.load_file("/media/song.mp3")

        service.play_shifted(start_seconds=12.5)

        assert service._start_seconds == 12.5
        assert isinstance(service._play_thread, threading.Thread)
        service._play_thread.join(timeout=2)
        assert started.get("ran") is True

    def test_negative_start_is_clamped_to_zero(self, service, monkeypatch):
        monkeypatch.setattr(service, "_play_worker", lambda: None)
        service.load_file("/media/song.mp3")

        service.play_shifted(start_seconds=-5)

        assert service._start_seconds == 0.0
        service._play_thread.join(timeout=2)

    def test_none_start_is_treated_as_zero(self, service, monkeypatch):
        monkeypatch.setattr(service, "_play_worker", lambda: None)
        service.load_file("/media/song.mp3")

        service.play_shifted(start_seconds=None)

        assert service._start_seconds == 0.0
        service._play_thread.join(timeout=2)

    def test_stop_kills_ffmpeg_process_and_clears_state(self, service):
        class FakeProc:
            def __init__(self):
                self.killed = False

            def kill(self):
                self.killed = True

        proc = FakeProc()
        service._ffmpeg_proc = proc
        service._active = True

        service.stop()

        assert proc.killed is True
        assert service._ffmpeg_proc is None
        assert service.is_active() is False
        assert service._stop_event.is_set()

    def test_stop_ignores_kill_failures(self, service):
        class BrokenProc:
            def kill(self):
                raise RuntimeError("already dead")

        service._ffmpeg_proc = BrokenProc()

        service.stop()

        assert service._ffmpeg_proc is None

    def test_stop_joins_running_worker_thread(self, service):
        release = threading.Event()

        def worker():
            release.wait(timeout=2)

        service._play_thread = threading.Thread(target=worker, daemon=True)
        service._play_thread.start()
        release.set()

        service.stop()

        assert service._play_thread is None

    def test_stop_is_idempotent(self, service):
        service.stop()
        service.stop()

        assert service.is_active() is False


class TestPlayWorker:
    def test_missing_sounddevice_disables_playback(self, service, monkeypatch):
        import sys

        monkeypatch.setitem(sys.modules, "sounddevice", None)
        service.load_file("/media/song.mp3")
        service._active = True

        service._play_worker()

        assert service.is_active() is False

    def test_ffmpeg_launch_failure_disables_playback(self, service, monkeypatch):
        import source_code.services.realtime_pitch_service as module

        def _boom(*args, **kwargs):
            raise OSError("ffmpeg not found")

        monkeypatch.setattr(module.subprocess, "Popen", _boom)
        service.load_file("/media/song.mp3")
        service._active = True

        service._play_worker()

        assert service.is_active() is False
        assert service._ffmpeg_proc is None

    def test_worker_builds_expected_ffmpeg_command(self, service, monkeypatch):
        import source_code.services.realtime_pitch_service as module

        captured = {}

        def fake_popen(cmd, **kwargs):
            captured["cmd"] = cmd
            raise OSError("stop here")

        monkeypatch.setattr(module.subprocess, "Popen", fake_popen)
        service.load_file("/media/song.mp3")
        service.set_pitch(12)
        service.set_speed(1.5)
        service.set_gain(2.0)
        service._start_seconds = 3.0

        service._play_worker()

        cmd = captured["cmd"]
        assert cmd[0] == "/usr/bin/ffmpeg"
        assert cmd[cmd.index("-i") + 1] == "/media/song.mp3"
        assert cmd[cmd.index("-ss") + 1] == "3.000"
        audio_filter = cmd[cmd.index("-af") + 1]
        assert "rubberband=pitch=2.00000000:tempo=1.50000000" in audio_filter
        assert "volume=2.0000" in audio_filter
        assert "alimiter=limit=0.98:attack=5:release=50" in audio_filter
        assert cmd[-1] == "pipe:1"

    def test_worker_omits_gain_filters_at_unity_gain(self, service, monkeypatch):
        import source_code.services.realtime_pitch_service as module

        captured = {}

        def fake_popen(cmd, **kwargs):
            captured["cmd"] = cmd
            raise OSError("stop here")

        monkeypatch.setattr(module.subprocess, "Popen", fake_popen)
        service.load_file("/media/song.mp3")

        service._play_worker()

        audio_filter = captured["cmd"][captured["cmd"].index("-af") + 1]
        assert audio_filter == "rubberband=pitch=1.00000000:tempo=1.00000000"

    def test_worker_uses_limiter_only_when_boosting(self, service, monkeypatch):
        import source_code.services.realtime_pitch_service as module

        captured = {}

        def fake_popen(cmd, **kwargs):
            captured["cmd"] = cmd
            raise OSError("stop here")

        monkeypatch.setattr(module.subprocess, "Popen", fake_popen)
        service.load_file("/media/song.mp3")
        service.set_gain(0.5)

        service._play_worker()

        audio_filter = captured["cmd"][captured["cmd"].index("-af") + 1]
        assert "volume=0.5000" in audio_filter
        assert "alimiter" not in audio_filter

    def test_output_stream_failure_disables_playback(self, service, monkeypatch):
        import sounddevice

        import source_code.services.realtime_pitch_service as module

        class FakeProc:
            def poll(self):
                return None

            def kill(self):
                pass

        monkeypatch.setattr(module.subprocess, "Popen", lambda cmd, **kwargs: FakeProc())

        def _boom(*args, **kwargs):
            raise RuntimeError("no output device")

        monkeypatch.setattr(sounddevice, "OutputStream", _boom, raising=False)
        service.load_file("/media/song.mp3")

        service._play_worker()

        assert service.is_active() is False
