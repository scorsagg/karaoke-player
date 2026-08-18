"""Unit tests for source_code/services/audio_service.py"""

import subprocess

import pytest

from source_code.services.audio_service import AudioService


class FakeAnalyzer:
    def __init__(self, is_playing=False, running=False, raise_on_stop=False):
        self.is_playing = is_playing
        self.running = running
        self.raise_on_stop = raise_on_stop
        self.stopped = False
        self.blocked = None
        self.waited = None

    def isRunning(self):
        return self.running

    def stop(self):
        if self.raise_on_stop:
            raise RuntimeError("stop failed")
        self.stopped = True
        self.running = False

    def set_playing(self, value):
        self.is_playing = value

    def blockSignals(self, value):
        self.blocked = value

    def wait(self, timeout):
        self.waited = timeout


class FakeMeter:
    def __init__(self):
        self.mode = None
        self.levels = []

    def set_measurement_mode(self, mode):
        self.mode = mode

    def update_level(self, db_value):
        self.levels.append(db_value)


class TestPauseAnalyzer:
    def test_stops_playing_analyzer_and_reports_previous_state(self):
        analyzer = FakeAnalyzer(is_playing=True)
        service = AudioService(analyzer, FakeMeter())

        assert service.pause_analyzer() is True
        assert analyzer.stopped is True

    def test_idle_analyzer_is_not_stopped(self):
        analyzer = FakeAnalyzer(is_playing=False)
        service = AudioService(analyzer, FakeMeter())

        assert service.pause_analyzer() is False
        assert analyzer.stopped is False

    def test_missing_analyzer_returns_false(self):
        assert AudioService(None, FakeMeter()).pause_analyzer() is False

    def test_analyzer_without_is_playing_attribute_returns_false(self):
        assert AudioService(object(), FakeMeter()).pause_analyzer() is False

    def test_stop_errors_are_swallowed(self):
        analyzer = FakeAnalyzer(is_playing=True, raise_on_stop=True)

        assert AudioService(analyzer, FakeMeter()).pause_analyzer() is True


class TestResumeAnalyzer:
    def test_running_analyzer_is_only_marked_playing(self):
        analyzer = FakeAnalyzer(running=True)
        service = AudioService(analyzer, FakeMeter())

        service.resume_analyzer()

        assert analyzer.is_playing is True
        assert service.audio_analyzer is analyzer

    def test_missing_analyzer_is_noop(self):
        service = AudioService(None, FakeMeter())

        service.resume_analyzer()

        assert service.audio_analyzer is None

    def test_stopped_analyzer_is_replaced_and_wired_to_handler(self, qapp):
        analyzer = FakeAnalyzer(running=False)
        meter = FakeMeter()
        levels = []
        replaced = []
        service = AudioService(analyzer, meter, level_update_handler=levels.append, analyzer_replaced_handler=replaced.append)

        service.resume_analyzer()

        new_thread = service.audio_analyzer
        assert new_thread is not analyzer
        assert replaced == [new_thread]
        assert new_thread.is_playing is True
        new_thread.level_updated.emit(-12.5)
        assert levels == [-12.5]
        assert meter.levels == []
        new_thread.stop()

    def test_stopped_analyzer_falls_back_to_meter_when_no_handler(self, qapp):
        meter = FakeMeter()
        service = AudioService(FakeAnalyzer(running=False), meter)

        service.resume_analyzer()

        service.audio_analyzer.level_updated.emit(-30.0)
        assert meter.levels == [-30.0]
        service.audio_analyzer.stop()

    def test_thread_creation_failure_keeps_previous_analyzer(self, monkeypatch):
        analyzer = FakeAnalyzer(running=False)
        service = AudioService(analyzer, FakeMeter())

        import source_code.workers.audio_analyzer as analyzer_module

        def _boom():
            raise RuntimeError("no audio device")

        monkeypatch.setattr(analyzer_module, "AudioAnalyzerThread", _boom)

        service.resume_analyzer()

        assert service.audio_analyzer is analyzer


class TestMonitoringToggles:
    def test_start_monitoring_marks_playing(self):
        analyzer = FakeAnalyzer()
        AudioService(analyzer, FakeMeter()).start_audio_monitoring()

        assert analyzer.is_playing is True

    def test_stop_monitoring_clears_playing(self):
        analyzer = FakeAnalyzer(is_playing=True)
        AudioService(analyzer, FakeMeter()).stop_audio_monitoring()

        assert analyzer.is_playing is False

    def test_monitoring_toggles_without_analyzer_are_noops(self):
        service = AudioService(None, FakeMeter())

        service.start_audio_monitoring()
        service.stop_audio_monitoring()

    def test_get_audio_analyzer_returns_current_instance(self):
        analyzer = FakeAnalyzer()

        assert AudioService(analyzer, FakeMeter()).get_audio_analyzer() is analyzer


class TestSignalBlocking:
    def test_disconnect_blocks_signals(self):
        analyzer = FakeAnalyzer()
        AudioService(analyzer, FakeMeter()).disconnect_audio_signals()

        assert analyzer.blocked is True

    def test_reconnect_unblocks_signals(self):
        analyzer = FakeAnalyzer()
        AudioService(analyzer, FakeMeter()).reconnect_audio_signals()

        assert analyzer.blocked is False

    def test_block_errors_are_swallowed(self):
        class Broken:
            def blockSignals(self, value):
                raise RuntimeError("boom")

        service = AudioService(Broken(), FakeMeter())

        service.disconnect_audio_signals()
        service.reconnect_audio_signals()


