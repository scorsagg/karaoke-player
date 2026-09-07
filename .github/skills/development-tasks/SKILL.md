---
name: development-tasks
description: 'Run, test, and build Karaoke Studio Pro. Use when: executing the app, running tests, building the executable, debugging launch issues, checking syntax, validating changes.'
---

# Development Tasks for Karaoke Studio Pro v3

## When to Use

- Running the development application
- Running unit tests
- Building the standalone executable
- Checking Python syntax before committing
- Debugging common setup or runtime issues

---

## Quick Commands

### Run Development App
```powershell
python source_code\main.py
```
**Expected:** Window opens with media loader, playback, and audio studio pages visible. Exit code 0 on clean close.

### Run All Tests
```powershell
pytest
```
**Expected:** Output shows test count, passes/failures. All tests pass or shows specific skip markers (skip_windows, skip_non_windows).

### Run Specific Test File
```powershell
pytest tests\test_filename.py -v
```
**Expected:** Verbose output of test names and results.

### Build Standalone Executable
```powershell
python build_system\build.py
```
**Expected:** Output at `build_system/dist/KaraokeStudioPro/KaraokeStudioPro.exe`. Build takes 2-3 minutes.

### Check Python Syntax (All Files)
```powershell
python -m py_compile source_code\*.py source_code\**\*.py
```
**Expected:** No output means success. Errors show syntax problems.

---

## Common Workflows

### After Making Code Changes

**1. Syntax Check**
```powershell
python -m py_compile source_code\main.py
```
Verify your file compiles. Exit code 0 = success.

**2. Run Tests**
```powershell
pytest -q
```
Ensures existing functionality still works. Review any failed tests.

**3. Run App**
```powershell
python source_code\main.py
```
Smoke test: Can the app launch? Expected: window opens, no crash.

**4. Update Documentation** (if applicable)
See [copilot-instructions.md](../../copilot-instructions.md) → "Update Documentation" section. Run tests again after changes.

### Building for Distribution

**1. Verify All Tests Pass**
```powershell
pytest
```

**2. Verify Python 3.13 Runtime Available**
```powershell
py -3.13 --version
```
Should output `Python 3.13.x`. If not installed, build will fail.

**3. Run Build Script**
```powershell
python build_system\build.py
```
Build script handles FFmpeg/yt-dlp/libvlc bundling. **Do NOT skip this step — it bundles required tools.**

**4. Test Executable**
```powershell
build_system\dist\KaraokeStudioPro\KaraokeStudioPro.exe
```
Verify .exe launches and loads media without errors.

### Debugging Common Issues

#### App won't start from source

```powershell
python source_code\main.py
```
- **ImportError**: Dependencies missing → `pip install -r documentation/requirements.txt`
- **VLC library not found**: Expected behavior on clean install. Bundled libvlc requires build. Use source run or build .exe.
- **Audio meter not working**: sounddevice needs proper audio device. Check Windows sound settings.

#### Test failures

```powershell
pytest --tb=short
```
Shows stack trace. Check:
- Platform-specific skips: `pytest -m skip_windows` or `pytest -m skip_non_windows`
- Missing test data in `tests/` folder
- Syntax errors in modified files

#### Build fails

```powershell
python build_system/build.py
```
- **PyInstaller not found**: `pip install -r build_system/requirements-build.txt`
- **Python 3.13 not found**: Set `KARAOKE_BUILD_PYTHON` env var or install Python 3.13
- **Missing bundled tools**: Check `resources/ffmpeg.exe`, `resources/yt-dlp.exe`, `resources/libvlc.dll` exist

#### After build, .exe won't launch

- **Missing VLC plugins**: Verify `resources/plugins/` copied to build output
- **FFmpeg lookup failed**: Bundled ffmpeg.exe not copied → re-run build with correct resources/
- **Runtime library missing**: Rebuild with `python build_system/build.py`

---

## File Locations

| Task | File | Path |
|------|------|------|
| Main app | main.py | `source_code/` |
| Tests | test_*.py | `tests/` |
| Build config | KaraokeStudioPro.spec | `build_system/` |
| Build script | build.py | `build_system/` |
| Bundled tools | ffmpeg.exe, yt-dlp.exe, libvlc.dll | `resources/` |
| Dev dependencies | requirements.txt | `documentation/` |
| Build dependencies | requirements-build.txt | `build_system/` |

---

## Success Criteria

| Task | Success | Verify |
|------|---------|--------|
| Syntax check | Exit code 0 | No compile errors |
| Tests pass | All pass or expected skips | `pytest -v` output |
| App runs | Window opens, no crash | Can load media, play |
| Build succeeds | .exe created at dist/ | File exists, launches |
| .exe works | App launches from .exe | No DLL/library errors |

---

## When to Ask for Help

If you encounter:
- **Module not found after adding new files**: Check `build_system/KaraokeStudioPro.spec` hiddenimports list
- **VLC playback hangs**: See [IMPLEMENTATION_LOG.md](documentation/IMPLEMENTATION_LOG.md) for known issues
- **FFmpeg command fails**: Check `documentation/FILE_DEPENDENCIES.md` section 3b (bundled tool binaries)

Consult these files for deeper context:
- [DEVELOPMENT.md](DEVELOPMENT.md) — Architecture and setup details
- [FILE_DEPENDENCIES.md](documentation/FILE_DEPENDENCIES.md) — What files affect what
- [IMPLEMENTATION_LOG.md](documentation/IMPLEMENTATION_LOG.md) — Recent fixes and workarounds
