# Development Guide - Karaoke Studio Pro v3

Complete development and contribution guide for Karaoke Studio Pro.

**For Copilot:** See `.copilot-instructions.md` (auto-loaded)

---

## ⚠️ CRITICAL: Read Before Making Changes

**ALWAYS read before modifying code or documentation:**
- [`documentation/FILE_DEPENDENCIES.md`](documentation/FILE_DEPENDENCIES.md) - Complete dependency checklist
- [`.copilot-instructions.md`](.copilot-instructions.md) - Copilot context

---

## Project Overview

**Karaoke Studio Pro v3** is a Python-based karaoke application with:
- Real-time audio monitoring (SPL & dBFS modes)
- YouTube video downloading and playback
- Configurable room-specific audio calibration
- Modularized UI architecture
- Standalone executable (zero external dependencies for end users)

---

## Development Environment Setup

### Prerequisites
```powershell
# Python 3.8+ required
python --version

# Install development dependencies
pip install -r documentation/requirements.txt

# For building
pip install -r build_system/requirements-build.txt
```

### Running Development Version
```powershell
cd d:\Srikanth\Academics\Python\karaoke-player
python source_code\main.py
```

### Building Standalone Executable
```powershell
cd d:\Srikanth\Academics\Python\karaoke-player
python build_system\build.py
# Output: build_system/dist/KaraokeStudioProV3/KaraokeStudioProV3.exe
```

---

## Project Structure

```
source_code/
├── main.py                    # App orchestrator & event handler
├── ui/                        # Modularized UI components (6 modules)
│   ├── main_layout.py        # Orchestrator assembling all UI
│   ├── sidebar.py            # Navigation & settings
│   ├── playback_bar.py       # Play/pause/volume/audio meter
│   ├── download_page.py      # File & URL loading
│   ├── pitch_page.py         # Pitch & speed controls
│   └── extra_page.py         # Video aspect ratio tool
├── services/
│   ├── audio_service.py      # Audio analyzer coordination
│   ├── player_service.py     # VLC player abstraction
│   └── download_service.py   # YouTube downloads
├── widgets/
│   ├── audio_meter.py        # Real-time audio visualization
│   └── video_frame.py        # Video display
├── workers/
│   ├── audio_analyzer.py     # Real-time audio capture (sounddevice)
│   └── process_thread.py     # Background processing
└── dialogs/
    └── settings_dialog.py    # Settings UI & configuration

build_system/
├── build.py                  # Build orchestrator script
├── KaraokeStudioPro.spec     # PyInstaller configuration
└── requirements-build.txt    # Build dependencies

documentation/
├── FILE_DEPENDENCIES.md      # ⭐ READ THIS BEFORE CHANGES
├── ARCHITECTURE.md           # Technical design
├── INSTALLATION.txt          # User guide
├── FOLDER_ORGANIZATION_SUMMARY.txt  # Project structure
└── requirements.txt          # Runtime dependencies

config/
├── settings.json             # User preferences
└── history.json              # Local data (NOT tracked in git)
```

---

## File Dependencies Reference

### When You Update... Update These Too:

| Change Type | Related Files |
|---|---|
| **Version bump** | build.py, spec, README, all docs |
| **New Python module** | spec (hiddenimports), main.py, docs |
| **Audio features** | audio_service.py, audio_meter.py, main.py, settings_dialog.py, settings.json, docs |
| **UI component** | ui/ files, spec, main.py, docs |
| **Settings field** | settings.json, settings_dialog.py, main.py |
| **New service/worker** | spec (hiddenimports), main.py, docs |

**See [`documentation/FILE_DEPENDENCIES.md`](documentation/FILE_DEPENDENCIES.md) for complete details.**

---

## Core Features (v3)

### Audio Calibration System
- **Modes:** SPL (Sound Pressure Level) ~60-90 dB or dBFS (raw -80 to 0 dB)
- **Auto-Reduce:** Configurable threshold (0-100%, default 80%)
- **Components:**
  - `audio_service.py` - Manages analyzer coordination
  - `audio_meter.py` - Dual-mode visualization
  - `audio_analyzer.py` - Real-time capture (sounddevice + numpy)

### Modularized UI
- All UI components in separate files (`source_code/ui/`)
- `main_layout.py` orchestrates assembly
- `main.py` handles event connections only
- Clean separation of concerns

### Settings System
- Schema-driven UI builder (supports file, directory, number, select types)
- Persistent JSON storage
- Audio-specific fields: measurement_mode, auto_reduce_threshold

---

## Making Changes: Step-by-Step

### Adding a New Audio Feature

1. **Implement in audio module**
   - Update `services/audio_service.py` or `widgets/audio_meter.py`

2. **Wire into settings**
   - Add field to `config/settings.json` schema
   - Add to `dialogs/settings_dialog.py` (schema + build_pages + accept_changes)

3. **Integrate in main app**
   - Update `main.py` to use new setting/feature
   - Call `audio_service.pause_analyzer()` before settings dialog if needed

4. **Update build**
   - Update `build_system/KaraokeStudioPro.spec` if new modules

5. **Document**
   - Update `documentation/INSTALLATION.txt` (features/config sections)
   - Update `documentation/ARCHITECTURE.md` (audio system)
   - Update `documentation/FOLDER_ORGANIZATION_SUMMARY.txt` (recent improvements)

### Adding a New UI Component

1. **Create in `source_code/ui/new_component.py`**
   - Function should return dict with all component references

2. **Add to `ui/main_layout.py`**
   - Import and call `create_new_component()`
   - Add to main layout assembly

3. **Update build spec**
   - Add `source_code.ui.new_component` to hiddenimports

4. **Update main.py**
   - Extract component references from returned dict

