"""Unit tests for source_code/workers/audio_separator_thread.py"""

import json
import os
import shutil
import sys

import pytest

from source_code.workers import audio_separator_thread as separator_module
from source_code.workers.audio_separator_thread import AudioSeparatorThread

FFMPEG = "/usr/bin/ffmpeg"


class FakeStdout:
    def __init__(self, lines):
        self._lines = list(lines)
        self.closed = False

    def readline(self):
        if not self._lines:
            return ""
        return self._lines.pop(0)

    def close(self):
        self.closed = True


class FakeProcess:
    def __init__(self, lines=(), returncode=0):
        self.stdout = FakeStdout(lines)
        self.returncode = returncode
        self.terminated = False
        self.killed = False

    def poll(self):
        return self.returncode

    def terminate(self):
        self.terminated = True

    def kill(self):
        self.killed = True


def make_thread(tmp_path, **overrides):
    kwargs = dict(
        input_path=str(tmp_path / "song.mp3"),
        ffmpeg_path=FFMPEG,
        output_dir=str(tmp_path),
        backend_name="audio-separator",
        model_filename="model.onnx",
        output_format="WAV",
        target_mode="both",
        fast_mode=False,
        model_file_dir=str(tmp_path / "models"),
    )
    kwargs.update(overrides)
    return AudioSeparatorThread(**kwargs)


@pytest.fixture
def thread(tmp_path, qapp):
    return make_thread(tmp_path)


@pytest.fixture
def popen(monkeypatch):
    """Replace subprocess.Popen with a scripted fake process."""
    state = {"process": FakeProcess(), "cmd": None}

    def fake_popen(cmd, **kwargs):
        state["cmd"] = cmd
        state["kwargs"] = kwargs
        return state["process"]

    monkeypatch.setattr(separator_module.subprocess, "Popen", fake_popen)
    return state


class TestInit:
    def test_output_format_is_normalized(self, thread):
        assert thread.output_format == "wav"

    @pytest.mark.parametrize("value, expected", [(-5, 0), (0, 0), (12, 12), (99, 30)])
    def test_music_recovery_is_clamped(self, tmp_path, qapp, value, expected):
        thread = make_thread(tmp_path, demucs_music_recovery=value)

        assert thread.demucs_music_recovery == expected

    @pytest.mark.parametrize("mode", ["standard", "side_heavy", "center_aware"])
    def test_known_recovery_modes_are_kept(self, tmp_path, qapp, mode):
        thread = make_thread(tmp_path, demucs_recovery_mode=mode)

        assert thread.demucs_recovery_mode == mode

    def test_unknown_recovery_mode_falls_back_to_standard(self, tmp_path, qapp):
        thread = make_thread(tmp_path, demucs_recovery_mode="wild")

        assert thread.demucs_recovery_mode == "standard"

    def test_defaults(self, thread):
        assert thread.is_killed is False
        assert thread.process is None
        assert thread.demucs_music_recovery == 10
        assert thread.demucs_recovery_mode == "standard"


class TestStop:
    def test_stop_without_process_only_sets_flag(self, thread):
        thread.stop()

        assert thread.is_killed is True

    def test_stop_terminates_running_process(self, thread):
        process = FakeProcess()
        thread.process = process

        thread.stop()

        assert (process.terminated, process.killed) == (True, True)

    def test_stop_ignores_termination_errors(self, thread):
        class BrokenProcess(FakeProcess):
            def terminate(self):
                raise RuntimeError("gone")

        thread.process = BrokenProcess()

        thread.stop()

        assert thread.is_killed is True


class TestVideoDetection:
    @pytest.mark.parametrize("name", ["clip.mp4", "clip.MKV", "clip.avi", "clip.mov", "clip.webm", "clip.mts"])
    def test_video_extensions(self, thread, name):
        assert thread._is_video_path(name) is True

    @pytest.mark.parametrize("name", ["song.mp3", "song.wav", "song.flac", "song"])
    def test_non_video_extensions(self, thread, name):
        assert thread._is_video_path(name) is False


