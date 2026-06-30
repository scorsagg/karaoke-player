from PySide6.QtCore import QThread, Signal
import sounddevice as sd
import numpy as np
import sys
import warnings

try:
    import soundcard as sc
except Exception:
    sc = None

warnings.filterwarnings("ignore", message="data discontinuity in recording")


class AudioAnalyzerThread(QThread):
    """Thread to capture and analyze real-time audio output levels"""
    level_updated = Signal(float)  # Emit dB value
    clip_warning = Signal()  # Emit when level exceeds 90%
    
    def __init__(self):
        super().__init__()
        self.running = True
        self.is_playing = False
        self.audio_buffer = np.array([], dtype=np.float32)
        self.buffer_size = 4410 
        self.high_level_counter = 0 # Track how long it's been loud

    def _emit_level_from_buffer(self):
        if len(self.audio_buffer) >= self.buffer_size // 2:
            recent_audio = self.audio_buffer[-self.buffer_size:]
            rms = np.sqrt(np.mean(recent_audio ** 2))
            db_level = 20 * np.log10(rms + 1e-10)
            db_level = max(-80.0, min(0.0, db_level))
            self.level_updated.emit(db_level)

    def _append_audio_data(self, audio_data):
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
                    stream_opened = True
                    print("[AudioAnalyzerThread] ✓ InputStream opened")
                    while self.running:
                        if self.is_playing:
                            self._emit_level_from_buffer()

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