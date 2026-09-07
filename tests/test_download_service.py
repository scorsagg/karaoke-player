"""Unit tests for source_code/services/download_service.py"""

import pytest

from source_code.services.download_service import DownloadService


class FakeSettingsManager:
    def __init__(self, values=None):
        self.values = values or {}

    def get(self, key, default=None):
        return self.values.get(key, default)


class FakeSignal:
    def __init__(self):
        self.slots = []

    def connect(self, slot):
        self.slots.append(slot)

    def emit(self, *args):
        for slot in list(self.slots):
            slot(*args)


class FakeProcessThread:
    def __init__(self, cmd, duration=0):
        self.cmd = cmd
        self.duration = duration
        self.is_killed = False
        self.started = False
        self.terminated = False
        self.waited = False
        self.running = False
        self.line_output = FakeSignal()
        self.finished = FakeSignal()

    def start(self):
        self.started = True
        self.running = True

    def isRunning(self):
        return self.running

    def terminate(self):
        self.terminated = True
        self.running = False

    def wait(self, *args):
        self.waited = True
        return True


@pytest.fixture
def service(qapp):
    created = []

    def factory(cmd, duration=0):
        thread = FakeProcessThread(cmd, duration)
        created.append(thread)
        return thread

    svc = DownloadService(FakeSettingsManager({"ytdlp_path": "/opt/yt-dlp"}), factory)
    svc.created_threads = created
    return svc


@pytest.fixture
def recorder(service):
    events = {"progress": [], "finished": [], "error": []}
    service.download_progress.connect(lambda pct, msg: events["progress"].append((pct, msg)))
    service.download_finished.connect(events["finished"].append)
    service.download_error.connect(events["error"].append)
    return events


class TestDownloadVideo:
    def test_builds_ytdlp_command_and_starts_thread(self, service, tmp_path):
        assert service.download_video("https://youtu.be/abc", str(tmp_path)) is True

        thread = service.created_threads[0]
        assert thread.started is True
        assert thread.cmd[0] == "/opt/yt-dlp"
        assert thread.cmd[-1] == "https://youtu.be/abc"
        assert "--no-playlist" in thread.cmd
        assert str(tmp_path / "%(title)s.%(ext)s") in thread.cmd
        assert service.download_url == "https://youtu.be/abc"

    def test_uses_custom_format_selector(self, service, tmp_path):
        service.download_video("https://youtu.be/abc", str(tmp_path), preferred_format="bestaudio")

        cmd = service.created_threads[0].cmd
        assert cmd[cmd.index("-f") + 1] == "bestaudio"

    def test_creates_missing_download_directory(self, service, tmp_path):
        target = tmp_path / "nested" / "downloads"

        service.download_video("https://youtu.be/abc", str(target))

        assert target.is_dir()

    def test_falls_back_to_bare_ytdlp_when_unset(self, tmp_path, qapp):
        svc = DownloadService(FakeSettingsManager(), FakeProcessThread)

        svc.download_video("https://youtu.be/abc", str(tmp_path))

        assert svc.download_thread.cmd[0] == "yt-dlp"

    def test_rejects_concurrent_download(self, service, recorder, tmp_path):
        service.download_video("https://youtu.be/first", str(tmp_path))

        assert service.download_video("https://youtu.be/second", str(tmp_path)) is False
        assert len(service.created_threads) == 1
        assert "already in progress" in recorder["error"][0]

    def test_is_downloading_reflects_thread_state(self, service, tmp_path):
        assert service.is_downloading() is False

        service.download_video("https://youtu.be/abc", str(tmp_path))
        assert service.is_downloading() is True

        service.download_thread.running = False
        assert service.is_downloading() is False


class TestParseDownloadStatus:
    def test_percentage_line_emits_progress(self, service, recorder):
        service._parse_download_status("[download]  42.7% of 10.00MiB at 1.00MiB/s ETA 00:05")

        assert recorder["progress"] == [(42, "Downloading: 42%")]

    def test_merge_line_emits_post_processing_progress(self, service, recorder):
        service._parse_download_status('[ffmpeg] Merging formats into "out.mp4"')

        assert recorder["progress"] == [(95, "Post-processing: Merging audio/video...")]

    def test_extract_audio_marker_emits_post_processing_progress(self, service, recorder):
        service._parse_download_status("[ExtractAudio] preparing")

        assert recorder["progress"] == [(95, "Post-processing: Merging audio/video...")]

    def test_destination_line_records_filename(self, service, recorder):
        service._parse_download_status("[download] Destination: /media/song.mp4")

        assert service.current_download_filename == "/media/song.mp4"
        assert recorder["progress"] == [(100, "Download complete.")]

    def test_merger_line_records_final_filename(self, service, recorder):
        service._parse_download_status('[Merger] Merging formats into "/media/final.mp4"')

        assert service.current_download_filename == "/media/final.mp4"
        assert recorder["progress"] == [(100, "Download complete.")]

    def test_extract_audio_destination_records_final_filename(self, service, recorder):
        service._parse_download_status("[ExtractAudio] Destination: /media/song.m4a")

        assert service.current_download_filename == "/media/song.m4a"
        assert recorder["progress"] == [(100, "Download complete.")]

    def test_error_line_emits_error_only_once(self, service, recorder):
        service._parse_download_status("ERROR: unable to download video")
        service._parse_download_status("ERROR: unable to download video")

        assert recorder["error"] == ["ERROR: unable to download video"]
        assert service.last_download_error == "ERROR: unable to download video"

    def test_unrelated_line_is_ignored(self, service, recorder):
        service._parse_download_status("[info] Available formats for abc")

        assert recorder["progress"] == []
        assert recorder["error"] == []


