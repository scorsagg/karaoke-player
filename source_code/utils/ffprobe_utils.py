"""Thin ffprobe query helpers shared by the app, services and controllers."""

import os

from source_code.utils.subprocess_utils import run_hidden

DEFAULT_OUTPUT_FORMAT = "default=noprint_wrappers=1:nokey=1"


def probe(ffprobe_path, target_path, show_entries, select_streams=None,
          output_format=DEFAULT_OUTPUT_FORMAT, timeout=3):
    """Return stripped ffprobe stdout for a query, or an empty string when probing fails."""
    if not ffprobe_path or not target_path or not os.path.exists(target_path):
        return ""

    cmd = [ffprobe_path, "-v", "error"]
    if select_streams:
        cmd += ["-select_streams", select_streams]
    cmd += ["-show_entries", show_entries, "-of", output_format, target_path]

    try:
        result = run_hidden(cmd, timeout=timeout)
        return (result.stdout or "").strip()
    except Exception:
        return ""


def probe_duration_seconds(ffprobe_path, target_path, default=0.0):
    """Return media duration in seconds, or `default` when it cannot be determined."""
    try:
        return float(probe(ffprobe_path, target_path, "format=duration"))
    except (TypeError, ValueError):
        return default


def probe_audio_sample_rate(ffprobe_path, target_path, default=44100):
    """Return the first audio stream sample rate, or `default` when unavailable."""
    try:
        sample_rate = int(float(probe(ffprobe_path, target_path, "stream=sample_rate",
                                      select_streams="a:0")))
    except (TypeError, ValueError):
        return default
    return sample_rate if sample_rate > 0 else default


def probe_stream_codec_types(ffprobe_path, target_path):
    """Return the lowercased codec_type of every stream in the file."""
    output = probe(ffprobe_path, target_path, "stream=codec_type")
    return [line.strip().lower() for line in output.splitlines() if line.strip()]


def probe_video_resolution(ffprobe_path, target_path, timeout=2):
    """Return (width, height) floats of the first video stream, or None when unavailable."""
    output = probe(ffprobe_path, target_path, "stream=width,height", select_streams="v:0",
                   output_format="csv=p=0:s=x", timeout=timeout)
    parts = output.split("x")
    if len(parts) != 2:
        return None
    try:
        return float(parts[0]), float(parts[1])
    except ValueError:
        return None
