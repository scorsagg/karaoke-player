from PySide6.QtCore import QThread, Signal
import sounddevice as sd
import numpy as np
import sys
import warnings
import threading

try:
    import soundcard as sc
except Exception:
    sc = None

warnings.filterwarnings("ignore", message="data discontinuity in recording")

NOTE_NAMES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")


def frequency_to_midi_note(frequency_hz):
    """Convert a frequency in Hz to the nearest MIDI note number."""
    if frequency_hz is None or frequency_hz <= 0:
        return None
    return int(round(69 + (12 * np.log2(float(frequency_hz) / 440.0))))


def midi_note_to_name(midi_note):
    """Convert a MIDI note number to a note name like C#4."""
    if midi_note is None:
        return ""
    octave = (int(midi_note) // 12) - 1
    note_name = NOTE_NAMES[int(midi_note) % 12]
    return f"{note_name}{octave}"


def detect_pitch_from_audio(audio_data, sample_rate, min_frequency=55.0, max_frequency=1100.0):
    """Detect the strongest fundamental frequency in a mono audio buffer."""
    if audio_data is None:
        return None

    samples = np.asarray(audio_data, dtype=np.float32).flatten()
    if samples.size < 2048 or sample_rate is None or sample_rate <= 0:
        return None

    # Keep the analysis window small enough for responsive UI updates.
    window_size = min(4096, samples.size)
    window = samples[-window_size:]
    window = window - np.mean(window)

    rms = float(np.sqrt(np.mean(window ** 2)))
    if rms < 0.01:
        return None

    window = window * np.hanning(window.size)
    window = np.append(window[0], window[1:] - 0.97 * window[:-1])

    autocorr = np.correlate(window, window, mode="full")[window.size - 1:]
    if autocorr.size < 3 or autocorr[0] <= 0:
        return None

    min_lag = max(1, int(sample_rate / max_frequency))
    max_lag = min(autocorr.size - 1, int(sample_rate / min_frequency))
    if max_lag <= min_lag:
        return None

    search_slice = autocorr[min_lag:max_lag]
    if search_slice.size == 0:
        return None

    peak_lag = int(np.argmax(search_slice)) + min_lag
    peak_value = float(autocorr[peak_lag] / (autocorr[0] + 1e-12))
    if peak_value < 0.35:
        return None

    # Refine the lag slightly using parabolic interpolation for a steadier note readout.
    refined_lag = float(peak_lag)
    if 1 <= peak_lag < autocorr.size - 1:
        left = float(autocorr[peak_lag - 1])
        center = float(autocorr[peak_lag])
        right = float(autocorr[peak_lag + 1])
        denominator = (2.0 * center) - left - right
        if abs(denominator) > 1e-12:
            refined_lag += 0.5 * (left - right) / denominator

    frequency_hz = float(sample_rate / refined_lag)
    if frequency_hz < min_frequency or frequency_hz > max_frequency:
        return None

    midi_note = frequency_to_midi_note(frequency_hz)
    if midi_note is None:
        return None

    return {
        "frequency_hz": frequency_hz,
        "midi_note": midi_note,
        "note_name": midi_note_to_name(midi_note),
        "confidence": peak_value,
    }


class AudioAnalyzerThread(QThread):
    """Thread to capture and analyze real-time audio output levels"""
    level_updated = Signal(float)  # Emit dB value
    pitch_updated = Signal(float, str, float)  # Emit frequency_hz, note_name, confidence
    clip_warning = Signal()  # Emit when level exceeds 90%
    
    def __init__(self):
        super().__init__()
        self.running = True
        self.is_playing = False
        self.audio_buffer = np.array([], dtype=np.float32)
        self.buffer_size = 4410 
        self.high_level_counter = 0 # Track how long it's been loud
        self.current_samplerate = 44100
        self._buffer_lock = threading.Lock()
        self._last_pitch_note = ""
        self._last_pitch_frequency = 0.0

    def _emit_level_from_buffer(self):
        with self._buffer_lock:
            if len(self.audio_buffer) < self.buffer_size // 2:
                return
            recent_audio = np.array(self.audio_buffer[-self.buffer_size:], copy=True)

        if len(recent_audio) >= self.buffer_size // 2:
            rms = np.sqrt(np.mean(recent_audio ** 2))
            db_level = 20 * np.log10(rms + 1e-10)
            db_level = max(-80.0, min(0.0, db_level))
            self.level_updated.emit(db_level)

    def _emit_pitch_from_buffer(self):
        with self._buffer_lock:
            if len(self.audio_buffer) < self.buffer_size:
                return
            recent_audio = np.array(self.audio_buffer[-self.buffer_size:], copy=True)

        pitch = detect_pitch_from_audio(recent_audio, self.current_samplerate)
        if not pitch:
            if self._last_pitch_note:
                self._last_pitch_note = ""
                self._last_pitch_frequency = 0.0
                self.pitch_updated.emit(0.0, "", 0.0)
            return

        note_name = pitch["note_name"]
        frequency_hz = float(pitch["frequency_hz"])
        confidence = float(pitch["confidence"])

        # Avoid churn by only emitting when the detected note changes or the pitch moves meaningfully.
        if note_name != self._last_pitch_note or abs(frequency_hz - self._last_pitch_frequency) >= 0.75:
            self._last_pitch_note = note_name
            self._last_pitch_frequency = frequency_hz
            self.pitch_updated.emit(frequency_hz, note_name, confidence)

    def _append_audio_data(self, audio_data):
        with self._buffer_lock:
            self.audio_buffer = np.append(self.audio_buffer, audio_data)
            if len(self.audio_buffer) > self.buffer_size * 2:
                self.audio_buffer = self.audio_buffer[-self.buffer_size:]

    def _run_soundcard_loopback(self):
        """Use Windows speaker loopback capture via soundcard when available."""
        if sys.platform != "win32" or sc is None:
            return False

        try:
            speaker = sc.default_speaker()
            if speaker is None:
                print("[AudioAnalyzerThread] soundcard: no default speaker")
                return False

            loopback_mic = sc.get_microphone(speaker.name, include_loopback=True)
            print(f"[AudioAnalyzerThread] soundcard loopback candidate: {speaker.name}")
        except Exception as e:
            print(f"[AudioAnalyzerThread] soundcard loopback init failed: {e}")
            return False

        sample_rates = [48000, 44100]
        channel_options = [2, 1]

        for samplerate in sample_rates:
            self.current_samplerate = samplerate
            for channels in channel_options:
                if not self.running:
                    return True
                try:
                    print(
                        f"[AudioAnalyzerThread] Trying soundcard loopback: "
                        f"speaker={speaker.name}, channels={channels}, samplerate={samplerate}"
                    )
                    with loopback_mic.recorder(samplerate=samplerate, channels=channels, blocksize=2048) as recorder:
                        print("[AudioAnalyzerThread] ✓ soundcard loopback opened")
                        while self.running:
                            data = recorder.record(numframes=2048)
                            if data is None or len(data) == 0:
                                continue

                            if not self.is_playing:
                                continue

                            if data.ndim > 1 and data.shape[1] > 1:
                                audio_data = np.mean(data, axis=1)
                            else:
                                audio_data = data[:, 0] if data.ndim > 1 else data

                            self._append_audio_data(audio_data)
                            self._emit_level_from_buffer()
                            self._emit_pitch_from_buffer()
                        return True
                except Exception as e:
                    print(f"[AudioAnalyzerThread] ❌ soundcard loopback failed: {e}")

        return False

    def _append_unique_config(self, configs, seen, cfg):
        key = (
            cfg.get("label"),
            cfg.get("device"),
            cfg.get("channels"),
            cfg.get("samplerate"),
            cfg.get("blocksize"),
            bool(cfg.get("extra_settings") is not None),
        )
        if key not in seen:
            seen.add(key)
            configs.append(cfg)

    def _get_wasapi_output_candidates(self):
        """Return prioritized WASAPI output device indices for loopback capture on Windows."""
        if sys.platform != "win32":
            return []

        candidates = []
        seen = set()

        try:
            hostapis = sd.query_hostapis()
        except Exception as e:
            print(f"[AudioAnalyzerThread] query_hostapis failed: {e}")
            return []

        wasapi_host_index = None
        for i, hostapi in enumerate(hostapis):
            if "WASAPI" in str(hostapi.get("name", "")).upper():
                wasapi_host_index = i
                break

        if wasapi_host_index is None:
            return []

        # First preference: WASAPI host's default output device.
        try:
            default_wasapi_out = int(hostapis[wasapi_host_index].get("default_output_device", -1))
            if default_wasapi_out >= 0 and default_wasapi_out not in seen:
                seen.add(default_wasapi_out)
                candidates.append(default_wasapi_out)
        except Exception:
            pass

        # Second preference: current global default output if it belongs to WASAPI.
        try:
            global_default_out = sd.default.device[1]
            if global_default_out is not None and global_default_out >= 0:
                info = sd.query_devices(global_default_out)
                if int(info.get("hostapi", -1)) == wasapi_host_index and global_default_out not in seen:
                    seen.add(global_default_out)
                    candidates.append(global_default_out)
        except Exception:
            pass

        # Then try all WASAPI output-capable devices.
        try:
            all_devices = sd.query_devices()
            for idx, dev in enumerate(all_devices):
                if int(dev.get("hostapi", -1)) != wasapi_host_index:
                    continue
                if int(dev.get("max_output_channels", 0)) <= 0:
                    continue
                if idx not in seen:
                    seen.add(idx)
                    candidates.append(idx)
        except Exception as e:
            print(f"[AudioAnalyzerThread] device enumeration failed: {e}")

        return candidates

    def _build_stream_configs(self):
        """Create candidate stream configs with safe fallbacks for diverse devices."""
        configs = []
        seen = set()
        default_input = None

        try:
            default_input = sd.default.device[0]
        except Exception:
            default_input = None

        max_input_channels = 1
        if default_input is not None:
            try:
                info = sd.query_devices(default_input)
                max_input_channels = max(1, int(info.get("max_input_channels", 1)))
            except Exception:
                max_input_channels = 1

        preferred_channel_orders = [2, 1]
        preferred_samplerates = [48000, 44100]

        # Prefer capturing actual playback output on Windows via WASAPI loopback.
        if sys.platform == "win32" and hasattr(sd, "WasapiSettings"):
            # sounddevice 0.5.x does not accept a loopback kwarg in WasapiSettings.
            wasapi_settings = sd.WasapiSettings()
            for dev_idx in self._get_wasapi_output_candidates():
                try:
                    dev_info = sd.query_devices(dev_idx)
                    out_channels = max(1, int(dev_info.get("max_output_channels", 1)))
                    default_sr = int(float(dev_info.get("default_samplerate", 48000)))
                    sample_rates = [default_sr] + [sr for sr in preferred_samplerates if sr != default_sr]

                    for channels in preferred_channel_orders:
                        if channels > out_channels:
                            continue
                        for samplerate in sample_rates:
                            self._append_unique_config(configs, seen, {
                                "device": dev_idx,
                                "channels": channels,
                                "samplerate": samplerate,
                                "blocksize": 2048,
                                "extra_settings": wasapi_settings,
                                "label": f"WASAPI loopback ({dev_info.get('name', dev_idx)})",
                            })
                except Exception as e:
                    print(f"[AudioAnalyzerThread] WASAPI device config error (device={dev_idx}): {e}")

        for channels in preferred_channel_orders:
            if channels > max_input_channels:
                continue
            for samplerate in preferred_samplerates:
                self._append_unique_config(configs, seen, {
                    "device": None,
                    "channels": channels,
                    "samplerate": samplerate,
                    "blocksize": 2048,
                    "extra_settings": None,
                    "label": "Default input",
                })

        if not configs:
            self._append_unique_config(configs, seen, {
                "device": None,
                "channels": 1,
                "samplerate": 44100,
                "blocksize": 2048,
                "extra_settings": None,
                "label": "Fallback input",
            })

        return configs
        
    def set_playing(self, is_playing):
        """Set whether audio should be monitored"""
        self.is_playing = is_playing
        self.silence_count = 0
        
    def audio_callback(self, indata, frames, time, status):
        """Callback for audio stream - capture audio data"""
        if not self.is_playing:
            return
        if status:
            print(f"[AudioAnalyzerThread] stream status: {status}")
        try:
            # Get mono mix of audio
            if indata.ndim > 1 and indata.shape[1] > 1:
                audio_data = np.mean(indata, axis=1)
            else:
                audio_data = indata[:, 0] if indata.ndim > 1 else indata
            
            self._append_audio_data(audio_data)
        except Exception as e:
            print(f"Audio callback error: {e}")
    
    def run(self):
        if self._run_soundcard_loopback():
            return

        stream_opened = False
        last_error = None

        for cfg in self._build_stream_configs():
            if not self.running:
                return
            try:
                print(
                    f"[AudioAnalyzerThread] Trying InputStream: "
                    f"mode={cfg.get('label', 'unknown')}, "
                    f"device={cfg.get('device')}, "
                    f"channels={cfg['channels']}, samplerate={cfg['samplerate']}, blocksize={cfg['blocksize']}"
                )
                with sd.InputStream(
                    device=cfg.get("device"),
                    callback=self.audio_callback,
                    channels=cfg["channels"],
                    samplerate=cfg["samplerate"],
                    blocksize=cfg["blocksize"],
                    extra_settings=cfg.get("extra_settings"),
                ):
                    self.current_samplerate = int(cfg["samplerate"])
                    stream_opened = True
                    print("[AudioAnalyzerThread] ✓ InputStream opened")
                    while self.running:
                        if self.is_playing:
                            self._emit_level_from_buffer()
                            self._emit_pitch_from_buffer()

                        self.msleep(100) # Throttled to 10Hz for smoother UI updates
                break
            except Exception as e:
                last_error = e
                print(f"[AudioAnalyzerThread] ❌ Stream config failed: {e}")

        if not stream_opened and self.running:
            print(f"[AudioAnalyzerThread] ❌ Could not open any InputStream: {last_error}")
    
    def stop(self):
        """Stop the audio analyzer"""
        self.running = False
        self.is_playing = False
        # Wait longer for the stream to close
        self.wait(2000)
        # Force terminate if still running
        if self.isRunning():
            self.terminate()
            self.wait(500)