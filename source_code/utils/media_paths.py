"""Path helpers for building FFmpeg-friendly input/output locations."""

import os


def to_ffmpeg_path(path):
    """Return an absolute path with forward slashes, the form FFmpeg accepts everywhere."""
    if not path:
        return ""
    return os.path.abspath(path).replace("\\", "/")


def source_base_name(source_path):
    """Return the file name of a media path without directory or extension."""
    return os.path.splitext(os.path.basename(source_path or ""))[0]


def build_output_path(directory, source_path, suffix, extension):
    """Return `<directory>/<source name><suffix>.<extension>` for an export target."""
    return os.path.join(
        directory,
        f"{source_base_name(source_path)}{suffix}.{str(extension).lstrip('.')}",
    )
