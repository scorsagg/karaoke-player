"""Unit tests for source_code/controllers/processing_controller.py"""

import pytest

from source_code.controllers import processing_controller as pc_module
from source_code.controllers.processing_controller import ProcessingController

FFMPEG = "/usr/bin/ffmpeg"


class FakeLabel:
    def __init__(self, text=""):
        self._text = text

    def setText(self, text):
        self._text = text

    def text(self):
        return self._text


class FakeSplash:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


class FakeSpin:
    def __init__(self, value=0.0):
        self._value = value

    def value(self):
        return self._value


class FakeThread:
    def __init__(self, running=True):
        self._running = running
        self.stopped = False
        self.wait_ms = None

    def isRunning(self):
        return self._running

    def stop(self):
        self.stopped = True

    def wait(self, msecs):
        self.wait_ms = msecs
        return True


class FakeApp:
    def __init__(self, **overrides):
        self.settings = {"ffmpeg_path": FFMPEG}
        self.active_tasks = {}
        self.export_splash = None
        self.status_label = FakeLabel()
        self.audio_file_status = FakeLabel()
        self.merge_status_label = FakeLabel()
        self.amp_status_label = FakeLabel()
        self.merge_audio_offset_spin = FakeSpin()
        self.audio_tools_file_path = ""
        self.debug_lines = []
        self.loaded = []
        self.extraction_ui_calls = []
        self.reset_amplify_calls = []
        self.merge_behavior = "concat"
        self.media_types = {}
        self.durations = {}
        self.PAGE_AUDIO_STUDIO = 1
        self.PAGE_CONVERT_EXPORT = 3
        self._current_export_media_kind = "audio"
        self._last_merge_cmd_text = ""
        for key, value in overrides.items():
            setattr(self, key, value)

    def log_debug(self, message):
        self.debug_lines.append(message)

    def load_video(self, path, is_audio_only=False):
        self.loaded.append((path, is_audio_only))

    def update_extraction_ui(self, flag):
        self.extraction_ui_calls.append(flag)

    def classify_media_type(self, path):
        return self.media_types.get(path, "video")

    def _classify_media_type_for_merge(self, path):
        return self.media_types.get(path, "video")

    def _resolve_merge_behavior(self, mode):
        return self.merge_behavior

    def get_video_duration_via_ffprobe(self, path):
        return self.durations.get(path, 0.0)

    def _reset_export_amplify_factor(self, name):
        self.reset_amplify_calls.append(name)

    def _return_to_amplify_export_tab(self):
        pass

    def handle_navigation_change(self, idx):
        pass


@pytest.fixture
def controller():
    return ProcessingController()


@pytest.fixture
def app():
    return FakeApp()


@pytest.fixture
def message_boxes(monkeypatch):
    """Capture QMessageBox usage instead of showing modal dialogs."""
    calls = {"information": [], "warning": []}

    class FakeMessageBox:
        @staticmethod
        def information(parent, title, text):
            calls["information"].append((title, text))

        @staticmethod
        def warning(parent, title, text):
            calls["warning"].append((title, text))

    monkeypatch.setattr(pc_module, "QMessageBox", FakeMessageBox)
    return calls


@pytest.fixture
def deferred_calls(monkeypatch):
    """Capture QTimer.singleShot callbacks without running an event loop."""
    scheduled = []

    class FakeTimer:
        @staticmethod
        def singleShot(msec, callback):
            scheduled.append((msec, callback))

    monkeypatch.setattr(pc_module, "QTimer", FakeTimer)
    return scheduled