class TestAudioExtraction:
    def test_builds_pcm_extraction_command(self, thread, popen, tmp_path):
        extracted = thread._extract_audio_input(str(tmp_path))

        assert extracted == os.path.join(str(tmp_path), "audio_separator_input.wav")
        cmd = popen["cmd"]
        assert cmd[0] == FFMPEG
        assert "-vn" in cmd
        assert cmd[cmd.index("-acodec") + 1] == "pcm_s16le"
        assert cmd[cmd.index("-ar") + 1] == "44100"

    def test_failed_extraction_returns_none(self, thread, popen, tmp_path):
        popen["process"] = FakeProcess(lines=["ffmpeg: invalid data\n"], returncode=1)

        assert thread._extract_audio_input(str(tmp_path)) is None


class TestAudioSeparatorBackend:
    @pytest.fixture(autouse=True)
    def resolved_command(self, monkeypatch):
        monkeypatch.setattr(
            AudioSeparatorThread, "_resolve_audio_separator_command", lambda self: ["/bin/audio-separator"]
        )

    def test_both_stems_are_requested_with_custom_names(self, thread, popen, tmp_path):
        ok, err, instrumental, vocals = thread._run_separator_backend("/tmp/in.wav", str(tmp_path))

        cmd = popen["cmd"]
        assert ok is True and err == ""
        assert cmd[:2] == ["/bin/audio-separator", "/tmp/in.wav"]
        assert "--single_stem" not in cmd
        assert json.loads(cmd[cmd.index("--custom_output_names") + 1]) == {
            "Instrumental": "song_instrumental",
            "Vocals": "song_vocals",
        }
        assert instrumental.endswith("song_instrumental.wav")
        assert vocals.endswith("song_vocals.wav")

    @pytest.mark.parametrize(
        "target_mode, stem",
        [("instrumental_only", "Instrumental"), ("vocals_only", "Vocals")],
    )
    def test_single_stem_modes(self, tmp_path, qapp, popen, target_mode, stem):
        thread = make_thread(tmp_path, target_mode=target_mode)

        thread._run_separator_backend("/tmp/in.wav", str(tmp_path))

        cmd = popen["cmd"]
        assert cmd[cmd.index("--single_stem") + 1] == stem
        assert list(json.loads(cmd[cmd.index("--custom_output_names") + 1])) == [stem]

    def test_fast_mode_reduces_mdx_overlap_for_onnx_models(self, tmp_path, qapp, popen):
        thread = make_thread(tmp_path, fast_mode=True)

        thread._run_separator_backend("/tmp/in.wav", str(tmp_path))

        assert popen["cmd"][popen["cmd"].index("--mdx_overlap") + 1] == "0.1"

    def test_fast_mode_is_ignored_for_non_onnx_models(self, tmp_path, qapp, popen):
        thread = make_thread(tmp_path, fast_mode=True, model_filename="model.ckpt")

        thread._run_separator_backend("/tmp/in.wav", str(tmp_path))

        assert "--mdx_overlap" not in popen["cmd"]

    def test_backend_failure_is_reported(self, thread, popen, tmp_path):
        popen["process"] = FakeProcess(lines=["model missing\n"], returncode=1)

        ok, err, _, _ = thread._run_separator_backend("/tmp/in.wav", str(tmp_path))

        assert ok is False
        assert "model missing" in err


