"""Unit tests for source_code/workers/audio_analyzer.py"""

import numpy as np
import pytest

from source_code.workers import audio_analyzer as aa
from source_code.workers.audio_analyzer import (
    AudioAnalyzerThread,
    detect_pitch_from_audio,
    frequency_to_midi_note,
    midi_note_to_name,
)

SAMPLE_RATE = 44100


def _tone(frequency_hz, sample_count=4096, sample_rate=SAMPLE_RATE, amplitude=0.5):
    t = np.arange(sample_count, dtype=np.float32) / float(sample_rate)
    return (amplitude * np.sin(2 * np.pi * frequency_hz * t)).astype(np.float32)


class TestFrequencyToMidiNote:
    @pytest.mark.parametrize(
        "frequency_hz, expected_midi",
        [
            (440.0, 69),
            (880.0, 81),
            (220.0, 57),
            (261.6256, 60),
        ],
    )
    def test_known_frequencies(self, frequency_hz, expected_midi):
        assert frequency_to_midi_note(frequency_hz) == expected_midi

    def test_rounds_to_nearest_semitone(self):
        assert frequency_to_midi_note(444.0) == 69

    @pytest.mark.parametrize("frequency_hz", [None, 0, -100.0])
    def test_invalid_frequencies_return_none(self, frequency_hz):
        assert frequency_to_midi_note(frequency_hz) is None


class TestMidiNoteToName:
    @pytest.mark.parametrize(
        "midi_note, expected_name",
        [
            (69, "A4"),
            (60, "C4"),
            (61, "C#4"),
            (0, "C-1"),
            (127, "G9"),
        ],
    )
    def test_known_notes(self, midi_note, expected_name):
        assert midi_note_to_name(midi_note) == expected_name

    def test_none_returns_empty_string(self):
        assert midi_note_to_name(None) == ""

    def test_accepts_float_midi_values(self):
        assert midi_note_to_name(69.0) == "A4"


class TestDetectPitchFromAudio:
    def test_detects_a4_sine_wave(self):
        result = detect_pitch_from_audio(_tone(440.0), SAMPLE_RATE)

        assert result is not None
        assert result["note_name"] == "A4"
        assert result["midi_note"] == 69
        assert result["frequency_hz"] == pytest.approx(440.0, rel=0.02)
        assert 0.35 <= result["confidence"] <= 1.5

    def test_detects_pitch_from_multichannel_buffer(self):
        # Multichannel input is flattened (interleaved), which halves the
        # effective sample period, so a 220 Hz stereo tone reads as 110 Hz.
        mono = _tone(220.0)
        stereo = np.stack([mono, mono], axis=1)

        result = detect_pitch_from_audio(stereo, SAMPLE_RATE)

        assert result is not None
        assert result["frequency_hz"] == pytest.approx(110.0, rel=0.03)

    def test_none_audio_returns_none(self):
        assert detect_pitch_from_audio(None, SAMPLE_RATE) is None

    def test_short_buffer_returns_none(self):
        assert detect_pitch_from_audio(_tone(440.0, sample_count=1024), SAMPLE_RATE) is None

    @pytest.mark.parametrize("sample_rate", [None, 0, -1])
    def test_invalid_sample_rate_returns_none(self, sample_rate):
        assert detect_pitch_from_audio(_tone(440.0), sample_rate) is None

    def test_silence_returns_none(self):
        assert detect_pitch_from_audio(np.zeros(4096, dtype=np.float32), SAMPLE_RATE) is None

    def test_low_amplitude_below_rms_gate_returns_none(self):
        assert detect_pitch_from_audio(_tone(440.0, amplitude=0.001), SAMPLE_RATE) is None

    def test_noise_without_periodicity_returns_none(self):
        rng = np.random.default_rng(1234)
        noise = rng.standard_normal(4096).astype(np.float32) * 0.3

        assert detect_pitch_from_audio(noise, SAMPLE_RATE) is None

    def test_frequency_outside_requested_band_is_rejected(self):
        assert detect_pitch_from_audio(_tone(440.0), SAMPLE_RATE, min_frequency=600.0, max_frequency=1100.0) is None

    def test_inverted_frequency_band_returns_none(self):
        assert detect_pitch_from_audio(_tone(440.0), SAMPLE_RATE, min_frequency=100.0, max_frequency=50.0) is None


