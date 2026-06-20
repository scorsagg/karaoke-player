# 🎤 Karaoke Studio Pro - Development Instructions for Copilot

**If you see this file, context is loaded correctly for this session.**

---

## 📋 SESSION STARTUP ACKNOWLEDGMENT

**IMPORTANT:** When you load a new session and see these instructions, you MUST:

1. ✅ Display startup message to user (below)
2. ✅ **READ ALL DOCUMENTATION FILES** (new requirement - see "Initial Documentation Review")
3. ✅ Follow the change workflow

**After reading docs, display:**
```
✅ Copilot initialized for Karaoke Studio Pro v3
📚 Instructions loaded from .github/copilot-instructions.md
📚 Documentation reviewed (DEVELOPMENT.md, ARCHITECTURE.md, FILE_DEPENDENCIES.md, etc.)
📋 Workflow enabled:
   1. Complete project documentation context loaded
   2. Always check FILE_DEPENDENCIES.md before changes
   3. Update all related files together
   4. Reference DEVELOPMENT.md for guidance
```

---

## 📖 INITIAL DOCUMENTATION REVIEW (New Session Requirement)

**BEFORE ANY WORK:** Read these files to understand current project state:
1. `DEVELOPMENT.md` - Complete architecture and development guide
2. `ARCHITECTURE.md` - System design and component relationships
3. `documentation/FILE_DEPENDENCIES.md` - File dependency tracking
4. `documentation/IMPLEMENTATION_LOG.md` - Recent changes and solutions
5. `documentation/FOLDER_ORGANIZATION_SUMMARY.txt` - Project structure
6. `.github/copilot-instructions.md` - This file

**Why:** Avoids rework, uses fewer tokens, maintains context accuracy, understands current patterns

---

## ⚠️ CRITICAL: Before Making ANY Changes

1. **Read:** `documentation/FILE_DEPENDENCIES.md`
   - Identifies ALL related files that need updating together
   - Prevents missed updates (e.g., build spec, documentation)

2. **Reference:** `DEVELOPMENT.md`
   - Complete development guide
   - Setup, architecture, common tasks

---

## New Session Workflow

