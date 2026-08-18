"""Helpers for launching console tools (ffmpeg/ffprobe/yt-dlp/demucs) without popup windows."""

import subprocess
import sys

CREATE_NO_WINDOW = 0x08000000


def hidden_startupinfo():
    """Return a STARTUPINFO that hides the child console window (None on non-Windows)."""
    if sys.platform != "win32" or not hasattr(subprocess, "STARTUPINFO"):
        return None

    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = 0
    return startupinfo


def hidden_creationflags():
    """Return creation flags that suppress the child console window (0 on non-Windows)."""
    return CREATE_NO_WINDOW if sys.platform == "win32" else 0


def run_hidden(cmd, timeout=None, text=True):
    """Run a command to completion with captured output and no visible console window."""
    return subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        startupinfo=hidden_startupinfo(),
        text=text,
        timeout=timeout,
    )


def popen_hidden(cmd, merge_stderr=False, universal_newlines=False, bufsize=-1):
    """Start a streaming command with stdout piped and no visible console window.

    With `merge_stderr`, stderr is folded into the stdout stream so progress output written to
    either channel can be parsed from one place.
    """
    return subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT if merge_stderr else subprocess.PIPE,
        universal_newlines=universal_newlines,
        startupinfo=hidden_startupinfo(),
        creationflags=hidden_creationflags(),
        bufsize=bufsize,
    )