class TestAmplifyExportCmd:
    def test_boost_adds_limiter(self, controller, app):
        cmd = controller.build_amplify_export_cmd(app, "in.wav", "out.wav", 2.0, "audio", "wav")

        assert cmd[cmd.index("-af") + 1] == "volume=2.0000,alimiter=limit=0.98:attack=5:release=50"

    def test_attenuation_has_no_limiter(self, controller, app):
        cmd = controller.build_amplify_export_cmd(app, "in.wav", "out.wav", 0.5, "audio", "wav")

        assert cmd[cmd.index("-af") + 1] == "volume=0.5000"

    def test_invalid_factor_falls_back_to_unity(self, controller, app):
        cmd = controller.build_amplify_export_cmd(app, "in.wav", "out.wav", "loud", "audio", "wav")

        assert cmd[cmd.index("-af") + 1] == "volume=1.0000"

    def test_video_copies_stream_and_reencodes_audio(self, controller, app):
        cmd = controller.build_amplify_export_cmd(app, "in.mp4", "out.mp4", 1.5, "video", "mp4")

        assert cmd[cmd.index("-c:v") + 1] == "copy"
        assert cmd[cmd.index("-c:a") + 1] == "aac"
        assert cmd[-1] == "out.mp4"

    @pytest.mark.parametrize(
        "src_ext, expected_codec",
        [("wav", "pcm_s16le"), ("mp3", "libmp3lame"), ("aac", "aac"), ("m4a", "aac"), ("flac", "flac"), ("ogg", "libvorbis"), ("opus", "libopus")],
    )
    def test_audio_codec_per_source_extension(self, controller, app, src_ext, expected_codec):
        cmd = controller.build_amplify_export_cmd(app, f"in.{src_ext}", f"out.{src_ext}", 1.0, "audio", src_ext)

        assert cmd[cmd.index("-c:a") + 1] == expected_codec

    def test_flac_omits_bitrate(self, controller, app):
        cmd = controller.build_amplify_export_cmd(app, "in.flac", "out.flac", 1.0, "audio", "flac")

        assert "-b:a" not in cmd

    def test_unknown_extension_falls_back_to_aac(self, controller, app):
        cmd = controller.build_amplify_export_cmd(app, "in.xyz", "out.xyz", 1.0, "audio", "xyz")

        assert cmd[cmd.index("-c:a") + 1] == "aac"
        assert cmd[0] == FFMPEG


class TestFormatConversionCmd:
    @pytest.mark.parametrize(
        "target_fmt, expected_codec",
        [("mp3", "libmp3lame"), ("wav", "pcm_s16le"), ("aac", "aac"), ("m4a", "aac")],
    )
    def test_audio_targets_drop_video_stream(self, controller, app, target_fmt, expected_codec):
        cmd = controller.build_format_conversion_cmd(app, "in.mp4", f"out.{target_fmt}", target_fmt, "192k")

        assert "-vn" in cmd
        assert cmd[cmd.index("-acodec") + 1] == expected_codec

    def test_wav_target_ignores_bitrate(self, controller, app):
        cmd = controller.build_format_conversion_cmd(app, "in.mp4", "out.wav", "wav", "320k")

        assert "-b:a" not in cmd
        assert cmd[cmd.index("-ar") + 1] == "44100"

    def test_mp4_target_reencodes_video(self, controller, app):
        cmd = controller.build_format_conversion_cmd(app, "in.mkv", "out.mp4", "mp4", "192k")

        assert cmd[cmd.index("-c:v") + 1] == "libx264"
        assert cmd[cmd.index("-preset") + 1] == "fast"

    def test_mkv_target_copies_video(self, controller, app):
        cmd = controller.build_format_conversion_cmd(app, "in.mp4", "out.mkv", "mkv", "192k")

        assert cmd[cmd.index("-c:v") + 1] == "copy"

    def test_unknown_target_is_stream_copy(self, controller, app):
        cmd = controller.build_format_conversion_cmd(app, "in.mp4", "out.mov", "mov", "192k")

        assert cmd[cmd.index("-c") + 1] == "copy"