When starting a new session:
1. ✅ You see this file → context loaded
2. ✅ Check `documentation/FILE_DEPENDENCIES.md` BEFORE any changes
3. ✅ Reference `DEVELOPMENT.md` for detailed guidance
4. ✅ Update ALL related files together (don't miss dependencies!)

---

## Quick Reference

### Project Context
- **Version:** v3
- **Executable:** `KaraokeStudioProV3.exe`
- **Main App:** `source_code/main.py`
- **Build:** `build_system/build.py`

### Before Making Changes
| Type of Change | Check These Files |
|---|---|
| New Python module | FILE_DEPENDENCIES.md → Build spec update |
| Audio feature | FILE_DEPENDENCIES.md → 7 files to update |
| UI modification | FILE_DEPENDENCIES.md → spec + main.py + docs |
| Version bump | FILE_DEPENDENCIES.md → 7+ files to update |
| New setting | FILE_DEPENDENCIES.md → settings.json + dialog + main.py |

**All details in:** `documentation/FILE_DEPENDENCIES.md` and `DEVELOPMENT.md`

---

## ⚙️ CHANGE IMPLEMENTATION WORKFLOW (MANDATORY)

**Every time you make changes, follow this exact workflow:**

### Step 1: Plan
1. ✅ Read `documentation/FILE_DEPENDENCIES.md` 
2. ✅ Identify ALL affected files from the dependency checklist
3. ✅ Don't proceed until you've listed all related files

### Step 2: Implement
1. ✅ Make code changes in primary files
2. ✅ Update build spec (`KaraokeStudioPro.spec`) if adding new modules
3. ✅ Don't skip the build spec - it WILL break the executable

### Step 3: Document (CRITICAL - Always Do This)
**Update documentation in this order:**
1. ✅ `documentation/FILE_DEPENDENCIES.md` - Add/update entry for your change type
2. ✅ `documentation/ARCHITECTURE.md` - Document new components/services
3. ✅ `documentation/FOLDER_ORGANIZATION_SUMMARY.txt` - Reflect new file structure
4. ✅ `DEVELOPMENT.md` - Add guidance for future developers
5. ✅ Create/update `documentation/IMPLEMENTATION_LOG.md` - Track what changed and why

### Step 4: Verify
1. ✅ Check all modified files for syntax errors
2. ✅ Verify documentation is consistent across all files
3. ✅ Confirm all dependency files listed in FILE_DEPENDENCIES.md were updated

---

## ⚡ TOKEN EFFICIENCY RULES (Critical for Budget)

**Get it RIGHT the first time - no rework!**

1. **Before making ANY edits:**
   - Read the complete context needed (do parallel reads, not sequential)
   - Plan ALL changes at once
   - Use multi_replace_string_in_file for multiple edits in one call
   - Never make multiple sequential edits when one parallel call will work

2. **When reading files:**
   - Read large ranges in single calls (not many small reads)
   - Parallel-read unrelated files together
   - Use grep_search for targeted lookups in large files

3. **When editing:**
   - Batch related edits together
   - Plan includes 3-5 lines of context to avoid failed replacements
   - Double-check oldString EXACTLY matches (spacing, newlines, characters)
   - One replacement attempt per string (failed attempts waste tokens)

4. **When problem-solving:**
   - Understand root cause completely before fixing
   - Implement correct solution first time (not incremental fixes)
   - Reference existing patterns instead of designing new approaches

5. **Documentation:**
   - Update all 5 sync files together in ONE multi_replace call
   - Don't create new summary files (too expensive, keep in memory instead)

---

## 📚 Documentation Sync Rules

**These files MUST stay in sync:**
- `FILE_DEPENDENCIES.md` ← Source of truth for what needs updating
- `ARCHITECTURE.md` ← Technical design documentation
- `FOLDER_ORGANIZATION_SUMMARY.txt` ← Project structure
- `DEVELOPMENT.md` ← Developer guide with patterns
- `IMPLEMENTATION_LOG.md` ← Change history for reference

**When you update code, also update these 5 docs.**
**If you don't update all 5, the documentation is INCOMPLETE.**

---

## Key Files

- `documentation/FILE_DEPENDENCIES.md` ⭐ READ FIRST (Source of truth for dependencies)
- `DEVELOPMENT.md` - Full dev guide with patterns and examples
- `documentation/IMPLEMENTATION_LOG.md` - Recent changes and implementation details

---

## Recent Implementation: Audio Loudness Normalization (Feature 8) (v3)

**Status:** ✅ COMPLETE & WORKING

**What changed:**
- Added: `source_code/ui/extra_page.py` (normalize tab with controls)
- Added: `source_code/main.py` (normalize_audio() method)

**The Feature:** Normalizes audio to consistent LUFS levels for streaming/broadcast standards
- Three presets: -14 LUFS (Streaming), -16 LUFS (Broadcast), -18 LUFS (Loud)
- FFmpeg `loudnorm` filter with automatic gain application
- Output: WAV format with 44100 Hz sample rate

**Why It Works:** 
- Uses industry-standard LUFS (Loudness Units relative to Full Scale) measurement
- Three-second analysis + automatic gain calculation
- Preserves audio quality while normalizing loudness

**For future developers:** See `documentation/FILE_DEPENDENCIES.md` section 11 for complete Feature 8 details and `IMPLEMENTATION_LOG.md` for implementation specifics

---

## Previous Implementation: Audio Tools Extraction UI Fix (v3)

**Status:** ✅ COMPLETE & WORKING

**What changed:**
- Fixed: `source_code/services/file_loading_service.py` (removed player.stop() call, added pause-based cleanup)
- Updated: `source_code/services/player_service.py` (added pause() method)
- Updated: `source_code/services/audio_service.py` (enhanced thread recreation)
- Updated: `source_code/main.py` (audio_service helper methods)
- Docs: All 5 sync files updated with final solution

**The Problem:** App hung indefinitely when loading second file - VLC's stop() hangs with active decoder threads

**The Solution:** Don't call stop(). Instead: pause → wait 1.0s → stop audio analyzer → release media reference → wait 0.5s → load new file (VLC auto-cleanup)

**Why It Works:** 
- VLC decoder threads stay alive even after pause
- Calling stop() tries to wait for them → DEADLOCK
- Solution avoids the wait by just releasing reference
- VLC auto-cleans old media when new media is set

**For future developers:** See `documentation/IMPLEMENTATION_LOG.md` for complete debugging journey and `ARCHITECTURE.md` FileLoadingService section for how it works

**Status after fix:** 5+ consecutive file loads without any hangs ✅

---

## Recent Implementation: Audio Tools Features 6&7 with H/M/S Time Picker (v3)

**Status:** ✅ COMPLETE & FULLY TESTED

**Features Implemented:**
- ✅ Feature 6: Audio Trimming (trim first/last/keep range with combinations)
- ✅ Feature 7: Format Conversion (MP3, WAV, M4A, AAC, MP4, MKV, AVI, WebM with quality control)
- ✅ TimePickerWidget: Custom UI component with separate H/M/S spinners
- ✅ Audio Overlay: Visual indicator "🎵 Audio File Loaded" for audio files
- ✅ Navigation Fix: Page stays on Audio Tools after trim/convert/extract
- ✅ History Detection: Audio files from history show overlay automatically

**What changed:**
- **Created:** `TimePickerWidget` class in `source_code/ui/extra_page.py` (lines 6-36)
  - Three QSpinBox widgets (hours 0-59, minutes 0-59, seconds 0-59)
  - Methods: `get_total_seconds()`, `set_total_seconds(seconds)`, `get_display_text()`
  - Display format: HH:MM:SS with independent increment buttons
- **Updated:** `source_code/ui/extra_page.py` - Trim spinners use TimePickerWidget (lines 167-197)
- **Updated:** `source_code/main.py`
  - Added `audio_overlay` widget, `create_audio_overlay()`, `show_audio_visualization()`, `hide_audio_visualization()`
  - Added `load_history_item()` for audio format detection
  - Added `is_audio_only` parameter to `load_video()` and `finish_loading()`
  - Updated `trim_audio()` to use `get_total_seconds()` instead of `value()`
  - Updated `handle_task_completion()` to auto-navigate back to Audio Tools page
- **Updated:** `extract_audio_from_video()` to show overlay
- **Updated:** All 5 documentation files with completion markers

**UX Improvements:**
- **No More Typing:** Each time unit (hours, minutes, seconds) has independent spinners
- **Clear Display:** HH:MM:SS format shows exact time selected
- **Visual Feedback:** Green "🎵 Audio File Loaded" overlay confirms audio is playing
- **Navigation Stability:** Users stay on Audio Tools page after any operation
- **Smart History:** Loading audio files from history auto-detects format and shows overlay

**Dependencies:** No new packages added (TimePickerWidget uses only PySide6 primitives)

**Validation:**
- ✅ Syntax check passed (exit code 0)
- ✅ H/M/S spinners parse correctly (1:30 = 5400 seconds)
- ✅ Multiple trim operations combined successfully
- ✅ Format conversion handles all formats
- ✅ Navigation stays on Audio Tools page after trim/convert/extract
- ✅ Audio overlay displays for audio-only files
- ✅ History detection works for audio formats

**For future developers:** See `documentation/FILE_DEPENDENCIES.md` section 9 for TimePickerWidget details, `FEATURE_IMPLEMENTATION_GUIDE.md` for Features 6&7 implementation details, and `ARCHITECTURE.md` for system design

---


## Common Tasks Checklist

**Adding a New Service:**
- [ ] Create file in `source_code/services/`
- [ ] Add to `build_system/KaraokeStudioPro.spec` hiddenimports
- [ ] Import and init in `main.py`
- [ ] Update 5 docs (FILE_DEPENDENCIES, ARCHITECTURE, FOLDER_ORGANIZATION, DEVELOPMENT, IMPLEMENTATION_LOG)

**Adding a New UI Component:**
- [ ] Create in `source_code/ui/`
- [ ] Add to `ui/main_layout.py`
- [ ] Add to build spec hiddenimports
- [ ] Update 5 docs

**Modifying Audio Features:**
- [ ] Update audio_service.py or audio_meter.py
- [ ] Update settings in dialogs/settings_dialog.py
- [ ] Update 5 docs

**ANY Change Type:**
1. Check FILE_DEPENDENCIES.md for what to update
2. Make changes
3. Update all 5 docs
4. Test syntax

**Adding a New Service:**
- [ ] Create file in `source_code/services/`
- [ ] Add to `build_system/KaraokeStudioPro.spec` hiddenimports
- [ ] Import and init in `main.py`
- [ ] Update 5 docs (FILE_DEPENDENCIES, ARCHITECTURE, FOLDER_ORGANIZATION, DEVELOPMENT, IMPLEMENTATION_LOG)

**Adding a New UI Component:**
- [ ] Create in `source_code/ui/`
- [ ] Add to `ui/main_layout.py`
- [ ] Add to build spec hiddenimports
- [ ] Update 5 docs

**Modifying Audio Features:**
- [ ] Update audio_service.py or audio_meter.py
- [ ] Update settings in dialogs/settings_dialog.py
- [ ] Update 5 docs

**ANY Change Type:**
1. Check FILE_DEPENDENCIES.md for what to update
2. Make changes
3. Update all 5 docs
4. Test syntax
5. Done