class TestCommandResolution:
    def test_missing_command_is_reported_to_caller(self, thread, tmp_path, monkeypatch):
        monkeypatch.setattr(AudioSeparatorThread, "_resolve_audio_separator_command", lambda self: None)

        ok, err, instrumental, vocals = thread._run_separator_backend("/tmp/in.wav", str(tmp_path))

        assert ok is False
        assert "audio-separator could not be found" in err
        assert (instrumental, vocals) == ("", "")

    def test_interpreter_local_script_is_preferred(self, thread, tmp_path, monkeypatch):
        script = tmp_path / "audio-separator"
        script.write_text("#!/bin/sh\n", encoding="utf-8")
        monkeypatch.setattr(separator_module.sys, "executable", str(tmp_path / "python"))

        assert thread._resolve_audio_separator_command() == [str(script)]

    def test_path_lookup_is_used_next(self, thread, tmp_path, monkeypatch):
        monkeypatch.setattr(separator_module.sys, "executable", str(tmp_path / "empty" / "python"))
        monkeypatch.setattr(separator_module.shutil, "which", lambda name: "/usr/bin/audio-separator")

        assert thread._resolve_audio_separator_command() == ["/usr/bin/audio-separator"]

    def test_module_fallback_is_used_when_script_is_missing(self, thread, tmp_path, monkeypatch):
        monkeypatch.setattr(separator_module.sys, "executable", str(tmp_path / "empty" / "python"))
        monkeypatch.setattr(separator_module.shutil, "which", lambda name: None)
        monkeypatch.setitem(sys.modules, "audio_separator", object())

        assert thread._resolve_audio_separator_command() == [
            str(tmp_path / "empty" / "python"),
            "-m",
            "audio_separator",
        ]

    def test_returns_none_when_package_is_absent(self, thread, tmp_path, monkeypatch):
        monkeypatch.setattr(separator_module.sys, "executable", str(tmp_path / "empty" / "python"))
        monkeypatch.setattr(separator_module.shutil, "which", lambda name: None)
        monkeypatch.setitem(sys.modules, "audio_separator", None)

        assert thread._resolve_audio_separator_command() is None


class TestExportOutputs:
    def _stem(self, tmp_path, name):
        path = tmp_path / name
        path.write_bytes(b"RIFF")
        return str(path)

    def test_wav_to_wav_is_copied_without_ffmpeg(self, thread, tmp_path, monkeypatch):
        monkeypatch.setattr(
            AudioSeparatorThread, "_run_cmd", lambda self, cmd: pytest.fail("ffmpeg should not run")
        )
        src = self._stem(tmp_path, "src.wav")
        dst = str(tmp_path / "out.wav")

        thread._export_one(src, dst, "wav")

        assert os.path.exists(dst)

    @pytest.mark.parametrize(
        "out_fmt, expected_codec", [("wav", "pcm_s16le"), ("flac", "flac"), ("mp3", "libmp3lame")]
    )
    def test_transcoding_codecs(self, thread, tmp_path, popen, out_fmt, expected_codec):
        src = self._stem(tmp_path, "src.flac")

        thread._export_one(src, str(tmp_path / f"out.{out_fmt}"), out_fmt)

        assert popen["cmd"][popen["cmd"].index("-c:a") + 1] == expected_codec

    def test_unsupported_format_raises(self, thread, tmp_path):
        with pytest.raises(RuntimeError, match="Unsupported output format"):
            thread._export_one(self._stem(tmp_path, "src.flac"), "/out.ogg", "ogg")

    def test_export_failure_raises(self, thread, tmp_path, popen):
        popen["process"] = FakeProcess(lines=["encoder error\n"], returncode=1)

        with pytest.raises(RuntimeError, match="Failed to export"):
            thread._export_one(self._stem(tmp_path, "src.flac"), str(tmp_path / "out.mp3"), "mp3")

    def test_both_stems_are_exported(self, thread, tmp_path):
        instrumental = self._stem(tmp_path, "inst.wav")
        vocals = self._stem(tmp_path, "voc.wav")

        instrumental_out, vocals_out = thread._export_outputs("song", instrumental, vocals, "wav")

        assert instrumental_out.endswith("song_instrumental.wav")
        assert vocals_out.endswith("song_vocals.wav")
        assert os.path.exists(instrumental_out) and os.path.exists(vocals_out)

    def test_target_mode_limits_exported_stems(self, tmp_path, qapp):
        thread = make_thread(tmp_path, target_mode="vocals_only")
        instrumental = self._stem(tmp_path, "inst.wav")
        vocals = self._stem(tmp_path, "voc.wav")

        instrumental_out, vocals_out = thread._export_outputs("song", instrumental, vocals, "wav")

        assert instrumental_out == ""
        assert vocals_out.endswith("song_vocals.wav")

    def test_missing_sources_are_skipped(self, thread, tmp_path):
        assert thread._export_outputs("song", "/gone.wav", "", "wav") == ("", "")


