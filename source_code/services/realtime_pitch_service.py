import subprocess
import threading

import numpy as np


class RealtimePitchService:
    """Real-time pitch-shift playback using FFmpeg filter graph + sounddevice output."""

    def __init__(self, ffmpeg_path: str = "ffmpeg", error_callback=None):
        self.ffmpeg_path = ffmpeg_path
        self.error_callback = error_callback
        self.current_path: str = ""
        self.pitch_semitones: float = 0.0
        self.playback_speed: float = 1.0
        self.gain_factor: float = 1.0

        self._sample_rate = 48000
        self._channels = 2
        self._block_frames = 1024

        self._ffmpeg_proc = None
        self._play_thread = None
        self._stop_event = threading.Event()

        self._active = False
        self._start_seconds = 0.0

    def load_file(self, path: str):
        self.current_path = path

    def _report_error(self, message: str):
        print(f"[RealtimePitchService] {message}")
        if callable(self.error_callback):
            try:
                self.error_callback(message)
            except Exception as exc:
                print(f"[RealtimePitchService] error_callback raised: {exc}")

    def set_pitch(self, semitones: float):
        self.pitch_semitones = float(semitones)

    def set_speed(self, speed: float):
        try:
            value = float(speed)
        except Exception:
            value = 1.0
        self.playback_speed = max(0.5, min(2.0, value))

    def set_gain(self, factor: float):
        try:
            value = float(factor)
        except Exception:
            value = 1.0
        self.gain_factor = max(0.01, min(10.0, value))

    def _build_atempo_chain(self, target: float) -> str:
        """Build an ffmpeg atempo chain that supports values outside [0.5, 2.0]."""
        factors = []
        value = max(0.01, float(target))

        while value > 2.0:
            factors.append(2.0)
            value /= 2.0

        while value < 0.5:
            factors.append(0.5)
            value /= 0.5

        factors.append(value)
        return ",".join(f"atempo={f:.6f}" for f in factors)

    def is_active(self) -> bool:
        return self._active

    def stop(self):
        self._stop_event.set()
        self._active = False

        if self._ffmpeg_proc is not None:
            try:
                self._ffmpeg_proc.kill()
            except Exception:
                pass
            self._ffmpeg_proc = None

        if self._play_thread and self._play_thread.is_alive():
            self._play_thread.join(timeout=1.0)
        self._play_thread = None

    def play_shifted(self, start_seconds: float = 0.0):
        if not self.current_path:
            raise ValueError("No media file loaded")

        self.stop()
        self._stop_event.clear()
        self._active = True
        self._start_seconds = max(0.0, float(start_seconds or 0.0))
        self._play_thread = threading.Thread(target=self._play_worker, daemon=True)
        self._play_thread.start()

    def _play_worker(self):
        try:
            import sounddevice as sd
        except Exception as exc:
            self._active = False
            self._report_error(f"sounddevice import error: {exc}")
            return

        pf = float(2 ** (self.pitch_semitones / 12.0))
        speed = float(self.playback_speed)
        audio_filters = [f"rubberband=pitch={pf:.8f}:tempo={speed:.8f}"]
        gain = float(self.gain_factor)
        if abs(gain - 1.0) > 0.001:
            audio_filters.append(f"volume={gain:.4f}")
            if gain > 1.0:
                audio_filters.append("alimiter=limit=0.98:attack=5:release=50")
        audio_filter = ",".join(audio_filters)

        cmd = [
            self.ffmpeg_path,
            "-hide_banner",
            "-loglevel",
            "error",
            "-ss",
            f"{self._start_seconds:.3f}",
            "-i",
            self.current_path,
            "-vn",
            "-ac",
            str(self._channels),
            "-ar",
            str(self._sample_rate),
            "-af",
            audio_filter,
            "-f",
            "f32le",
            "pipe:1",
        ]

        startupinfo = None
        if hasattr(subprocess, "STARTUPINFO"):
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                startupinfo=startupinfo,
            )
            self._ffmpeg_proc = process
        except Exception as exc:
            self._active = False
            self._report_error(f"ffmpeg start error: {exc}")
            return

        bytes_per_frame = self._channels * 4
        chunk_bytes = self._block_frames * bytes_per_frame

        try:
            stream = sd.OutputStream(
                samplerate=self._sample_rate,
                channels=self._channels,
                dtype="float32",
                blocksize=self._block_frames,
                latency="low",
            )
            stream.start()
        except Exception as exc:
            self._active = False
            self._report_error(f"output stream error: {exc}")
            try:
                process.kill()
            except Exception:
                pass
            self._ffmpeg_proc = None
            return

        try:
            while not self._stop_event.is_set():
                if process.poll() is not None:
                    break

                raw = process.stdout.read(chunk_bytes)
                if not raw:
                    break

                out_arr = np.frombuffer(raw, dtype=np.float32)
                if out_arr.size == 0:
                    continue
                frames = out_arr.size // self._channels
                if frames <= 0:
                    continue
                stream.write(out_arr[:frames * self._channels].reshape(-1, self._channels))
            if not self._stop_event.is_set():
                try:
                    returncode = process.wait(timeout=1.0)
                except Exception:
                    returncode = process.poll()
                if returncode is not None and returncode != 0:
                    detail = ""
                    try:
                        detail = (process.stderr.read() or b"").decode(errors="replace").strip()
                    except Exception:
                        pass
                    message = f"ffmpeg exited with code {returncode}"
                    if detail:
                        message += f": {detail}"
                    self._report_error(message)
        except Exception as exc:
            self._report_error(f"playback error: {exc}")
        finally:
            try:
                stream.stop()
                stream.close()
            except Exception:
                pass
            try:
                process.kill()
            except Exception:
                pass
            self._ffmpeg_proc = None
            self._active = False
