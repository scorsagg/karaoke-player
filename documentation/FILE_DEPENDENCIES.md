# Karaoke Studio Pro - File Dependencies & Update Checklist

**IMPORTANT:** Before making ANY changes to the codebase, consult this file to identify all related files that need updating together.

## When Making Changes to These Areas, Update These Files:

### 1. VERSION UPDATES (Currently: v3)
**Files to update:**
- `build_system/build.py` → `VERSION = "3"`
- `build_system/KaraokeStudioPro.spec` → Comment at top mentions v3
- `README.md` → Title and version references
- `build_system/BUILD_GUIDE.md` → Title includes v3
- `documentation/INSTALLATION.txt` → Title and file name references
- `documentation/FOLDER_ORGANIZATION_SUMMARY.txt` → Title includes v3
- `documentation/ARCHITECTURE.md` → Title includes v3

### 2. EXE NAME CHANGES
**Current:** `KaraokeStudioProV3.exe`
**Files to update:**
- `build_system/KaraokeStudioPro.spec` → `name='KaraokeStudioProV3'` in EXE section
- `documentation/INSTALLATION.txt` → All executable references

### 3. BUILD SPEC HIDDEN IMPORTS (Add new modules here when creating new Python files)
**File:** `build_system/KaraokeStudioPro.spec` → `hiddenimports=[]` list
**Update when:**
- Creating new service: `source_code.services.new_service`
- Creating new UI component: `source_code.ui.new_component`
- Creating new widget: `source_code.widgets.new_widget`
- Creating new dialog: `source_code.dialogs.new_dialog`
- Creating new worker: `source_code.workers.new_worker`

### 4. UI REFACTORING (Modularized Components)
**Current structure:** `source_code/ui/` folder with:
- main_layout.py, sidebar.py, playback_bar.py, download_page.py, pitch_page.py, extra_page.py

**Files to update when modifying UI:**
- `build_system/KaraokeStudioPro.spec` → hiddenimports for new UI modules
- `source_code/main.py` → imports from ui package, setup_ui() method
- `documentation/FOLDER_ORGANIZATION_SUMMARY.txt` → UI folder structure
- `documentation/ARCHITECTURE.md` → UI architecture section

### 5. AUDIO FEATURES (SPL, dBFS, Auto-Reduce, AudioService)
**Related files:**
- `source_code/services/audio_service.py` → AudioService implementation
- `source_code/widgets/audio_meter.py` → Measurement mode logic, SPL calculation
- `source_code/main.py` → Audio level handler, settings integration
- `source_code/dialogs/settings_dialog.py` → Audio settings fields
- `config/settings.json` → measurement_mode, auto_reduce_threshold fields
- `build_system/KaraokeStudioPro.spec` → audio_service hidden import
- `documentation/INSTALLATION.txt` → Audio calibration section, features
- `documentation/ARCHITECTURE.md` → Audio system section
- `documentation/FOLDER_ORGANIZATION_SUMMARY.txt` → AudioService in services/

### 6. SETTINGS/CONFIG CHANGES
**File:** `config/settings.json`
**When adding new settings:**
- Add field to settings.json default structure
- Add field to `source_code/dialogs/settings_dialog.py` schema
- Add field handling in settings_dialog.py `build_pages()` method
- Add field handling in settings_dialog.py `accept_changes()` method
- Update documentation if user-facing

### 7. NEW SERVICE/WORKER CREATION
**When creating:** `source_code/services/new_service.py` or `source_code/workers/new_worker.py`
**Update:**
- `build_system/KaraokeStudioPro.spec` → Add to hiddenimports
- `source_code/main.py` → Import and instantiate
- `source_code/[services|workers]/__init__.py` → Export if needed
- `documentation/ARCHITECTURE.md` → Document new component
- `documentation/FOLDER_ORGANIZATION_SUMMARY.txt` → Add to folder listing

### 8. THREAD-SAFE FILE LOADING (File Loading Operations - FINAL FIX ✅)
**Current Service:** `source_code/services/file_loading_service.py`
**Related files:**
- `source_code/services/file_loading_service.py` → FileLoadingService implementation
- `source_code/services/audio_service.py` → Coordinates with audio analyzer state
- `source_code/services/player_service.py` → Player state checks and pause
- `source_code/main.py` → Initializes FileLoadingService, uses prepare_for_loading()/finish_loading()
- `build_system/KaraokeStudioPro.spec` → file_loading_service in hiddenimports

**Final Solution (After Debugging):**
The key fix: **Never call player.stop() when decoder is active** instead:
1. Call `player.pause()` to stop decoder threads
2. Wait 1.0s for pause to take effect
3. Call `audio_analyzer.stop()` to close sounddevice InputStream
4. Release media reference: `player._media = None` (DON'T call stop()!)
5. Wait 0.5s for cleanup
6. Load new file - VLC auto-cleans old media

**Why This Works:**
- VLC decoder threads stay active even after pause
- Calling `player.stop()` hangs waiting for threads to exit
- Solution: pause + release media reference + let VLC auto-cleanup when new media loads

**Entry Points (all use load_video() internally):**
1. Download page "Open File..." button
2. Widen page "Open Widen File..." button
3. History list double-click
4. Download & Queue button completion
5. Convert to 16:9 button completion

### 9. DEPRECATED/DELETED FILES
**Current deprecated files:**
- karaoke_app.py
- v2-karaoke_app - Copy.py
- v2-VLC_version.py

**When removing files:**
- Delete actual file
- Remove from version control (git)
- Update documentation (mark as deprecated or remove mention)
- Check build_system/KaraokeStudioPro.spec doesn't reference it
- Check .gitignore if needed

### 10. GITIGNORE & LOCAL FILES
**Current:**
- config/history.json (local user data, not tracked)
- __pycache__/, *.pyc
- build_system/build/, build_system/dist/

**When adding local-only files:**
- Add to .gitignore
- Document in FOLDER_ORGANIZATION_SUMMARY.txt

### 11. DOCUMENTATION SYNC CHECKLIST
**When updating docs, ensure consistency across:**
- README.md (project overview, features)
- ARCHITECTURE.md (technical design, components)
- INSTALLATION.txt (user guide, features, settings)
- FOLDER_ORGANIZATION_SUMMARY.txt (structure, recent improvements)
- BUILD_GUIDE.md (build version, prerequisites)

---

## Quick Reference: Common Tasks

### Adding a new Python module to source_code/
1. Create file: `source_code/[package]/new_file.py`
2. Add import to `build_system/KaraokeStudioPro.spec` hiddenimports
3. Import in parent file (main.py or relevant module)
4. Update documentation if structural change

### Version bump (e.g., v3 → v4)
1. Update VERSION in build.py
2. Update spec file comment
3. Update all doc titles and references
4. Update exe name in spec and docs

### Adding new audio feature
1. Implement in audio_service.py or audio_meter.py
2. Add settings fields to settings.json and settings_dialog.py
3. Integrate in main.py
4. Document in INSTALLATION.txt (Audio Calibration section)
5. Document in ARCHITECTURE.md (Audio System section)
6. Update FOLDER_ORGANIZATION_SUMMARY.txt (recent improvements)

### UI refactoring
1. Create/modify files in source_code/ui/
2. Update hiddenimports in spec file
3. Update imports in main.py
4. Update FOLDER_ORGANIZATION_SUMMARY.txt with folder structure
5. Update ARCHITECTURE.md with UI section
