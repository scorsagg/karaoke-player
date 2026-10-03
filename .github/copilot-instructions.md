# Copilot instructions

Karaoke Studio Pro v3 is a Python/PySide6 desktop app. Playback is provided by VLC; FFmpeg/FFprobe handle media processing and probing; yt-dlp handles downloads; `sounddevice` and NumPy support audio monitoring. Windows is the primary packaging target.

## Before changing code

- Read [`documentation/FILE_DEPENDENCIES.md`](../documentation/FILE_DEPENDENCIES.md) and [`DEVELOPMENT.md`](../DEVELOPMENT.md) first. The dependency checklist identifies coupled files and packaging requirements.
- Keep the five project docs in sync for code or structural changes: `documentation/FILE_DEPENDENCIES.md`, `documentation/ARCHITECTURE.md`, `documentation/FOLDER_ORGANIZATION_SUMMARY.txt`, `DEVELOPMENT.md`, and `documentation/IMPLEMENTATION_LOG.md`.
- Follow the more specific guidance when changing an applicable file:
  - [`main-py-editing.instructions.md`](instructions/main-py-editing.instructions.md) for `source_code/main.py`
  - [`build-spec-editing.instructions.md`](instructions/build-spec-editing.instructions.md) for `build_system/KaraokeStudioPro.spec`
  - [`file-dependencies-editing.instructions.md`](instructions/file-dependencies-editing.instructions.md) for the dependency checklist
  - [`docs-sync-editing.instructions.md`](instructions/docs-sync-editing.instructions.md) for the five-doc workflow

## Build, test, and run

Run commands from the repository root in PowerShell:

```powershell
# Run the app from source
python source_code\main.py

# Run all unit tests
python -m pytest

# Run one test module
python -m pytest tests\test_playback_controller.py

# Run one test
python -m pytest tests\test_app_state.py::TestDefaults::test_paths_default_to_empty_strings

# Run tests with coverage
python -m pytest --cov=source_code --cov-report=term-missing

# Build the Windows distribution (verified with Python 3.13)
python build_system\build.py
```

Pytest discovers `tests/test_*.py` and uses quiet output from `pytest.ini`. `tests/conftest.py` configures Qt for offscreen use and stubs VLC/audio-device dependencies, so the unit suite does not require media hardware or a GUI display. Widget tests use the shared `qapp` fixture. A repository-wide lint command is not defined; use `python -m py_compile source_code\path\to\changed_file.py` for a focused syntax check.

The build script resolves an interpreter with PyInstaller; set `KARAOKE_BUILD_PYTHON` if needed to select one explicitly. A distribution build requires the bundled media resources and offline Demucs model cache described in `build_system/build.py` and `build_system/BUILD_GUIDE.md`. The script clears generated build, distribution, and temporary build output directories before packaging.

## Architecture and data flow

- [`source_code/main.py`](../source_code/main.py) is the application shell: it creates `AppState`, services, and controllers, builds the UI, and wires Qt signals and callbacks. Its compatibility mapping exposes `AppState` fields through the window while state is being migrated.
- [`source_code/models/app_state.py`](../source_code/models/app_state.py) holds window-level runtime state. Controllers take the app as context and coordinate focused workflows: playback, media loading/history, processing, and navigation.
- Services own integrations and lifecycles such as VLC playback, downloads, audio monitoring, file loading, logging, and real-time pitch. UI modules under `source_code/ui/` build individual pages; [`main_layout.py`](../source_code/ui/main_layout.py) assembles them into a `QStackedWidget`.
- Long-running work runs in Qt workers (`QThread`) and reports completion/progress through signals rather than blocking the UI. Keep worker references alive until their `finished` signal and follow existing stop/wait cleanup patterns.
- Shared helpers under `source_code/utils/` centralize subprocess launch behavior, FFprobe probing, media paths, splash lifecycle, and range-row handling. Reuse them instead of duplicating these operations.
- The PyInstaller spec explicitly lists hidden imports and bundled binaries; source imports working is not sufficient to guarantee the packaged app works.

For detailed component responsibilities and pipelines, see [`documentation/ARCHITECTURE.md`](../documentation/ARCHITECTURE.md).

## Repository-specific conventions

- Use absolute package imports such as `from source_code.services.player_service import PlayerService`.
- Keep responsibilities in their existing layer: UI builders construct widgets, controllers orchestrate app workflows, services encapsulate integrations, and workers handle long-running operations.
- If adding a Python module, update `build_system/KaraokeStudioPro.spec` hidden imports as needed. If adding or changing bundled tools, also update the spec binaries and prerequisite validation in `build_system/build.py`.
- The page order is a contract: Media Loader `0`, Playback `1`, Audio Studio `2`, Video Studio `3`, Convert & Export `4`. Keep it aligned across `main.py`, the stacked layout, and the dependency checklist. Pages 2–4 are wrapped in `QScrollArea`; retrieve the page widget through the scroll area when a caller needs it.
- Route subprocesses through `source_code.utils.subprocess_utils`; use the shared FFprobe helpers and media-path helpers for their respective jobs. Subprocess output that may contain user paths should follow the existing UTF-8 decoding with replacement behavior.
- Settings span the JSON configuration, settings dialog, and app initialization. When opening settings, pause audio analysis as the existing workflow does; clean up the analyzer during shutdown.
- Tests favor hand-written fakes around services, workers, and Qt signals, asserting behavior such as command arguments and state changes. `main.py` is primarily exercised through the controllers, services, and UI builders it wires together.
