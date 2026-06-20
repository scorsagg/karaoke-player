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
- `source_code/widgets/audio_meter.py` → Measurement mode logic, SPL calculation, **HAS BOTH set_level() and update_level() methods (aliases)**
- `source_code/main.py` → Audio level handler, settings integration
- `source_code/dialogs/settings_dialog.py` → Audio settings fields
- `config/settings.json` → measurement_mode, auto_reduce_threshold fields
- `build_system/KaraokeStudioPro.spec` → audio_service hidden import
- `documentation/INSTALLATION.txt` → Audio calibration section, features
- `documentation/ARCHITECTURE.md` → Audio system section
- `documentation/FOLDER_ORGANIZATION_SUMMARY.txt` → AudioService in services/

**CRITICAL SIGNAL CONNECTIONS:**
- When audio analyzer thread is recreated (pause/resume), audio_service.py line 59 calls: `new_thread.level_updated.connect(self.audio_meter.update_level)`
- AudioLevelMeter widget MUST have BOTH methods:
  - `set_level(db_value)` - Called directly from main.py's on_audio_level_updated()
  - `update_level(db_value)` - Called from audio_service when thread is recreated (alias to set_level)

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

### 9. AUDIO PROCESSING FEATURES (Features 6 & 7) ✅ COMPLETE
**Status:** Fully Implemented & Enhanced in v3

**Related files:**
- `source_code/ui/extra_page.py` → UI with tabbed interface + TimePickerWidget class
- `source_code/main.py` → trim_audio(), convert_audio_format(), build_format_conversion_cmd() methods, audio overlay, history loading
- `documentation/ARCHITECTURE.md` → Audio Processing section
- `documentation/IMPLEMENTATION_LOG.md` → Features 6 & 7 + UX improvements entry

**Feature 6: Audio Trimming ✅ COMPLETE**
- Trim first X seconds, last X seconds, keep range, or combinations
- Supports all audio formats (MP3, WAV, AAC, M4A)
- FFmpeg command: `-ss {start} -to {end} -acodec copy`
- **UI Component:** `TimePickerWidget` class with three spinboxes
  - Separate Hour/Minute/Second controls (0-59 range each)
  - Total time calculated as: hours * 3600 + minutes * 60 + seconds
  - Display format: HH:MM:SS
  - Each unit increments independently
- **UI Location:** Extra Tools → Audio Tools tab → Trimming section
- **Checkbox Controls:**
  - ☑ Trim First X seconds (with H/M/S picker)
  - ☑ Trim Last X seconds (with H/M/S picker)
  - ☑ Keep Range (from A to B) with Start and End H/M/S pickers
  - Output format selector (MP3, WAV, AAC, M4A)

**Feature 7: Format Conversion ✅ COMPLETE**
- Convert between audio/video formats: MP3, WAV, M4A, AAC, DAT, MP4, MKV, AVI, WebM
- Quality selector for lossy formats (High 320kbps, Medium 192kbps, Low 128kbps)
- Intelligent FFmpeg command builder handles all format combinations
- **UI Location:** Extra Tools → Audio Tools tab → Converter section
- **Controls:**
  - Source format dropdown (Auto-detect + specific formats)
  - Target format dropdown
  - Quality selector (for lossy formats)
  - Convert & Export button

**Quality Mappings (for MP3 and other lossy formats):**
- High (320kbps) → bitrate=320k
- Medium (192kbps) → bitrate=192k
- Low (128kbps) → bitrate=128k

**Format Conversion Examples:**
- MP3 → WAV: `ffmpeg -i input.mp3 -acodec pcm_s16le -ar 44100 output.wav`
- WAV → MP3: `ffmpeg -i input.wav -acodec libmp3lame -b:a 192k output.mp3`
- DAT → MP3: `ffmpeg -i input.dat -vn -acodec libmp3lame -b:a 192k output.mp3`
- MP4 → M4A: `ffmpeg -i input.mp4 -vn -acodec aac -b:a 192k output.m4a`

**UX Improvements ✅ COMPLETE**
- **Audio Visualization Overlay:** Green glowing widget shows "🎵 Audio File Loaded" for audio-only files
- **Navigation Fix:** After trim/convert/extract, page stays on Audio Tools (auto-navigates back)
- **TimePickerWidget:** Custom QWidget with separate H/M/S spinners for better UX
  - Methods: `get_total_seconds()`, `set_total_seconds(seconds)`, `get_display_text()`
  - Displays time clearly in HH:MM:SS format
- **History Detection:** Audio files loaded from history now show visualization automatically

**Auto-Reload:** After export, file automatically loads into player (via handle_task_completion)

### 10. AUDIO EXTRACTION UI STATE MANAGEMENT ✅ COMPLETE
**Status:** Fixed - Extraction UI now properly updates for all loading scenarios

**Related files:**
- `source_code/main.py` → 
  - `update_extraction_ui(is_video)` helper method (new)
  - `load_audio_tools_file()` updated to call helper
  - `load_history_item()` updated to call helper
  - `handle_navigation_change()` updated to call helper
  - `show_audio_visualization()` enhanced with retry logic
  - `finish_loading()` delay increased to 150ms

