"""Unit tests for source_code/workers/process_thread.py"""

import pytest

from source_code.workers import process_thread as process_thread_module
from source_code.workers.process_thread import ProcessThread


class FakeStdout:
    def __init__(self, text):
        self._chars = list(text)
        self.closed = False

    def read(self, size=1):
        if not self._chars:
            return ""
        return self._chars.pop(0)

    def close(self):
        self.closed = True


class FakeProcess:
    def __init__(self, output="", returncode=0):
        self.stdout = FakeStdout(output)
        self.returncode = returncode
        self.terminated = False
        self.killed = False
        self.waited = False

    def poll(self):
        return self.returncode

    def terminate(self):
        self.terminated = True

    def kill(self):
        self.killed = True

    def wait(self, timeout=None):
        self.waited = True
        return self.returncode


@pytest.fixture
def spawn(monkeypatch):
    """Run a ProcessThread against fake process output and collect emitted signals."""

    def _spawn(output, duration=0, returncode=0):
        process = FakeProcess(output=output, returncode=returncode)
        captured = {}

        def fake_popen(cmd, **kwargs):
            captured["cmd"] = cmd
            captured["kwargs"] = kwargs
            return process

        monkeypatch.setattr(process_thread_module.subprocess, "Popen", fake_popen)

        thread = ProcessThread(["ffmpeg", "-i", "in.mp4", "out.mp4"], duration=duration)
        events = {"progress": [], "status": [], "lines": [], "finished": []}
        thread.progress.connect(events["progress"].append)
        thread.status_update.connect(events["status"].append)
        thread.line_output.connect(events["lines"].append)
        thread.finished.connect(events["finished"].append)

        thread.run()
        return thread, process, events, captured

    return _spawn


class TestInit:
    def test_stores_command_and_duration(self):
        thread = ProcessThread(["ffmpeg"], duration=42)

        assert thread.cmd == ["ffmpeg"]
        assert thread.duration == 42
        assert thread.process is None
        assert thread.is_killed is False


class TestRun:
    def test_emits_raw_lines_and_success(self, qapp, spawn):
        _, _, events, captured = spawn("hello\nworld\n")

        assert events["lines"] == ["hello", "world"]
        assert events["finished"] == [True]
        assert captured["cmd"] == ["ffmpeg", "-i", "in.mp4", "out.mp4"]

    def test_blank_lines_are_ignored(self, qapp, spawn):
        _, _, events, _ = spawn("\n   \r\nreal line\n")

        assert events["lines"] == ["real line"]

    def test_parses_download_percentage(self, qapp, spawn):
        _, _, events, _ = spawn("[download]  42.7% of 10MiB\n")

        assert events["progress"] == [42]
        assert events["status"] == ["Downloading Assets... 42%"]

    def test_download_percentage_is_capped_at_100(self, qapp, spawn):
        _, _, events, _ = spawn("[download] 150.0%\n")

        assert events["progress"] == [100]

    def test_download_line_without_match_emits_nothing(self, qapp, spawn):
        _, _, events, _ = spawn("[download] unknown %\n")

        assert events["progress"] == []

    def test_duration_is_detected_when_unknown(self, qapp, spawn):
        thread, _, events, _ = spawn("  Duration: 00:02:30.50, start: 0.0\n")

        assert thread.duration == pytest.approx(150.5)
        assert events["progress"] == []

    def test_existing_duration_is_not_overwritten(self, qapp, spawn):
        thread, _, _, _ = spawn("  Duration: 00:02:30.50\n", duration=99)

        assert thread.duration == 99

    def test_time_lines_produce_conversion_progress(self, qapp, spawn):
        _, _, events, _ = spawn("frame= 10 time=00:00:50.00 bitrate=1k\n", duration=100)

        assert events["progress"] == [50]
        assert events["status"] == ["Converting Video Layout... 50%"]

    def test_conversion_progress_is_capped_at_100(self, qapp, spawn):
        _, _, events, _ = spawn("time=00:00:20.00\n", duration=10)

        assert events["progress"] == [100]

    def test_time_lines_are_ignored_without_known_duration(self, qapp, spawn):
        _, _, events, _ = spawn("time=00:00:05.00\n")

        assert events["progress"] == []

    def test_carriage_returns_delimit_lines(self, qapp, spawn):
        _, _, events, _ = spawn("[download] 10.0%\r[download] 20.0%\r")

        assert events["progress"] == [10, 20]

    def test_nonzero_exit_code_reports_failure(self, qapp, spawn):
        _, _, events, _ = spawn("done\n", returncode=1)

        assert events["finished"] == [False]

    def test_killed_thread_reports_failure(self, qapp, monkeypatch):
        process = FakeProcess(output="line\n")
        monkeypatch.setattr(process_thread_module.subprocess, "Popen", lambda cmd, **kwargs: process)

        thread = ProcessThread(["ffmpeg"])
        thread.is_killed = True
        results = []
        thread.finished.connect(results.append)

        thread.run()

        assert results == [False]
        assert process.killed is True

    def test_stdout_read_error_is_swallowed(self, qapp, monkeypatch):
        class BrokenStdout(FakeStdout):
            def read(self, size=1):
                raise OSError("pipe broken")

        process = FakeProcess()
        process.stdout = BrokenStdout("")
        monkeypatch.setattr(process_thread_module.subprocess, "Popen", lambda cmd, **kwargs: process)

        thread = ProcessThread(["ffmpeg"])
        results = []
        thread.finished.connect(results.append)

        thread.run()

        assert results == [True]


class TestCleanupAndStop:
    def test_cleanup_without_process_is_noop(self):
        ProcessThread(["ffmpeg"]).cleanup_process()

    def test_cleanup_closes_stdout_and_waits(self):
        thread = ProcessThread(["ffmpeg"])
        thread.process = FakeProcess()

        thread.cleanup_process()

        assert thread.process.waited is True
        assert thread.process.stdout.closed is True
        assert thread.process.killed is False

    def test_stop_marks_killed_and_terminates_process(self):
        thread = ProcessThread(["ffmpeg"])
        thread.process = FakeProcess()

        thread.stop()

        assert thread.is_killed is True
        assert thread.process.terminated is True
        assert thread.process.killed is True

    def test_stop_ignores_termination_errors(self):
        class BrokenProcess(FakeProcess):
            def terminate(self):
                raise RuntimeError("gone")

        thread = ProcessThread(["ffmpeg"])
        thread.process = BrokenProcess()

        thread.stop()

        assert thread.is_killed is True