class TestMultiTrimCmds:
    def test_audio_trim_builds_filter_per_range(self, controller, app):
        cmd = controller.build_audio_multi_trim_cmd(app, "in.mp3", "out.mp3", "mp3", [(0, 1500), (3000, 4500)])

        filter_complex = cmd[cmd.index("-filter_complex") + 1]
        assert "[0:a]atrim=start=0.0:end=1.5,asetpts=PTS-STARTPTS[a0]" in filter_complex
        assert "[0:a]atrim=start=3.0:end=4.5,asetpts=PTS-STARTPTS[a1]" in filter_complex
        assert filter_complex.endswith("[a0][a1]concat=n=2:v=0:a=1[a]")
        assert cmd[cmd.index("-map") + 1] == "[a]"

    @pytest.mark.parametrize(
        "target_fmt, expected_codec",
        [("mp3", "libmp3lame"), ("wav", "pcm_s16le"), ("aac", "aac"), ("m4a", "aac"), ("weird", "copy")],
    )
    def test_audio_trim_codec_per_target(self, controller, app, target_fmt, expected_codec):
        cmd = controller.build_audio_multi_trim_cmd(app, "in.mp3", "out.x", target_fmt, [(0, 1000)])

        assert cmd[cmd.index("-acodec") + 1] == expected_codec

    def test_video_trim_maps_both_streams(self, controller, app):
        cmd = controller.build_video_multi_trim_cmd(app, "in.mp4", "out.mp4", "mp4", [(0, 2000)])

        filter_complex = cmd[cmd.index("-filter_complex") + 1]
        assert "[0:v]trim=start=0.0:end=2.0,setpts=PTS-STARTPTS[v0]" in filter_complex
        assert filter_complex.endswith("[v0][a0]concat=n=1:v=1:a=1[v][a]")
        assert cmd.count("-map") == 2

    @pytest.mark.parametrize(
        "target_fmt, expected_video_codec",
        [("mp4", "libx264"), ("mkv", "libx264"), ("webm", "libvpx-vp9"), ("avi", "mpeg4"), ("weird", "libx264")],
    )
    def test_video_trim_codec_per_target(self, controller, app, target_fmt, expected_video_codec):
        cmd = controller.build_video_multi_trim_cmd(app, "in.mp4", "out.x", target_fmt, [(0, 1000)])

        assert cmd[cmd.index("-c:v") + 1] == expected_video_codec


