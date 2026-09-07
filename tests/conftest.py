"""Shared pytest configuration for the Karaoke Studio Pro unit tests.

The application depends on native media libraries (VLC via ``python-vlc``,
PortAudio via ``sounddevice``/``soundcard``) that are not available on headless
machines. Lightweight stand-ins are installed in ``sys.modules`` before any
application module is imported so the pure-Python logic can be unit tested.
"""

import os
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def _install_vlc_stub():
    vlc = types.ModuleType("vlc")

    class State:
        NothingSpecial = 0
        Opening = 1
        Buffering = 2
        Playing = 3
        Paused = 4
        Stopped = 5
        Ended = 6
        Error = 7

    class EventType:
        MediaPlayerTimeChanged = "MediaPlayerTimeChanged"
        MediaPlayerPositionChanged = "MediaPlayerPositionChanged"
        MediaPlayerPlaying = "MediaPlayerPlaying"
        MediaPlayerPaused = "MediaPlayerPaused"
        MediaPlayerStopped = "MediaPlayerStopped"
        MediaPlayerEndReached = "MediaPlayerEndReached"

    def Instance(*args, **kwargs):
        return MagicMock(name="vlc.Instance")

    vlc.State = State
    vlc.EventType = EventType
    vlc.Instance = Instance
    sys.modules["vlc"] = vlc


def _install_sounddevice_stub():
    sounddevice = types.ModuleType("sounddevice")
    sounddevice.default = types.SimpleNamespace(device=[None, None])
    sounddevice.query_devices = lambda *args, **kwargs: {}
    sounddevice.query_hostapis = lambda *args, **kwargs: []
    sounddevice.InputStream = MagicMock(name="sounddevice.InputStream")
    sounddevice.OutputStream = MagicMock(name="sounddevice.OutputStream")
    sys.modules["sounddevice"] = sounddevice


def _install_soundcard_stub():
    soundcard = types.ModuleType("soundcard")
    soundcard.default_speaker = lambda: None
    soundcard.get_microphone = lambda *args, **kwargs: None
    sys.modules["soundcard"] = soundcard


for _installer in (_install_vlc_stub, _install_sounddevice_stub, _install_soundcard_stub):
    _installer()


@pytest.fixture(scope="session")
def qapp():
    """A single offscreen QApplication shared by widget tests."""
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def sd_stub():
    """The stubbed ``sounddevice`` module, reset to defaults for each test."""
    sounddevice = sys.modules["sounddevice"]
    sounddevice.default = types.SimpleNamespace(device=[None, None])
    sounddevice.query_devices = lambda *args, **kwargs: {}
    sounddevice.query_hostapis = lambda *args, **kwargs: []
    return sounddevice