5. **Update documentation**
   - `documentation/FOLDER_ORGANIZATION_SUMMARY.txt`
   - `documentation/ARCHITECTURE.md` (UI section)

### Adding a New Setting

1. **Add to `config/settings.json`**
   ```json
   "new_setting": "default_value"
   ```

2. **Add to `dialogs/settings_dialog.py` schema**
   ```python
   "new_setting": {
       "label": "Display Label",
       "type": "file|directory|number|select",
       "default": "default_value"
   }
   ```

3. **Handle in `settings_dialog.py`**
   - `build_pages()` - Create UI widget
   - `accept_changes()` - Validate and save

4. **Use in `main.py`**
   - Access via `self.settings.get("new_setting")`

### Implementing Thread-Safe File Loading

**Important:** All file loading operations must go through the `FileLoadingService` to prevent audio analyzer conflicts and UI hangs.

#### Problem This Solves
Without proper coordination, switching pages and opening files causes:
- Audio analyzer signals conflicting with file dialogs
- UI event loop blocked during file operations
- App hangs when widen/export operations complete

#### Solution: FileLoadingService Pattern

The `FileLoadingService` coordinates state between file loading and audio monitoring:
```python
# In main.py __init__()
self.file_loading_service = FileLoadingService(self.audio_service, self.player)

# In load_video() method
def load_video(self, file_path=None):
    # Prepare: pause audio, process events, stop player
    was_playing = self.file_loading_service.prepare_for_loading()
    
    try:
        # Your file loading logic here
        self.player.set_media(file_path)
        self.player.play()
        # ... rest of load logic ...
    finally:
        # Cleanup: resume audio if it was playing
        self.file_loading_service.finish_loading(resume_audio=was_playing)
```

#### Adding a New File Loading Entry Point

**If adding another way to load files:**

1. Ensure all paths call `load_video()` (don't duplicate loading logic)
2. Example: "Open from Folder" button
   ```python
   open_folder_btn.clicked.connect(lambda: self.load_video())
   ```

3. Test by:
   - Opening file in download page ✓
   - Switching to pitch page immediately ✓
   - Opening another file - should not hang ✓
   - Switching to widen page and downloading ✓
   - Switching back and opening file - should not hang ✓

#### Files Affected by File Loading Changes
- `services/file_loading_service.py` - Core loading logic
- `services/audio_service.py` - Audio state coordination
- `main.py` - Usage and initialization
- Build spec (add to hiddenimports if creating new module)
- Documentation (ARCHITECTURE.md, FOLDER_ORGANIZATION_SUMMARY.txt, FILE_DEPENDENCIES.md)

---

## Testing Checklist

Before committing or building:

- [ ] `python source_code/main.py` runs without errors
- [ ] All UI components load and display correctly
- [ ] Audio meter shows values (SPL or dBFS)
- [ ] Settings dialog opens/closes without freezing
- [ ] Settings persist in `config/settings.json`
- [ ] Audio features work as expected
- [ ] **File loading:** Open file in download page ✓
- [ ] **File loading:** Switch pages quickly ✓
- [ ] **File loading:** Open multiple files in same page ✓
- [ ] **File loading:** Download and convert to 16:9 without hang ✓
- [ ] `python build_system/build.py` completes successfully
- [ ] `build_system/dist/KaraokeStudioProV3/KaraokeStudioProV3.exe` runs
- [ ] Documentation is consistent and up-to-date

---

## Code Quality Standards

### Imports
- Use absolute imports: `from source_code.services.audio_service import AudioService`
- Not relative: `from .audio_service import AudioService`

### Naming Conventions
- Classes: `PascalCase` (e.g., `AudioService`, `AudioLevelMeter`)
- Functions: `snake_case` (e.g., `create_main_layout()`, `pause_analyzer()`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `DEFAULT_THRESHOLD`)

### Threading
- Audio analyzer runs on QThread for non-blocking UI
- Always call `analyzer.stop()` and `analyzer.wait()` on exit
- Use `audio_service.cleanup()` for graceful shutdown

### Settings & Configuration
- Schema-driven (type validation built-in)
- Persist to JSON on changes
- Pause analyzer during settings dialogs to prevent conflicts

---

## Common Mistakes to Avoid

❌ **Don't create new Python module without updating build_system/KaraokeStudioPro.spec**
✅ Do check `documentation/FILE_DEPENDENCIES.md` first

❌ **Don't update only one doc when version changes**
✅ Do update all docs (README, ARCHITECTURE, INSTALLATION, FOLDER_ORGANIZATION)

❌ **Don't add settings only to settings.json**
✅ Do wire them in settings_dialog.py AND main.py

❌ **Don't open settings dialog without pausing audio analyzer**
✅ Do call `audio_service.pause_analyzer()` before dialog

❌ **Don't close app while audio analyzer is running**
✅ Do call `audio_service.cleanup()` in closeEvent()

---

## Resources

- **Dependencies Reference:** [`documentation/FILE_DEPENDENCIES.md`](documentation/FILE_DEPENDENCIES.md)
- **Architecture Details:** [`documentation/ARCHITECTURE.md`](documentation/ARCHITECTURE.md)
- **User Guide:** [`documentation/INSTALLATION.txt`](documentation/INSTALLATION.txt)
- **Project Structure:** [`documentation/FOLDER_ORGANIZATION_SUMMARY.txt`](documentation/FOLDER_ORGANIZATION_SUMMARY.txt)

---

## Questions or Issues?

1. Check the relevant documentation file
2. Search `documentation/FILE_DEPENDENCIES.md` for related files
3. Run tests to verify nothing broke
4. Document your changes in commit message

Happy coding! 🎤🚀