class TestAudioAnalyzerThreadBuffer:
    def test_initial_state(self):
        thread = AudioAnalyzerThread()

        assert thread.running is True
        assert thread.is_playing is False
        assert thread.audio_buffer.size == 0
        assert thread.current_samplerate == 44100

    def test_set_playing_resets_silence_counter(self):
        thread = AudioAnalyzerThread()

        thread.set_playing(True)

        assert thread.is_playing is True
        assert thread.silence_count == 0

    def test_append_audio_data_keeps_buffer_below_two_windows(self):
        thread = AudioAnalyzerThread()

        thread._append_audio_data(np.ones(thread.buffer_size * 2, dtype=np.float32))

        assert len(thread.audio_buffer) == thread.buffer_size * 2

        thread._append_audio_data(np.ones(1, dtype=np.float32))

        assert len(thread.audio_buffer) == thread.buffer_size

    def test_append_audio_data_preserves_short_appends(self):
        thread = AudioAnalyzerThread()

        thread._append_audio_data(np.full(100, 0.25, dtype=np.float32))
        thread._append_audio_data(np.full(50, 0.5, dtype=np.float32))

        assert len(thread.audio_buffer) == 150
        assert thread.audio_buffer[-1] == pytest.approx(0.5)

    def test_emit_level_skips_when_buffer_too_small(self, qapp):
        thread = AudioAnalyzerThread()
        emitted = []
        thread.level_updated.connect(emitted.append)

        thread._append_audio_data(np.ones(10, dtype=np.float32))
        thread._emit_level_from_buffer()

        assert emitted == []

    def test_emit_level_reports_full_scale_as_zero_db(self, qapp):
        thread = AudioAnalyzerThread()
        emitted = []
        thread.level_updated.connect(emitted.append)

        thread._append_audio_data(np.ones(thread.buffer_size, dtype=np.float32))
        thread._emit_level_from_buffer()

        assert emitted == [pytest.approx(0.0, abs=1e-6)]

    def test_emit_level_clamps_silence_to_floor(self, qapp):
        thread = AudioAnalyzerThread()
        emitted = []
        thread.level_updated.connect(emitted.append)

        thread._append_audio_data(np.zeros(thread.buffer_size, dtype=np.float32))
        thread._emit_level_from_buffer()

        assert emitted == [-80.0]

    def test_emit_pitch_skips_when_buffer_too_small(self, qapp):
        thread = AudioAnalyzerThread()
        emitted = []
        thread.pitch_updated.connect(lambda *args: emitted.append(args))

        thread._append_audio_data(np.ones(100, dtype=np.float32))
        thread._emit_pitch_from_buffer()

        assert emitted == []

    def test_emit_pitch_reports_detected_note_once(self, qapp):
        thread = AudioAnalyzerThread()
        emitted = []
        thread.pitch_updated.connect(lambda *args: emitted.append(args))

        thread._append_audio_data(_tone(440.0, sample_count=thread.buffer_size))
        thread._emit_pitch_from_buffer()
        thread._emit_pitch_from_buffer()

        assert len(emitted) == 1
        frequency_hz, note_name, confidence = emitted[0]
        assert note_name == "A4"
        assert frequency_hz == pytest.approx(440.0, rel=0.03)
        assert confidence > 0.35

    def test_emit_pitch_resets_note_when_signal_disappears(self, qapp):
        thread = AudioAnalyzerThread()
        emitted = []
        thread.pitch_updated.connect(lambda *args: emitted.append(args))

        thread._append_audio_data(_tone(440.0, sample_count=thread.buffer_size))
        thread._emit_pitch_from_buffer()
        thread._append_audio_data(np.zeros(thread.buffer_size, dtype=np.float32))
        thread._emit_pitch_from_buffer()

        assert emitted[-1] == (0.0, "", 0.0)
        assert thread._last_pitch_note == ""
        assert thread._last_pitch_frequency == 0.0

    def test_emit_pitch_does_not_emit_reset_twice(self, qapp):
        thread = AudioAnalyzerThread()
        emitted = []
        thread.pitch_updated.connect(lambda *args: emitted.append(args))

        thread._append_audio_data(np.zeros(thread.buffer_size, dtype=np.float32))
        thread._emit_pitch_from_buffer()
        thread._emit_pitch_from_buffer()

        assert emitted == []


class TestAudioAnalyzerThreadCallback:
    def test_callback_ignored_while_not_playing(self):
        thread = AudioAnalyzerThread()

        thread.audio_callback(np.ones((256, 2), dtype=np.float32), 256, None, None)

        assert thread.audio_buffer.size == 0

    def test_callback_downmixes_multichannel_to_mono(self):
        thread = AudioAnalyzerThread()
        thread.set_playing(True)
        indata = np.stack([np.full(256, 0.2, dtype=np.float32), np.full(256, 0.4, dtype=np.float32)], axis=1)

        thread.audio_callback(indata, 256, None, None)

        assert len(thread.audio_buffer) == 256
        assert thread.audio_buffer == pytest.approx(np.full(256, 0.3, dtype=np.float32), abs=1e-6)

    def test_callback_uses_first_channel_for_single_channel_2d_input(self):
        thread = AudioAnalyzerThread()
        thread.set_playing(True)
        indata = np.full((128, 1), 0.5, dtype=np.float32)

        thread.audio_callback(indata, 128, None, None)

        assert len(thread.audio_buffer) == 128
        assert thread.audio_buffer == pytest.approx(np.full(128, 0.5, dtype=np.float32))

    def test_callback_accepts_mono_1d_input(self):
        thread = AudioAnalyzerThread()
        thread.set_playing(True)

        thread.audio_callback(np.full(64, 0.1, dtype=np.float32), 64, None, None)

        assert len(thread.audio_buffer) == 64

    def test_callback_swallows_errors_from_bad_payload(self):
        thread = AudioAnalyzerThread()
        thread.set_playing(True)

        thread.audio_callback("not-an-array", 64, None, None)

        assert thread.audio_buffer.size == 0