class TestProgressHook:
    def test_downloading_with_total_bytes_reports_speed_and_eta(self, service, recorder):
        service._download_progress_hook(
            {"status": "downloading", "total_bytes": 1000, "downloaded_bytes": 250, "speed": 2 * 1024 * 1024, "eta": 12}
        )

        assert recorder["progress"] == [(25, "Downloading: 25% at 2.00MB/s ETA 12s")]

    def test_downloading_without_speed_or_eta_uses_placeholders(self, service, recorder):
        service._download_progress_hook(
            {"status": "downloading", "total_bytes": 1000, "downloaded_bytes": 500, "speed": 0, "eta": 0}
        )

        assert recorder["progress"] == [(50, "Downloading: 50% at N/A ETA N/A")]

    def test_zero_total_bytes_reports_zero_percent(self, service, recorder):
        service._download_progress_hook({"status": "downloading", "total_bytes": 0, "downloaded_bytes": 10})

        assert recorder["progress"][0][0] == 0

    def test_estimated_total_reports_estimated_message(self, service, recorder):
        service._download_progress_hook(
            {"status": "downloading", "total_bytes_estimate": 400, "downloaded_bytes": 100}
        )

        assert recorder["progress"] == [(25, "Downloading: 25% (estimated)")]

    def test_finished_status_records_filename_and_finalizing_message(self, service, recorder):
        service._download_progress_hook({"status": "finished", "filename": "/tmp/out.mp4"})

        assert service.current_download_filename == "/tmp/out.mp4"
        assert recorder["progress"] == [(100, "Finalizing download...")]

    def test_error_status_emits_error(self, service, recorder):
        service._download_progress_hook({"status": "error", "error": "boom"})

        assert recorder["error"] == ["Download error: boom"]


class TestProcessCompletion:
    def test_success_emits_finished_with_filename_and_resets_state(self, service, recorder, tmp_path):
        service.download_video("https://youtu.be/abc", str(tmp_path))
        service._parse_download_status("[download] Destination: /media/song.mp4")

        service.download_thread.finished.emit(True)

        assert recorder["finished"] == ["/media/song.mp4"]
        assert service.download_thread is None
        assert service.current_download_filename is None
        assert service.download_url is None

    def test_success_without_filename_emits_empty_string(self, service, recorder, tmp_path):
        service.download_video("https://youtu.be/abc", str(tmp_path))

        service.download_thread.finished.emit(True)

        assert recorder["finished"] == [""]

    def test_failure_emits_last_error(self, service, recorder, tmp_path):
        service.download_video("https://youtu.be/abc", str(tmp_path))
        service.last_download_error = "ERROR: 403 forbidden"

        service.download_thread.finished.emit(False)

        assert recorder["error"] == ["ERROR: 403 forbidden"]

    def test_failure_without_known_error_emits_generic_message(self, service, recorder, tmp_path):
        service.download_video("https://youtu.be/abc", str(tmp_path))

        service.download_thread.finished.emit(False)

        assert recorder["error"] == ["Download process failed unexpectedly."]

    def test_failure_after_reported_error_does_not_emit_twice(self, service, recorder, tmp_path):
        service.download_video("https://youtu.be/abc", str(tmp_path))
        service._parse_download_status("ERROR: broken pipe")

        service.download_thread.finished.emit(False)

        assert recorder["error"] == ["ERROR: broken pipe"]

    def test_killed_thread_failure_is_silent(self, service, recorder, tmp_path):
        service.download_video("https://youtu.be/abc", str(tmp_path))
        service.download_thread.is_killed = True

        service.download_thread.finished.emit(False)

        assert recorder["error"] == []


class TestStopDownload:
    def test_stop_terminates_thread_and_reports_cancellation(self, service, recorder, tmp_path):
        service.download_video("https://youtu.be/abc", str(tmp_path))
        thread = service.download_thread

        service.stop_download()

        assert thread.is_killed is True
        assert thread.terminated is True
        assert thread.waited is True
        assert recorder["error"] == ["Download cancelled by user."]
        assert service.download_thread is None

    def test_stop_without_active_download_is_noop(self, service, recorder):
        service.stop_download()

        assert recorder["error"] == []