class TestDisplayModeAndCleanup:
    def test_set_display_mode_forwards_to_meter(self):
        meter = FakeMeter()
        AudioService(FakeAnalyzer(), meter).set_display_mode("SPL Estimate (Room)")

        assert meter.mode == "SPL Estimate (Room)"

    def test_set_display_mode_without_meter_is_noop(self):
        AudioService(FakeAnalyzer(), None).set_display_mode("dB Output (dBFS)")

    def test_pause_and_apply_settings_pauses_then_sets_mode(self):
        analyzer = FakeAnalyzer(is_playing=True)
        meter = FakeMeter()
        service = AudioService(analyzer, meter)

        assert service.pause_and_apply_settings("SPL Estimate (Room)") is True
        assert analyzer.stopped is True
        assert meter.mode == "SPL Estimate (Room)"

    def test_cleanup_stops_and_waits_for_analyzer(self):
        analyzer = FakeAnalyzer(is_playing=True, running=True)

        AudioService(analyzer, FakeMeter()).cleanup()

        assert analyzer.is_playing is False
        assert analyzer.stopped is True
        assert analyzer.waited == 1000

    def test_cleanup_swallows_errors(self):
        analyzer = FakeAnalyzer(is_playing=True, raise_on_stop=True)

        AudioService(analyzer, FakeMeter()).cleanup()

    def test_cleanup_without_analyzer_is_noop(self):
        AudioService(None, FakeMeter()).cleanup()


class TestFileDuration:
    def test_missing_file_returns_zero(self, tmp_path):
        service = AudioService(FakeAnalyzer(), FakeMeter())

        assert service.get_file_duration("ffprobe", str(tmp_path / "nope.wav")) == 0.0

    def test_parses_ffprobe_duration(self, tmp_path, monkeypatch):
        media = tmp_path / "song.wav"
        media.write_bytes(b"data")
        captured = {}

        def fake_run(cmd, **kwargs):
            captured["cmd"] = cmd
            return subprocess.CompletedProcess(cmd, 0, stdout="123.45\n", stderr="")

        monkeypatch.setattr(subprocess, "run", fake_run)

        service = AudioService(FakeAnalyzer(), FakeMeter())
        assert service.get_file_duration("/usr/bin/ffprobe", str(media)) == pytest.approx(123.45)
        assert captured["cmd"][0] == "/usr/bin/ffprobe"
        assert captured["cmd"][-1] == str(media)

    def test_unparsable_output_returns_zero(self, tmp_path, monkeypatch):
        media = tmp_path / "song.wav"
        media.write_bytes(b"data")
        monkeypatch.setattr(
            subprocess, "run", lambda cmd, **kwargs: subprocess.CompletedProcess(cmd, 0, stdout="N/A", stderr="")
        )

        assert AudioService(FakeAnalyzer(), FakeMeter()).get_file_duration("ffprobe", str(media)) == 0.0

    def test_subprocess_failure_returns_zero(self, tmp_path, monkeypatch):
        media = tmp_path / "song.wav"
        media.write_bytes(b"data")

        def _boom(cmd, **kwargs):
            raise OSError("ffprobe missing")

        monkeypatch.setattr(subprocess, "run", _boom)

        assert AudioService(FakeAnalyzer(), FakeMeter()).get_file_duration("ffprobe", str(media)) == 0.0


class TestCommandBuilders:
    @pytest.fixture
    def service(self):
        return AudioService(FakeAnalyzer(), FakeMeter())

    def test_volume_command_includes_limiter_by_default(self, service):
        cmd = service.get_volume_adjustment_command("ffmpeg", "in.mp4", "out.mp4", 6)

        assert cmd[cmd.index("-af") + 1] == "volume=6dB,alimiter=limit=0.95"
        assert cmd[:4] == ["ffmpeg", "-y", "-i", "in.mp4"]
        assert cmd[-1] == "out.mp4"

    def test_volume_command_can_skip_limiter(self, service):
        cmd = service.get_volume_adjustment_command("ffmpeg", "in.mp4", "out.mp4", -3, apply_limiter=False)

        assert cmd[cmd.index("-af") + 1] == "volume=-3dB"

    def test_volume_command_copies_video_and_encodes_aac(self, service):
        cmd = service.get_volume_adjustment_command("ffmpeg", "in.mp4", "out.mp4", 0)

        assert cmd[cmd.index("-c:v") + 1] == "copy"
        assert cmd[cmd.index("-c:a") + 1] == "aac"

    @pytest.mark.parametrize(
        "duration_a, duration_b, expected",
        [(120.0, 60.0, 2.0), (60.0, 120.0, 0.5), (90.0, 90.0, 1.0)],
    )
    def test_speed_ratio(self, service, duration_a, duration_b, expected):
        assert service.calculate_speed_ratio(duration_a, duration_b) == pytest.approx(expected)

    def test_speed_ratio_guards_zero_division(self, service):
        assert service.calculate_speed_ratio(120.0, 0) == 1.0

    def test_speed_adjustment_command_maps_filtered_streams(self, service):
        cmd = service.get_speed_adjustment_command("ffmpeg", "in.mp4", "out.mp4", 2.0)

        filter_complex = cmd[cmd.index("-filter_complex") + 1]
        assert filter_complex == "[0:v]setpts=0.5*PTS[v];[0:a]atempo=2.0[a]"
        assert cmd[cmd.index("-map") + 1] == "[v]"
        assert cmd[-1] == "out.mp4"