class TestRunCmd:
    def test_output_lines_are_emitted(self, thread, popen, qapp):
        popen["process"] = FakeProcess(lines=["first\n", "\n", "second\n"])
        lines = []
        thread.line_output.connect(lines.append)

        ok, err = thread._run_cmd(["/bin/true"])

        assert (ok, err) == (True, "")
        assert lines == ["first", "second"]
        assert popen["process"].stdout.closed is True

    def test_cancellation_short_circuits(self, thread, popen):
        thread.is_killed = True

        assert thread._run_cmd(["/bin/true"]) == (False, "Operation cancelled")

    def test_failure_returns_output_tail(self, thread, popen, qapp):
        popen["process"] = FakeProcess(lines=[f"line {i}\n" for i in range(40)], returncode=1)

        ok, err = thread._run_cmd(["/bin/false"])

        assert ok is False
        assert err.splitlines()[0] == "line 10"

    def test_launch_failure_is_returned_as_error(self, thread, monkeypatch):
        def _boom(cmd, **kwargs):
            raise OSError("ffmpeg missing")

        monkeypatch.setattr(separator_module.subprocess, "Popen", _boom)

        ok, err = thread._run_cmd(["/bin/true"])

        assert ok is False
        assert "ffmpeg missing" in err


class TestDemucsBackend:
    def _thread(self, tmp_path):
        return make_thread(tmp_path, backend_name="demucs", model_filename="htdemucs")

    def test_subprocess_runner_is_written_and_invoked(self, tmp_path, qapp, popen):
        thread = self._thread(tmp_path)
        popen["process"] = FakeProcess(lines=["DEMUCS_SUBPROCESS_DONE\n"])

        ok, err, instrumental, vocals = thread._run_demucs(str(tmp_path / "in.wav"), str(tmp_path))

        assert (ok, err) == (True, "")
        assert os.path.exists(tmp_path / "demucs_subprocess_runner.py")
        cmd = popen["cmd"]
        assert cmd[0] == sys.executable
        assert cmd[2] == str(tmp_path / "in.wav")
        assert cmd[3] == "htdemucs"
        assert cmd[4] == "0"
        assert cmd[5] == "10"
        assert cmd[6] == "standard"
        assert (instrumental, vocals) == ("", "")

    def test_existing_stems_are_returned(self, tmp_path, qapp, popen):
        thread = self._thread(tmp_path)
        popen["process"] = FakeProcess(lines=["DEMUCS_SUBPROCESS_DONE\n"])
        (tmp_path / "in_vocals.wav").write_bytes(b"data")
        (tmp_path / "in_no_vocals.wav").write_bytes(b"data")

        _, _, instrumental, vocals = thread._run_demucs(str(tmp_path / "in.wav"), str(tmp_path))

        assert instrumental.endswith("in_no_vocals.wav")
        assert vocals.endswith("in_vocals.wav")

    def test_fast_mode_flag_is_passed_through(self, tmp_path, qapp, popen):
        thread = make_thread(tmp_path, backend_name="demucs", fast_mode=True, demucs_music_recovery=25, demucs_recovery_mode="side_heavy")
        popen["process"] = FakeProcess()

        thread._run_demucs(str(tmp_path / "in.wav"), str(tmp_path))

        assert popen["cmd"][4:7] == ["1", "25", "side_heavy"]

    def test_download_progress_is_mapped_to_setup_band(self, tmp_path, qapp, popen):
        thread = self._thread(tmp_path)
        popen["process"] = FakeProcess(lines=["Downloading: htdemucs.th\n", "  50%\n"])
        progress, statuses = [], []
        thread.progress.connect(progress.append)
        thread.status_update.connect(statuses.append)

        thread._run_demucs(str(tmp_path / "in.wav"), str(tmp_path))

        assert 53 in progress
        assert any("Downloading Demucs model files (file 1)... 50%" == s for s in statuses)

    def test_separation_progress_is_mapped_to_processing_band(self, tmp_path, qapp, popen):
        thread = self._thread(tmp_path)
        popen["process"] = FakeProcess(lines=["Running Demucs apply_model(...)\n", " 50%\n"])
        progress = []
        thread.progress.connect(progress.append)

        thread._run_demucs(str(tmp_path / "in.wav"), str(tmp_path))

        assert 74 in progress

    def test_pass_totals_are_read_from_worker_output(self, tmp_path, qapp, popen):
        thread = self._thread(tmp_path)
        popen["process"] = FakeProcess(
            lines=["DEMUCS_PASS_TOTAL=4\n", "DEMUCS_EXPECTED_PASSES=8\n", " 10%\n"]
        )
        statuses = []
        thread.status_update.connect(statuses.append)

        thread._run_demucs(str(tmp_path / "in.wav"), str(tmp_path))

        assert any("pass 1/8" in s for s in statuses)

    def test_bag_of_models_line_sets_pass_total(self, tmp_path, qapp, popen):
        thread = self._thread(tmp_path)
        popen["process"] = FakeProcess(lines=["Selected model is a bag of 4 models\n", "Separating track\n"])
        statuses = []
        thread.status_update.connect(statuses.append)

        thread._run_demucs(str(tmp_path / "in.wav"), str(tmp_path))

        assert any("pass 1/4" in s for s in statuses)

    def test_progress_wrap_around_advances_the_pass_counter(self, tmp_path, qapp, popen):
        thread = self._thread(tmp_path)
        popen["process"] = FakeProcess(lines=[" 90%\n", " 10%\n"])
        statuses = []
        thread.status_update.connect(statuses.append)

        thread._run_demucs(str(tmp_path / "in.wav"), str(tmp_path))

        assert any("pass 2/2" in s for s in statuses)

    def test_recovery_blend_phase_is_reported(self, tmp_path, qapp, popen):
        thread = self._thread(tmp_path)
        popen["process"] = FakeProcess(lines=["Applying Demucs music recovery blend: 10% mode=standard\n"])
        statuses = []
        thread.status_update.connect(statuses.append)

        thread._run_demucs(str(tmp_path / "in.wav"), str(tmp_path))

        assert "Applying music recovery blend..." in statuses

    def test_cancellation_stops_the_loop(self, tmp_path, qapp, popen):
        thread = self._thread(tmp_path)
        thread.is_killed = True

        assert thread._run_demucs(str(tmp_path / "in.wav"), str(tmp_path)) == (False, "Operation cancelled", "", "")

    def test_worker_crash_returns_output_tail(self, tmp_path, qapp, popen):
        thread = self._thread(tmp_path)
        popen["process"] = FakeProcess(lines=["Traceback...\n", "RuntimeError: boom\n"], returncode=2)

        ok, err, _, _ = thread._run_demucs(str(tmp_path / "in.wav"), str(tmp_path))

        assert ok is False
        assert "Demucs subprocess failed" in err
        assert "RuntimeError: boom" in err

    def test_unwritable_temp_dir_is_reported(self, tmp_path, qapp):
        thread = self._thread(tmp_path)

        ok, err, _, _ = thread._run_demucs(str(tmp_path / "in.wav"), str(tmp_path / "missing"))

        assert ok is False
        assert err