**What Changed:**
- **New helper method `update_extraction_ui(is_video)`** centralizes all extraction UI logic
  - Shows extraction controls (checkbox, button, format selector) when is_video=True
  - Shows "Load a video to extract audio" message when is_video=False
  - Called from three locations to ensure consistency

- **Updated `load_audio_tools_file()`**
  - Detects file type (video vs audio) from extension
  - Calls `update_extraction_ui(is_video)` to update controls
  - Updates audio_file_status label with detected type

- **Updated `load_history_item()`**
  - Detects file type using extension sets (audio_exts and video_exts)
  - If on Audio Tools page, updates audio_tools_file_path and calls `update_extraction_ui()`
  - Ensures extraction UI is correct for files loaded from history

- **Updated `handle_navigation_change()`**
  - When navigating to Audio Tools page, detects current file type
  - Updates audio_file_status label if showing "No file loaded"
  - Calls `update_extraction_ui()` to show appropriate controls
  - Ensures UI is consistent when navigating after file is already loaded elsewhere

- **Enhanced `show_audio_visualization()`**
  - Retries with 100ms delay if frame dimensions are 0
  - Prevents early return before frame layout completes
  - Better visibility with 250 alpha (instead of 240)

**File Type Detection Logic:**
```python
video_exts = {'.mp4', '.avi', '.mkv', '.mov', '.webm'}
audio_exts = {'.mp3', '.wav', '.aac', '.m4a', '.flac', '.ogg', '.opus', '.wma'}
is_video = os.path.splitext(file_path)[1].lower() in video_exts
```

**Three File Loading Scenarios Now Handled:**
1. User opens file via "Load File" button → calls `load_audio_tools_file()`
2. User double-clicks file in history → calls `load_history_item()`
3. User loads file on another page, then navigates to Audio Tools → `handle_navigation_change()` detects and updates

### 11. AUDIO LOUDNESS NORMALIZATION (Feature 8) ✅ COMPLETE
**Status:** Fully Implemented - Normalizes audio to consistent LUFS level

**Related files:**
- `source_code/ui/extra_page.py` → Normalization tab with controls
- `source_code/main.py` → `normalize_audio()` method with FFmpeg loudnorm filter
- `documentation/IMPLEMENTATION_LOG.md` → Feature 8 implementation entry

**Feature 8: Audio Loudness Normalization ✅ COMPLETE**
- Normalizes audio files to consistent loudness levels using FFmpeg `loudnorm` filter
- Three preset LUFS targets for different use cases
- **UI Location:** Extra Tools → Audio Tools tab → Normalization section (Tab 4)
- **Controls:**
  - ☑ Normalize Loudness (checkbox, checked by default)
  - Target LUFS dropdown with three presets:
    - -14 LUFS (Streaming) - Spotify, Apple Music, YouTube
    - -16 LUFS (Broadcast) - TV, Radio standard
    - -18 LUFS (Loud) - Maximum output
  - "Normalize & Export" button (green, 35px height)

**FFmpeg Implementation:**
- Uses `loudnorm` audio filter with configurable LUFS targets
- Filter parameters: `loudnorm=I={LUFS_VALUE}:LRA=11:tp=-1.5`
  - I (Integrated LUFS): Target loudness level (-14, -16, or -18)
  - LRA (Loudness Range): 11 LUFS (standard range)
  - tp (True Peak): -1.5 dB (prevents clipping)
- Output format: WAV with 44100 Hz sample rate (CD quality)
- Output file naming: `{original_name}_normalized.wav`

**LUFS Standards:**
- **-14 LUFS**: Streaming platforms (loudest)
  - Spotify, Apple Music, YouTube Music use loudness normalization around this level
  - Best for: Modern streaming delivery, consistent across platforms
- **-16 LUFS**: Broadcast standard (medium)
  - Industry standard for broadcast TV and radio
  - Best for: Professional audio that needs to match broadcast specifications
- **-18 LUFS**: Loud output (quietest target)
  - Less common, use when maximum perceived loudness is needed
  - Caution: May risk clipping or audio artifacts

**Workflow:**
1. User loads audio or video file (any format)
2. Selects target LUFS from dropdown (default: -14 LUFS)
3. Ensures "Normalize Loudness" checkbox is checked
4. Clicks "Normalize & Export" button
5. FFmpeg analyzes audio and applies normalization filter
6. Output saved as `{filename}_normalized.wav` in download directory
7. File automatically loads into player (via handle_task_completion)

**Technical Details:**
- Two-pass processing: FFmpeg handles analysis and application in single command
- Loudnorm filter automatically detects input loudness and applies correct gain
- Output always PCM WAV format for maximum compatibility
- Sample rate standardized to 44100 Hz (CD quality)
- Processing preserves original duration and audio quality

### 12. DEPRECATED/DELETED FILES
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

### 13. GITIGNORE & LOCAL FILES
**Current:**
- config/history.json (local user data, not tracked)
- __pycache__/, *.pyc
- build_system/build/, build_system/dist/

**When adding local-only files:**
- Add to .gitignore
- Document in FOLDER_ORGANIZATION_SUMMARY.txt

### 14. DOCUMENTATION SYNC CHECKLIST
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