class TestJoinMergeCmd:
    def test_video_audio_merge_orders_inputs_by_media_type(self, controller):
        app = FakeApp(media_types={"/a.mp4": "video", "/b.mp3": "audio"})

        cmd = controller._build_join_merge_cmd(app, "/b.mp3", "/a.mp4", "video_audio_merge", "/out.mp4")

        assert cmd[cmd.index("-i") + 1] == "/a.mp4"
        assert cmd[cmd.index("0:v:0") - 1] == "-map"
        assert cmd[-1] == "/out.mp4"

    def test_video_audio_merge_rejects_mismatched_inputs(self, controller):
        app = FakeApp(media_types={"/a.mp4": "video", "/b.mp4": "video"})

        with pytest.raises(RuntimeError, match="expected one video \\+ one audio"):
            controller._build_join_merge_cmd(app, "/a.mp4", "/b.mp4", "video_audio_merge", "/out.mp4")

    def test_video_audio_merge_rejects_same_file(self, controller, tmp_path):
        media = tmp_path / "same.mp4"
        media.write_bytes(b"data")
        app = FakeApp()
        # Same path classified inconsistently (e.g. probe flakiness) still must not merge onto itself.
        types = iter(["video", "audio"])
        app._classify_media_type_for_merge = lambda path: next(types)

        with pytest.raises(RuntimeError, match="resolved to the same file"):
            controller._build_join_merge_cmd(app, str(media), str(media), "video_audio_merge", "/out.mp4")

    def test_video_audio_append_pads_video_and_prepends_silence(self, controller):
        app = FakeApp(
            media_types={"/a.mp4": "video", "/b.mp3": "audio"},
            durations={"/a.mp4": 30.0, "/b.mp3": 10.0},
            merge_behavior="append",
        )

        cmd = controller._build_join_merge_cmd(app, "/a.mp4", "/b.mp3", "video_audio_merge", "/out.mp4")

        filter_complex = cmd[cmd.index("-filter_complex") + 1]
        assert "tpad=stop_mode=clone:stop_duration=10.000" in filter_complex
        assert "anullsrc=channel_layout=stereo:sample_rate=44100:d=30.000" in filter_complex

    def test_video_audio_append_uses_fallback_durations(self, controller):
        app = FakeApp(
            media_types={"/a.mp4": "video", "/b.mp3": "audio"},
            merge_behavior="append",
        )
        app.get_video_duration_via_ffprobe = lambda path: None

        cmd = controller._build_join_merge_cmd(app, "/a.mp4", "/b.mp3", "video_audio_merge", "/out.mp4")

        filter_complex = cmd[cmd.index("-filter_complex") + 1]
        assert "stop_duration=1.000" in filter_complex
        assert "d=1.000" in filter_complex

    def test_video_audio_merge_applies_audio_offset(self, controller):
        app = FakeApp(
            media_types={"/a.mp4": "video", "/b.mp3": "audio"},
            merge_audio_offset_spin=FakeSpin(1.25),
        )

        cmd = controller._build_join_merge_cmd(app, "/a.mp4", "/b.mp3", "video_audio_merge", "/out.mp4")

        assert "[1:a]adelay=1250:all=1,aresample=44100,asetpts=PTS-STARTPTS[a]" in cmd

    def test_video_audio_merge_survives_broken_offset_spin(self, controller):
        class BrokenSpin:
            def value(self):
                raise RuntimeError("no widget")

        app = FakeApp(
            media_types={"/a.mp4": "video", "/b.mp3": "audio"},
            merge_audio_offset_spin=BrokenSpin(),
        )

        cmd = controller._build_join_merge_cmd(app, "/a.mp4", "/b.mp3", "video_audio_merge", "/out.mp4")

        assert "1:a:0" in cmd

    def test_audio_join_concat(self, controller, app):
        cmd = controller._build_join_merge_cmd(app, "/a.mp3", "/b.mp3", "audio_audio_join", "/out.mp3")

        assert "concat=n=2:v=0:a=1[a]" in cmd[cmd.index("-filter_complex") + 1]
        assert cmd[cmd.index("-c:a") + 1] == "libmp3lame"

    def test_audio_join_overlay_mixes_inputs(self, controller):
        app = FakeApp(merge_behavior="overlay")

        cmd = controller._build_join_merge_cmd(app, "/a.mp3", "/b.mp3", "audio_audio_join", "/out.wav")

        assert "amix=inputs=2:duration=longest" in cmd[cmd.index("-filter_complex") + 1]
        assert cmd[cmd.index("-c:a") + 1] == "pcm_s16le"

    def test_video_join_concat_normalizes_both_inputs(self, controller, app):
        cmd = controller._build_join_merge_cmd(app, "/a.mp4", "/b.mp4", "video_video_join", "/out.mp4")

        filter_complex = cmd[cmd.index("-filter_complex") + 1]
        assert filter_complex.count("scale=1280:720") == 2
        assert filter_complex.endswith("[v0][a0][v1][a1]concat=n=2:v=1:a=1[v][a]")

    def test_video_join_overlay_blends_streams(self, controller):
        app = FakeApp(merge_behavior="overlay")

        cmd = controller._build_join_merge_cmd(app, "/a.mp4", "/b.mp4", "video_video_join", "/out.mp4")

        assert "blend=all_mode='screen':all_opacity=0.5[v]" in cmd[cmd.index("-filter_complex") + 1]
        assert "-shortest" in cmd


class TestTaskLifecycle:
    def test_kill_allocated_task_is_noop_for_unknown_key(self, controller, app):
        controller.kill_allocated_task(app, "missing_task")

        assert app.debug_lines == []

    def test_kill_allocated_task_stops_thread_and_closes_splash(self, controller, app):
        thread = FakeThread()
        app.active_tasks["export_task"] = thread
        splash = FakeSplash()
        app.export_splash = splash

        controller.kill_allocated_task(app, "export_task")

        assert thread.stopped is True
        assert thread.wait_ms == 2000
        assert app.active_tasks == {}
        assert splash.closed is True
        assert app.export_splash is None
        assert app.status_label.text() == "Status: Ready"

    def test_kill_allocated_task_tolerates_broken_thread(self, controller, app):
        class BrokenThread:
            def isRunning(self):
                raise RuntimeError("dead")

            def stop(self):
                raise RuntimeError("dead")

            def wait(self, msecs):
                raise RuntimeError("dead")

        app.active_tasks["export_task"] = BrokenThread()

        controller.kill_allocated_task(app, "export_task")

        assert app.active_tasks == {}
        assert any("cancel wait raised exception" in line for line in app.debug_lines)

    def test_stop_all_tasks_clears_registry(self, controller, app):
        first, second = FakeThread(), FakeThread()
        app.active_tasks.update({"a": first, "b": second})

        controller.stop_all_tasks(app)

        assert first.stopped and second.stopped
        assert app.active_tasks == {}

    def test_stop_all_tasks_ignores_failures(self, controller, app):
        class BrokenThread:
            def stop(self):
                raise RuntimeError("dead")

        app.active_tasks["a"] = BrokenThread()

        controller.stop_all_tasks(app)

        assert app.active_tasks == {}
        assert any("shutdown stop | exception" in line for line in app.debug_lines)


