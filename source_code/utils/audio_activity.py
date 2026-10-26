"""FFmpeg-based loudness activity detection for playback timeline highlights."""

import math
import re

ACTIVITY_THRESHOLD_DBFS = -10
ACTIVITY_WINDOW_SECONDS = 0.1

_FRAME_TIME_RE = re.compile(r"pts_time:([+-]?(?:\d+(?:\.\d*)?|\.\d+))")
_RMS_LEVEL_RE = re.compile(
    r"lavfi\.astats\.Overall\.RMS_level=([+-]?(?:\d+(?:\.\d*)?|\.\d+)|-inf|inf|nan)",
    re.IGNORECASE,
)


def build_activity_scan_command(ffmpeg_path, media_path):
    """Build a quiet FFmpeg scan that reports RMS level for each short audio window."""
    return [
        ffmpeg_path,
        "-hide_banner",
        "-nostats",
        "-i",
        media_path,
        "-map",
        "0:a:0",
        "-af",
        (
            "aresample=44100,asetnsamples=n=4410:p=1,"
            "astats=metadata=1:reset=1,"
            "ametadata=print:key=lavfi.astats.Overall.RMS_level:file=-"
        ),
        "-f",
        "null",
        "-",
    ]


def active_ranges_from_rms_metadata(lines, duration_seconds, threshold_dbfs=None):
    """Return normalized ranges whose per-window RMS level meets the threshold."""
    if duration_seconds <= 0:
        return []
    if threshold_dbfs is None:
        threshold_dbfs = ACTIVITY_THRESHOLD_DBFS

    frames = []
    frame_time = None
    for line in lines:
        time_match = _FRAME_TIME_RE.search(line)
        if time_match:
            frame_time = float(time_match.group(1))
            continue

        rms_match = _RMS_LEVEL_RE.search(line)
        if rms_match and frame_time is not None:
            try:
                rms_dbfs = float(rms_match.group(1))
            except ValueError:
                rms_dbfs = float("-inf")
            frames.append((frame_time, rms_dbfs))
            frame_time = None

    active_ranges = []
    for frame_time, rms_dbfs in frames:
        if not math.isfinite(rms_dbfs) or rms_dbfs < threshold_dbfs:
            continue
        start = max(0.0, min(frame_time, duration_seconds))
        end = min(start + ACTIVITY_WINDOW_SECONDS, duration_seconds)
        if end <= start:
            continue
        if active_ranges and start <= active_ranges[-1][1] + 1e-6:
            active_ranges[-1] = (active_ranges[-1][0], max(active_ranges[-1][1], end))
        else:
            active_ranges.append((start, end))

    return [
        (start / duration_seconds, end / duration_seconds)
        for start, end in active_ranges
    ]