class TestRun:
    @pytest.fixture
    def stub_backend(self, monkeypatch, tmp_path):
        """Route separation through a stub backend that produces ready-made stems."""
        calls = {}

        def fake_backend(self, prepared_audio, temp_dir):
            calls["prepared_audio"] = prepared_audio
            instrumental = os.path.join(temp_dir, "inst.wav")
            vocals = os.path.join(temp_dir, "voc.wav")
            shutil.copyfile(self.input_path, instrumental)
            shutil.copyfile(self.input_path, vocals)
            return True, "", instrumental, vocals

        monkeypatch.setattr(AudioSeparatorThread, "_run_separator_backend", fake_backend)
        return calls

    def test_successful_run_emits_exported_paths(self, tmp_path, qapp, stub_backend):
        media = tmp_path / "song.mp3"
        media.write_bytes(b"data")
        thread = make_thread(tmp_path)
        results = []
        thread.separator_done.connect(lambda *args: results.append(args))

        thread.run()

        success, instrumental, vocals, error = results[0]
        assert success is True and error == ""
        assert instrumental.endswith("song_instrumental.wav")
        assert vocals.endswith("song_vocals.wav")

    def test_video_input_is_converted_first(self, tmp_path, qapp, stub_backend, monkeypatch):
        media = tmp_path / "clip.mp4"
        media.write_bytes(b"data")
        thread = make_thread(tmp_path, input_path=str(media))
        monkeypatch.setattr(
            AudioSeparatorThread,
            "_extract_audio_input",
            lambda self, temp_dir: shutil.copyfile(self.input_path, os.path.join(temp_dir, "prepared.wav")),
        )
        results = []
        thread.separator_done.connect(lambda *args: results.append(args))

        thread.run()

        assert stub_backend["prepared_audio"].endswith("prepared.wav")
        assert results[0][0] is True

    def test_failed_extraction_aborts_run(self, tmp_path, qapp, monkeypatch):
        media = tmp_path / "clip.mp4"
        media.write_bytes(b"data")
        thread = make_thread(tmp_path, input_path=str(media))
        monkeypatch.setattr(AudioSeparatorThread, "_extract_audio_input", lambda self, temp_dir: None)
        results = []
        thread.separator_done.connect(lambda *args: results.append(args))

        thread.run()

        assert results[0] == (False, "", "", "Failed to extract audio from video input")

    def test_cancellation_before_separation_is_reported(self, tmp_path, qapp, monkeypatch):
        media = tmp_path / "song.mp3"
        media.write_bytes(b"data")
        thread = make_thread(tmp_path)
        thread.is_killed = True
        results = []
        thread.separator_done.connect(lambda *args: results.append(args))

        thread.run()

        assert results[0] == (False, "", "", "Operation cancelled")

    def test_backend_failure_is_forwarded(self, tmp_path, qapp, monkeypatch):
        media = tmp_path / "song.mp3"
        media.write_bytes(b"data")
        thread = make_thread(tmp_path)
        monkeypatch.setattr(
            AudioSeparatorThread,
            "_run_separator_backend",
            lambda self, prepared_audio, temp_dir: (False, "model crashed", "inst", "voc"),
        )
        results = []
        thread.separator_done.connect(lambda *args: results.append(args))

        thread.run()

        assert results[0] == (False, "inst", "voc", "model crashed")

    def test_unexpected_error_is_reported(self, tmp_path, qapp, monkeypatch):
        media = tmp_path / "song.mp3"
        media.write_bytes(b"data")
        thread = make_thread(tmp_path)

        def _boom(self, prepared_audio, temp_dir):
            raise RuntimeError("unexpected")

        monkeypatch.setattr(AudioSeparatorThread, "_run_separator_backend", _boom)
        results = []
        thread.separator_done.connect(lambda *args: results.append(args))

        thread.run()

        assert results[0] == (False, "", "", "unexpected")