class TestTaskCompletion:
    def test_failure_warns_and_closes_splash(self, controller, app, message_boxes, deferred_calls):
        app.export_splash = FakeSplash()

        controller.handle_task_completion(app, "convert_task", "/out.mp3", False)

        assert app.export_splash is None
        assert message_boxes["warning"][0][0] == "Processing Break"
        assert app.loaded == []

    def test_merge_failure_copies_command_to_clipboard(self, controller, message_boxes, deferred_calls, monkeypatch):
        app = FakeApp(_last_merge_cmd_text="ffmpeg -i a -i b out.mp4")
        copied = {}

        class FakeClipboard:
            def setText(self, text):
                copied["text"] = text

        monkeypatch.setattr(pc_module.QApplication, "clipboard", staticmethod(lambda: FakeClipboard()))

        controller.handle_task_completion(app, "merge_task", "/out.mp4", False)

        assert copied["text"] == "ffmpeg -i a -i b out.mp4"
        assert "copied to clipboard" in message_boxes["warning"][0][1]

    def test_missing_output_file_does_not_load_media(self, controller, app, message_boxes, deferred_calls):
        controller.handle_task_completion(app, "convert_task", "/does/not/exist.mp3", True)

        assert app.loaded == []
        assert message_boxes["information"] == []

    def test_extract_task_updates_audio_tools_state(self, controller, app, message_boxes, deferred_calls, tmp_path):
        out = tmp_path / "vocals.wav"
        out.write_bytes(b"data")

        controller.handle_task_completion(app, "extract_task", str(out), True)

        assert app.loaded == [(str(out), True)]
        assert app.audio_tools_file_path == str(out)
        assert app.audio_file_status.text() == "✅ vocals.wav (Extracted Audio)"
        assert app.extraction_ui_calls == [False]
        assert [msec for msec, _ in deferred_calls] == [100]

    def test_amplify_task_uses_current_export_media_kind(self, controller, message_boxes, deferred_calls, tmp_path):
        out = tmp_path / "loud.mp4"
        out.write_bytes(b"data")
        app = FakeApp(_current_export_media_kind="video")

        controller.handle_task_completion(app, "amplify_task", str(out), True)

        assert app.loaded == [(str(out), False)]
        assert app.reset_amplify_calls == ["loud.mp4"]
        assert "Amplified file loaded" in app.amp_status_label.text()

    def test_merge_task_with_audio_output_updates_audio_status(self, controller, message_boxes, deferred_calls, tmp_path):
        out = tmp_path / "joined.mp3"
        out.write_bytes(b"data")
        app = FakeApp(media_types={str(out): "audio"})

        controller.handle_task_completion(app, "merge_task", str(out), True)

        assert app.loaded == [(str(out), True)]
        assert app.merge_status_label.text() == "✅ Merge completed: joined.mp3"
        assert app.audio_file_status.text() == "✅ joined.mp3 (Merged Output)"

    def test_merge_task_with_video_output_keeps_audio_status_empty(self, controller, message_boxes, deferred_calls, tmp_path):
        out = tmp_path / "joined.mp4"
        out.write_bytes(b"data")
        app = FakeApp(media_types={str(out): "video"})

        controller.handle_task_completion(app, "merge_task", str(out), True)

        assert app.loaded == [(str(out), False)]
        assert app.audio_file_status.text() == ""

    def test_convert_task_navigates_to_convert_export(self, controller, app, message_boxes, deferred_calls, tmp_path):
        out = tmp_path / "song.wav"
        out.write_bytes(b"data")

        controller.handle_task_completion(app, "convert_task", str(out), True)

        assert app.audio_file_status.text() == "✅ song.wav (Processed Audio)"
        assert len(deferred_calls) == 1
        assert message_boxes["information"][0][0] == "Success"