class TestStreamConfigBuilding:
    def test_append_unique_config_deduplicates_identical_entries(self):
        thread = AudioAnalyzerThread()
        configs, seen = [], set()
        cfg = {"label": "x", "device": None, "channels": 2, "samplerate": 48000, "blocksize": 2048, "extra_settings": None}

        thread._append_unique_config(configs, seen, dict(cfg))
        thread._append_unique_config(configs, seen, dict(cfg))

        assert len(configs) == 1

    def test_append_unique_config_keeps_distinct_entries(self):
        thread = AudioAnalyzerThread()
        configs, seen = [], set()

        thread._append_unique_config(configs, seen, {"label": "x", "channels": 1, "samplerate": 44100})
        thread._append_unique_config(configs, seen, {"label": "x", "channels": 2, "samplerate": 44100})

        assert len(configs) == 2

    def test_wasapi_candidates_empty_off_windows(self, monkeypatch):
        monkeypatch.setattr(aa.sys, "platform", "linux")

        assert AudioAnalyzerThread()._get_wasapi_output_candidates() == []

    def test_build_stream_configs_uses_default_input_channel_count(self, monkeypatch, sd_stub):
        monkeypatch.setattr(aa.sys, "platform", "linux")
        sd_stub.default = type("D", (), {"device": [3, 4]})()
        sd_stub.query_devices = lambda *args, **kwargs: {"max_input_channels": 2}

        configs = AudioAnalyzerThread()._build_stream_configs()

        assert len(configs) == 4
        assert {cfg["channels"] for cfg in configs} == {1, 2}
        assert {cfg["samplerate"] for cfg in configs} == {44100, 48000}
        assert all(cfg["label"] == "Default input" for cfg in configs)

    def test_build_stream_configs_limits_to_mono_for_single_channel_device(self, monkeypatch, sd_stub):
        monkeypatch.setattr(aa.sys, "platform", "linux")
        sd_stub.default = type("D", (), {"device": [0, 1]})()
        sd_stub.query_devices = lambda *args, **kwargs: {"max_input_channels": 1}

        configs = AudioAnalyzerThread()._build_stream_configs()

        assert {cfg["channels"] for cfg in configs} == {1}

    def test_build_stream_configs_falls_back_when_device_query_fails(self, monkeypatch, sd_stub):
        monkeypatch.setattr(aa.sys, "platform", "linux")

        def _boom(*args, **kwargs):
            raise RuntimeError("no device")

        sd_stub.default = type("D", (), {"device": [0, 1]})()
        sd_stub.query_devices = _boom

        configs = AudioAnalyzerThread()._build_stream_configs()

        assert {cfg["channels"] for cfg in configs} == {1}
        assert all(cfg["device"] is None for cfg in configs)


class TestSoundcardLoopback:
    def test_returns_false_off_windows(self, monkeypatch):
        monkeypatch.setattr(aa.sys, "platform", "linux")

        assert AudioAnalyzerThread()._run_soundcard_loopback() is False

    def test_returns_false_when_soundcard_missing(self, monkeypatch):
        monkeypatch.setattr(aa.sys, "platform", "win32")
        monkeypatch.setattr(aa, "sc", None)

        assert AudioAnalyzerThread()._run_soundcard_loopback() is False

    def test_returns_false_when_no_default_speaker(self, monkeypatch):
        monkeypatch.setattr(aa.sys, "platform", "win32")
        monkeypatch.setattr(aa, "sc", type("SC", (), {"default_speaker": staticmethod(lambda: None)}))

        assert AudioAnalyzerThread()._run_soundcard_loopback() is False

    def test_returns_false_when_speaker_lookup_raises(self, monkeypatch):
        def _boom():
            raise RuntimeError("no speaker")

        monkeypatch.setattr(aa.sys, "platform", "win32")
        monkeypatch.setattr(aa, "sc", type("SC", (), {"default_speaker": staticmethod(_boom)}))

        assert AudioAnalyzerThread()._run_soundcard_loopback() is False
