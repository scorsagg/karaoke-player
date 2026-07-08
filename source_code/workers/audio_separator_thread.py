from PySide6.QtCore import QThread, Signal
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile


class AudioSeparatorThread(QThread):
    progress = Signal(int)
    status_update = Signal(str)
    line_output = Signal(str)
    separator_done = Signal(bool, str, str, str)

    def __init__(self, input_path, ffmpeg_path, output_dir, backend_name, model_filename, output_format, target_mode, fast_mode, model_file_dir, demucs_music_recovery=10):
        super().__init__()
        self.input_path = input_path
        self.ffmpeg_path = ffmpeg_path
        self.output_dir = output_dir
        self.backend_name = backend_name
        self.model_filename = model_filename
        self.output_format = output_format.lower()
        self.target_mode = target_mode
        self.fast_mode = fast_mode
        self.model_file_dir = model_file_dir
        self.demucs_music_recovery = max(0, min(30, int(demucs_music_recovery)))
        self.is_killed = False
        self.process = None

    def run(self):
        temp_dir = tempfile.mkdtemp(prefix="audio_separator_", dir=self.output_dir)
        prepared_audio = self.input_path

        try:
            self.progress.emit(5)
            self.status_update.emit("Preparing separator input...")

            if self._is_video_path(self.input_path) or self.backend_name == "demucs":
                prepared_audio = self._extract_audio_input(temp_dir)
                if not prepared_audio:
                    self.separator_done.emit(False, "", "", "Failed to extract audio from video input")
                    return

            if self.is_killed:
                self.separator_done.emit(False, "", "", "Operation cancelled")
                return

            self.progress.emit(35)
            self.status_update.emit(f"Running {self.backend_name} separation model...")

            ok, err, instrumental_src, vocals_src = self._run_separator_backend(prepared_audio, temp_dir)
            if not ok:
                self.separator_done.emit(False, instrumental_src, vocals_src, err)
                return

            instrumental_path, vocals_path = self._export_outputs(
                os.path.splitext(os.path.basename(self.input_path))[0],
                instrumental_src,
                vocals_src,
                self.output_format,
            )

            self.progress.emit(100)
            self.status_update.emit("Audio separation complete")
            self.separator_done.emit(True, instrumental_path, vocals_path, "")
        except Exception as exc:
            self.separator_done.emit(False, "", "", str(exc))
        finally:
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass

    def stop(self):
        self.is_killed = True
        if self.process:
            try:
                self.process.terminate()
                self.process.kill()
            except Exception:
                pass

    def _is_video_path(self, path):
        ext = os.path.splitext(path)[1].lower()
        return ext in {".mp4", ".mkv", ".avi", ".mov", ".webm", ".mpeg", ".mts", ".m2ts"}

    def _extract_audio_input(self, temp_dir):
        self.status_update.emit("Extracting audio from video for separation...")
        self.progress.emit(20)

        extracted = os.path.join(temp_dir, "audio_separator_input.wav")
        cmd = [
            self.ffmpeg_path,
            "-y",
            "-i",
            self.input_path,
            "-vn",
            "-ac",
            "2",
            "-ar",
            "44100",
            "-acodec",
            "pcm_s16le",
            extracted,
        ]
        ok, err = self._run_cmd(cmd)
        if not ok:
            self.line_output.emit(err)
            return None
        return extracted

    def _run_separator_backend(self, prepared_audio, temp_dir):
        if self.backend_name == "demucs":
            return self._run_demucs(prepared_audio, temp_dir)
        return self._run_audio_separator(prepared_audio, temp_dir)

    def _run_audio_separator(self, prepared_audio, temp_dir):
        cmd_prefix = self._resolve_audio_separator_command()
        if not cmd_prefix:
            return False, (
                "audio-separator could not be found for the active Python environment. "
                "Make sure it is installed in the selected interpreter or available on PATH."
            ), "", ""

        base_name = os.path.splitext(os.path.basename(self.input_path))[0]
        instrumental_name = f"{base_name}_instrumental"
        vocals_name = f"{base_name}_vocals"
        custom_names = {}

        single_stem = None
        if self.target_mode == "instrumental_only":
            single_stem = "Instrumental"
            custom_names["Instrumental"] = instrumental_name
        elif self.target_mode == "vocals_only":
            single_stem = "Vocals"
            custom_names["Vocals"] = vocals_name
        else:
            custom_names["Instrumental"] = instrumental_name
            custom_names["Vocals"] = vocals_name

        cmd = cmd_prefix + [
            prepared_audio,
            "--model_filename",
            self.model_filename,
            "--output_format",
            "wav",
            "--output_dir",
            temp_dir,
            "--model_file_dir",
            self.model_file_dir,
            "--sample_rate",
            "44100",
            "--custom_output_names",
            json.dumps(custom_names),
            "--log_level",
            "info",
        ]

        if single_stem:
            cmd += ["--single_stem", single_stem]

        if self.fast_mode and self.model_filename.lower().endswith(".onnx"):
            cmd += ["--mdx_overlap", "0.1"]

        ok, err = self._run_cmd(cmd)
        instrumental_path = os.path.join(temp_dir, f"{instrumental_name}.wav")
        vocals_path = os.path.join(temp_dir, f"{vocals_name}.wav")
        return ok, err, instrumental_path, vocals_path

    def _run_demucs(self, prepared_audio, temp_dir):
        try:
            self.progress.emit(40)
            self.status_update.emit(f"Loading Demucs model ({self.model_filename})...")
            track_name = os.path.splitext(os.path.basename(prepared_audio))[0]
            vocals_path = os.path.join(temp_dir, f"{track_name}_vocals.wav")
            instrumental_path = os.path.join(temp_dir, f"{track_name}_no_vocals.wav")

            demucs_script = os.path.join(temp_dir, "demucs_subprocess_runner.py")
            script_source = '''
import os
import sys
import traceback

import soundfile as sf
import torch
from demucs.apply import apply_model
from demucs.pretrained import get_model

def main():
    if len(sys.argv) != 8:
        raise RuntimeError("demucs_subprocess_runner expected 7 args")

    prepared_audio = sys.argv[1]
    model_name = sys.argv[2]
    fast_mode = sys.argv[3] == "1"
    recovery_percent = max(0, min(30, int(sys.argv[4])))
    instrumental_path = sys.argv[5]
    vocals_path = sys.argv[6]
    status_hint_path = sys.argv[7]

    with open(status_hint_path, "w", encoding="utf-8") as hint_file:
        hint_file.write("demucs_subprocess_started")

    model = get_model(model_name)
    model.cpu()
    model.eval()

    pass_total = 1
    try:
        if hasattr(model, "models") and model.models is not None:
            pass_total = max(1, len(model.models))
    except Exception:
        pass_total = 1
    print(f"DEMUCS_PASS_TOTAL={pass_total}", flush=True)

    wav_np, sr = sf.read(prepared_audio, always_2d=True, dtype="float32")
    if sr != int(model.samplerate):
        raise RuntimeError(f"Prepared audio sample rate {sr} does not match Demucs model samplerate {model.samplerate}")

    wav = torch.from_numpy(wav_np.T).to(torch.float32)
    ref = wav.mean(0)
    wav = wav - ref.mean()
    std = ref.std()
    if float(std) > 0:
        wav = wav / std
    else:
        std = torch.tensor(1.0, dtype=wav.dtype)

    shifts = 1 if fast_mode else 2
    overlap = 0.1 if fast_mode else 0.25
    segment = 8 if fast_mode else None

    print(f"Running Demucs apply_model(name={model_name}, shifts={shifts}, overlap={overlap}, segment={segment})", flush=True)
    with torch.no_grad():
        sources = apply_model(
            model,
            wav[None],
            device="cpu",
            shifts=shifts,
            split=True,
            overlap=overlap,
            progress=True,
            num_workers=0,
            segment=segment,
        )[0]

    if float(std) > 0:
        sources = sources * std
    sources = sources + ref.mean()

    source_map = {name: sources[idx] for idx, name in enumerate(model.sources)}
    if "vocals" not in source_map:
        raise RuntimeError(f"Demucs model sources did not include vocals: {model.sources}")

    vocals_tensor = source_map["vocals"]
    non_vocal_sources = [tensor for name, tensor in source_map.items() if name != "vocals"]
    instrumental_tensor = torch.stack(non_vocal_sources, dim=0).sum(dim=0) if non_vocal_sources else None

    vocals_np = vocals_tensor.detach().cpu().transpose(0, 1).numpy()
    sf.write(vocals_path, vocals_np, sr)

    if instrumental_tensor is not None:
        instrumental_np = instrumental_tensor.detach().cpu().transpose(0, 1).numpy()
        recovery_ratio = float(recovery_percent) / 100.0
        if recovery_ratio > 0:
            print(f"Applying Demucs music recovery blend: {recovery_percent}% original mix into instrumental", flush=True)
            instrumental_np = ((1.0 - recovery_ratio) * instrumental_np) + (recovery_ratio * wav_np)
            instrumental_np = instrumental_np.clip(-1.0, 1.0)
        sf.write(instrumental_path, instrumental_np, sr)

    print("DEMUCS_SUBPROCESS_DONE", flush=True)

if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(2)
'''
            with open(demucs_script, "w", encoding="utf-8") as script_file:
                script_file.write(script_source)

            status_hint_path = os.path.join(temp_dir, "demucs_subprocess_status.txt")
            cmd = [
                sys.executable,
                demucs_script,
                prepared_audio,
                self.model_filename,
                "1" if self.fast_mode else "0",
                str(self.demucs_music_recovery),
                instrumental_path,
                vocals_path,
                status_hint_path,
            ]

            self.status_update.emit("Running Demucs separation...")
            output_lines = []
            demucs_phase = "startup"
            download_round = 0
            separation_pass = 1
            separation_total = 1
            last_separation_percent = -1

            startupinfo = None
            creationflags = 0
            if sys.platform == "win32":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = 0
                creationflags = 0x08000000

            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                startupinfo=startupinfo,
                creationflags=creationflags,
            )

            while True:
                if self.is_killed:
                    return False, "Operation cancelled", "", ""

                line = self.process.stdout.readline()
                if not line and self.process.poll() is not None:
                    break
                if not line:
                    continue

                line = line.strip()
                if not line:
                    continue

                output_lines.append(line)
                self.line_output.emit(line)

                lower_line = line.lower()
                if "downloading:" in lower_line:
                    demucs_phase = "download"
                    download_round += 1
                    self.status_update.emit(f"Downloading Demucs model files (file {download_round})...")
                elif "bag of" in lower_line and "models" in lower_line:
                    bag_match = re.search(r"bag of\s+(\d+)\s+models", lower_line)
                    if bag_match:
                        try:
                            separation_total = max(1, int(bag_match.group(1)))
                        except Exception:
                            separation_total = 1
                elif "running demucs apply_model" in lower_line or "separating track" in lower_line:
                    demucs_phase = "separation"
                    self.status_update.emit(f"Running Demucs separation (pass {separation_pass}/{separation_total})...")
                elif "applying demucs music recovery blend" in lower_line:
                    demucs_phase = "recovery"
                    self.status_update.emit("Applying music recovery blend...")

                pass_total_match = re.search(r"demucs_pass_total=(\d+)", lower_line)
                if pass_total_match:
                    try:
                        separation_total = max(1, int(pass_total_match.group(1)))
                        self.status_update.emit(f"Running Demucs separation (pass {separation_pass}/{separation_total})...")
                    except Exception:
                        separation_total = 1

                match = re.search(r"(\d{1,3})%", line)
                if match:
                    percent = max(0, min(100, int(match.group(1))))
                    if demucs_phase == "download":
                        ui_progress = 48 + int(percent * 0.10)
                        self.progress.emit(min(ui_progress, 58))
                        self.status_update.emit(
                            f"Downloading Demucs model files (file {download_round})... {percent}%"
                        )
                    else:
                        demucs_phase = "separation"
                        if last_separation_percent >= 80 and percent <= 20:
                            separation_pass += 1
                        if separation_pass > separation_total:
                            separation_pass = separation_total
                        last_separation_percent = percent

                        ui_progress = 60 + int(percent * 0.28)
                        self.progress.emit(min(ui_progress, 88))
                        self.status_update.emit(
                            f"Running Demucs separation (pass {separation_pass}/{separation_total})... {percent}%"
                        )

            if self.process.returncode != 0:
                tail = "\n".join(output_lines[-40:])
                return False, (
                    "Demucs subprocess failed. The app stayed alive, but Demucs crashed in its isolated worker process.\n"
                    + tail
                ), "", ""

            self.progress.emit(95)
            self.status_update.emit("Writing separated stems...")

            instrumental_out = instrumental_path if os.path.exists(instrumental_path) else ""
            vocals_out = vocals_path if os.path.exists(vocals_path) else ""
            return True, "", instrumental_out, vocals_out
        except Exception as exc:
            return False, str(exc), "", ""

    def _resolve_audio_separator_command(self):
        candidates = []

        python_dir = os.path.dirname(sys.executable)
        candidates.append(os.path.join(python_dir, "Scripts", "audio-separator.exe"))
        candidates.append(os.path.join(python_dir, "Scripts", "audio-separator"))
        candidates.append(os.path.join(python_dir, "audio-separator.exe"))
        candidates.append(os.path.join(python_dir, "audio-separator"))

        for candidate in candidates:
            if candidate and os.path.exists(candidate):
                return [candidate]

        path_exe = shutil.which("audio-separator")
        if path_exe:
            return [path_exe]

        # Module fallback for environments where the console script is missing but the package is installed.
        try:
            __import__("audio_separator")
            return [sys.executable, "-m", "audio_separator"]
        except Exception:
            return None

    def _export_outputs(self, base_name, instrumental_src, vocals_src, out_fmt):
        instrumental_out = ""
        vocals_out = ""

        if instrumental_src and os.path.exists(instrumental_src) and self.target_mode in {"instrumental_only", "both"}:
            instrumental_out = os.path.join(self.output_dir, f"{base_name}_instrumental.{out_fmt}")
            self._export_one(instrumental_src, instrumental_out, out_fmt)

        if vocals_src and os.path.exists(vocals_src) and self.target_mode in {"vocals_only", "both"}:
            vocals_out = os.path.join(self.output_dir, f"{base_name}_vocals.{out_fmt}")
            self._export_one(vocals_src, vocals_out, out_fmt)

        return instrumental_out, vocals_out

    def _export_one(self, src, dst, out_fmt):
        src_ext = os.path.splitext(src)[1].lower()
        if out_fmt == "wav" and src_ext == ".wav":
            shutil.copy2(src, dst)
            return

        if out_fmt == "wav":
            cmd = [self.ffmpeg_path, "-y", "-i", src, "-c:a", "pcm_s16le", "-ar", "44100", dst]
        elif out_fmt == "flac":
            cmd = [self.ffmpeg_path, "-y", "-i", src, "-c:a", "flac", dst]
        elif out_fmt == "mp3":
            cmd = [self.ffmpeg_path, "-y", "-i", src, "-c:a", "libmp3lame", "-b:a", "320k", dst]
        else:
            raise RuntimeError(f"Unsupported output format: {out_fmt}")

        ok, err = self._run_cmd(cmd)
        if not ok:
            raise RuntimeError(f"Failed to export {os.path.basename(dst)}: {err}")

    def _run_cmd(self, cmd):
        output_lines = []
        try:
            startupinfo = None
            creationflags = 0
            if sys.platform == "win32":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = 0
                creationflags = 0x08000000

            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                startupinfo=startupinfo,
                creationflags=creationflags,
            )

            while True:
                if self.is_killed:
                    return False, "Operation cancelled"

                line = self.process.stdout.readline()
                if not line and self.process.poll() is not None:
                    break
                if not line:
                    continue

                line = line.strip()
                if not line:
                    continue
                output_lines.append(line)
                self.line_output.emit(line)

            if self.process.returncode != 0:
                return False, "\n".join(output_lines[-30:])
            return True, ""
        except Exception as exc:
            return False, str(exc)
        finally:
            if self.process and self.process.stdout:
                try:
                    self.process.stdout.close()
                except Exception:
                    pass