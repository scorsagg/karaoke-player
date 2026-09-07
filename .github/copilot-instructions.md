# 🎤 Karaoke Studio Pro v3 - Development Context for AI Agents

## Project Overview

**Karaoke Studio Pro v3** is a Python/PySide6 karaoke application with:
- Real-time audio monitoring, YouTube downloads, video/audio playback
- Audio tools: trimming, format conversion, extraction, loudness normalization
- Modular architecture: controllers, services, UI pages
- Standalone executable (PyInstaller bundle)

**Key Files:**
- Main app: [`source_code/main.py`](source_code/main.py)
- Build: [`build_system/build.py`](build_system/build.py) & [`build_system/KaraokeStudioPro.spec`](build_system/KaraokeStudioPro.spec)
- Setup: [`DEVELOPMENT.md`](DEVELOPMENT.md) (setup, architecture, testing)
- Architecture: [`documentation/ARCHITECTURE.md`](documentation/ARCHITECTURE.md)

---

## ⚠️ BEFORE MAKING ANY CHANGES

**ALWAYS read first:**
1. [`documentation/FILE_DEPENDENCIES.md`](documentation/FILE_DEPENDENCIES.md) ⭐ — Identifies ALL files to update together
2. [`DEVELOPMENT.md`](DEVELOPMENT.md) — Full development guide

This prevents missed updates and broken builds.

---

## Change Workflow

### 1. Plan (Read Dependencies)
Consult [`documentation/FILE_DEPENDENCIES.md`](documentation/FILE_DEPENDENCIES.md):
- New module → Add to build spec + main.py imports
- UI change → Update main_layout.py + build spec + docs
- New service → Create in `source_code/services/` + build spec + main.py
- Version bump → Multiple files need updating

### 2. Implement
Make primary code changes. **Do NOT skip the build spec** for new modules—it breaks the executable.

### 3. Update Documentation
Always update these 5 files together (use multi-edit in one call):
1. [`documentation/FILE_DEPENDENCIES.md`](documentation/FILE_DEPENDENCIES.md) — Add/update entry
2. [`documentation/ARCHITECTURE.md`](documentation/ARCHITECTURE.md) — Document new components
3. [`documentation/FOLDER_ORGANIZATION_SUMMARY.txt`](documentation/FOLDER_ORGANIZATION_SUMMARY.txt) — Reflect structure
4. [`DEVELOPMENT.md`](DEVELOPMENT.md) — Add developer guidance
5. [`documentation/IMPLEMENTATION_LOG.md`](documentation/IMPLEMENTATION_LOG.md) — Track changes

### 4. Verify
- Syntax check all modified files
- Confirm all dependencies in FILE_DEPENDENCIES.md were updated
- If adding modules, verify build spec entry exists

---

## Project Structure (Key Directories)

```
source_code/
├── main.py                      # Entry point & event handler
├── controllers/                 # Orchestration (playback, media, processing, navigation)
├── services/                    # Core features (player, download, audio, file loading)
├── ui/                          # Pages (media_loader, pitch, audio_studio, video_tools, convert_export)
├── dialogs/                     # Settings dialog
└── models/                      # app_state.py (runtime state)

build_system/                    # PyInstaller build configuration
documentation/                   # Architecture, dependencies, implementation log
resources/                       # Bundled FFmpeg, yt-dlp, libvlc (for .exe)
```

See [`documentation/ARCHITECTURE.md`](documentation/ARCHITECTURE.md) for full module details.

---

## Common Patterns

**Feature-specific files to check:**
- Audio features → `source_code/services/audio_service.py`, `ui/audio_studio_page.py`
- Playback → `source_code/services/player_service.py`, `controllers/playback_controller.py`
- Video processing → `source_code/ui/video_tools_page.py`, `controllers/processing_controller.py`
- Settings → `dialogs/settings_dialog.py`, `config/settings.json`

**Bundled tools** (resources/):
- `ffmpeg.exe` — Encoding/transcoding
- `yt-dlp.exe` — YouTube downloads
- `ffprobe.exe` — Media probing
Update `build_system/build.py` validation if changing these.

---

## Documentation Sync Rule

**These 5 files MUST stay in sync:**
- FILE_DEPENDENCIES.md (source of truth for dependencies)
- ARCHITECTURE.md (technical design)
- FOLDER_ORGANIZATION_SUMMARY.txt (project structure)
- DEVELOPMENT.md (developer guide)
- IMPLEMENTATION_LOG.md (change history)

Update all 5 after code changes. Use multi-edit for efficiency.

---

## Token Efficiency

- **Before editing**: Read all needed context in parallel, plan all changes at once
- **When editing**: Batch related changes in one multi_replace_string_in_file call
- **When reading**: Use large ranges, not sequential small reads
- **When documenting**: Update all 5 sync files together in one call

---

## Quick Checklist: Making Any Change

- [ ] Read FILE_DEPENDENCIES.md
- [ ] List all affected files
- [ ] Make code changes + update build spec if needed
- [ ] Update all 5 docs together
- [ ] Verify syntax
- [ ] Confirm FILE_DEPENDENCIES.md entries were updated
