# 🎤 Karaoke Studio Pro - Development Instructions for Copilot

**If you see this file, context is loaded correctly for this session.**

---

## 📋 SESSION STARTUP ACKNOWLEDGMENT

**IMPORTANT:** When you load a new session and see these instructions, you MUST display this exact message to the user:

```
✅ Copilot initialized for Karaoke Studio Pro v3
📚 Instructions loaded from .github/copilot-instructions.md
📋 Workflow enabled:
   1. Always check documentation/FILE_DEPENDENCIES.md before changes
   2. Update all related files together
   3. Reference DEVELOPMENT.md for guidance
```

Display this message immediately, then proceed with the user's request following the workflow below.

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

## Recent Implementation: Final Fix for File Loading Hang (v3)

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
5. Done
