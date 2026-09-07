# Testing

Unit tests live in `tests/` and run headlessly: no VLC runtime, audio hardware, FFmpeg
binary, or display is required. Native dependencies (`vlc`, `sounddevice`, `soundcard`)
are stubbed in `tests/conftest.py`, Qt runs with `QT_QPA_PLATFORM=offscreen`, and every
subprocess (FFmpeg, ffprobe, yt-dlp, audio-separator, Demucs) is faked.

## Setup

```bash
python -m venv .venv-test
.venv-test/bin/pip install -r documentation/requirements-dev.txt
```

## Run

```bash
.venv-test/bin/pytest
.venv-test/bin/pytest --cov=source_code --cov-report=term-missing
```

Configuration lives in `pytest.ini` (test discovery) and `.coveragerc` (coverage scope).

## Conventions

- One test module per source module (`tests/test_<module>.py`), grouped into `Test*`
  classes by behavior.
- Collaborators are hand-written fakes recording the calls under test; the goal is to
  assert real production behavior (FFmpeg argument lists, emitted Qt signals, state
  transitions), not to re-describe the implementation.
- Widget tests use the shared session-scoped `qapp` fixture.
- `source_code/main.py` is the GUI application shell and is exercised through the
  controllers, services, and UI builders it delegates to rather than directly.
