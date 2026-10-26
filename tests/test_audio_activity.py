import math
import shutil
import struct
import wave
from pathlib import Path

import pytest

from source_code.utils.audio_activity import (
    ACTIVITY_THRESHOLD_DBFS,
    ACTIVITY_WINDOW_SECONDS,
    active_ranges_from_rms_metadata,
    build_activity_scan_command,
)
from source_code.utils.subprocess_utils import run_hidden


def test_default_activity_cutoff_is_source_dbfs():
    assert ACTIVITY_THRESHOLD_DBFS == -10
    assert active_ranges_from_rms_metadata([], 10) == []


def test_activity_scan_reports_rms_metadata_for_short_windows():
    command = build_activity_scan_command("ffmpeg", "karaoke track.wav")

    assert command[0] == "ffmpeg"
    assert command[command.index("-i") + 1] == "karaoke track.wav"
    filter_chain = command[command.index("-af") + 1]
    assert f"asetnsamples=n=4410" in filter_chain
    assert "astats=metadata=1:reset=1" in filter_chain
    assert "ametadata=print:key=lavfi.astats.Overall.RMS_level:file=-" in filter_chain


def test_active_ranges_select_source_rms_windows_above_dbfs_threshold():
    threshold = ACTIVITY_THRESHOLD_DBFS
    lines = [
        "frame:0 pts:0 pts_time:0",
        "lavfi.astats.Overall.RMS_level=-10",
        "frame:1 pts:4410 pts_time:0.1",
        "lavfi.astats.Overall.RMS_level=-59",
        "frame:2 pts:8820 pts_time:0.2",
        "lavfi.astats.Overall.RMS_level=-65",
        "frame:3 pts:13230 pts_time:0.3",
        "lavfi.astats.Overall.RMS_level=-5",
    ]

    ranges = active_ranges_from_rms_metadata(lines, 0.4, threshold)
    assert len(ranges) == 2
    assert ranges[0] == pytest.approx((0.0, 0.25))
    assert ranges[1] == pytest.approx((0.75, 1.0))


def test_activity_ranges_include_windows_exactly_at_threshold():
    threshold = ACTIVITY_THRESHOLD_DBFS
    lines = [
        "frame:0 pts:0 pts_time:0",
        f"lavfi.astats.Overall.RMS_level={threshold}",
    ]

    assert active_ranges_from_rms_metadata(lines, 0.1, threshold) == [(0.0, 1.0)]


def test_active_ranges_handle_nonfinite_levels_clipping_and_missing_frames():
    lines = [
        "frame:0 pts:0 pts_time:-1",
        "lavfi.astats.Overall.RMS_level=-54",
        "frame:1 pts:4410 pts_time:0.1",
        "lavfi.astats.Overall.RMS_level=nan",
        "frame:2 pts:8820 pts_time:1.9",
        "lavfi.astats.Overall.RMS_level=-54",
    ]

    assert active_ranges_from_rms_metadata(lines, 2, -60) == [(0.0, 0.05), (0.95, 1.0)]
    assert active_ranges_from_rms_metadata([], 0) == []


def _write_level_segments(path):
    sample_rate = 44100
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(sample_rate)
        for amplitude in (0.5, 0.0005, 0.8):
            frames = (
                struct.pack(
                    "<h",
                    int(amplitude * 32767 * math.sin(2 * math.pi * 440 * index / sample_rate)),
                )
                for index in range(sample_rate)
            )
            output.writeframes(b"".join(frames))


def test_ffmpeg_scan_highlights_only_audio_above_source_dbfs_threshold(tmp_path):
    bundled_ffmpeg = Path(__file__).resolve().parents[1] / "resources" / "ffmpeg.exe"
    ffmpeg_path = str(bundled_ffmpeg) if bundled_ffmpeg.is_file() else shutil.which("ffmpeg")
    if not ffmpeg_path:
        pytest.skip("FFmpeg is required for the audio activity integration test")

    media_path = tmp_path / "synthetic-level-segments.wav"
    _write_level_segments(media_path)
    command = build_activity_scan_command(ffmpeg_path, str(media_path))
    result = run_hidden(command, timeout=20)

    assert result.returncode == 0, result.stderr
    ranges = active_ranges_from_rms_metadata(result.stdout.splitlines(), 3.0)
    assert ranges == pytest.approx([(0.0, 1 / 3), (2 / 3, 1.0)], abs=ACTIVITY_WINDOW_SECONDS / 3)
