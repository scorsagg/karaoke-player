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

Run the offscreen UI regression checks and generated-media fixture independently with:

```bash
.venv-test/bin/pytest tests/test_ui_regression.py
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

## UI regression tests

Karaoke Studio Pro is a native PySide6 desktop app, so Playwright is not the appropriate
driver: it automates browser pages, not Qt widgets. `tests/test_ui_regression.py` uses
the existing `qapp` fixture and `PySide6.QtTest.QTest` to exercise the real shell,
widgets, navigation, signals, and handler wiring in the offscreen test environment.
Operation handlers and external services are faked at the UI boundary so a click does
not start a download, open a native dialog, or require media hardware. The current
development requirements do not include pytest-qt; use it only if it is deliberately
added to `documentation/requirements-dev.txt`. Existing controller/service tests cover
the operation logic separately.

The `generated_media_files` fixture in `tests/conftest.py` creates a short synthetic WAV
and MP4 in pytest's temporary directory and verifies their streams with FFprobe. Media
workflow integration tests should use these fixtures with real FFmpeg/FFprobe where
available, and inspect output streams/duration instead of asserting only process success.
Keep the regular UI regression suite self-contained; user-provided samples may
supplement local diagnosis but must not be required for ordinary CI.
Optional Windows process-level automation can be evaluated separately if tests need to
drive the launched desktop process. See
[`FEATURE_SERVICE_MIGRATION_PLAN.md`](FEATURE_SERVICE_MIGRATION_PLAN.md) for required
all-feature coverage and phase gates.
