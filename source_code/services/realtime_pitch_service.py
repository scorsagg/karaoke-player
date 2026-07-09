import subprocess
import threading

import numpy as np


class RealtimePitchService:
    """Real-time pitch-shift playback using FFmpeg filter graph + sounddevice output."""

    def __init__(self, ffmpeg_path: str = "ffmpeg"):
        self.ffmpeg_path = ffmpeg_path
        self.current_path: str = ""
        self.pitch_semitones: float = -2.0

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

    def set_pitch(self, semitones: float):
        self.pitch_semitones = float(semitones)

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
            print(f"[RealtimePitchService] sounddevice import error: {exc}")
            return

        pf = float(2 ** (self.pitch_semitones / 12.0))
        pitch_comp = max(0.5, min(2.0, 1.0 / pf))

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
            f"asetrate={self._sample_rate}*{pf:.8f},aresample={self._sample_rate},atempo={pitch_comp:.6f}",
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
            print(f"[RealtimePitchService] ffmpeg start error: {exc}")
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
            print(f"[RealtimePitchService] output stream error: {exc}")
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
        except Exception as exc:
            print(f"[RealtimePitchService] playback error: {exc}")
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
