---
name: file-dependencies-editing
description: 'Editing documentation/FILE_DEPENDENCIES.md (change checklist). Use when: planning any code change, identifying what files need updating, verifying documentation sync, tracking new features or versions.'
applyTo: 'documentation/FILE_DEPENDENCIES.md'
---

# Editing the File Dependencies Checklist

## File Role

`documentation/FILE_DEPENDENCIES.md` is the **source of truth** for what files need updating together.

**Purpose:**
- Prevents missed updates (e.g., adding a service but forgetting build spec)
- Identifies all dependent files for a given change type
- Serves as a planning checklist before making changes
- Ensures documentation stays in sync

**Coupling:** This file is referenced by:
- `.github/copilot-instructions.md` (points here as the first read)
- All agents planning code changes (read this before modifying code)
- Build process (validates bundled modules match imports)

---

## Before Editing

**Read the current structure:**
```markdown
### 1. VERSION UPDATES
**Files to update:** [list 6-8 files]

### 2. EXE NAME CHANGES
**Current:** KaraokeStudioProV3.exe
**Files to update:** [list 2-3 files]

### 3. BUILD SPEC HIDDEN IMPORTS
**File:** build_system/KaraokeStudioPro.spec → hiddenimports=[]
**Update when:** [conditions]
**Files to update:** [list affected files]

### 3b. BUNDLED TOOL BINARIES
**Files to update:** [list 4-5 files]

### 4. UI REFACTORING
**Current structure:** [UI file list]
**Files to update when modifying UI:** [list 4-5 files]
**Page index map (CRITICAL):** [table]
```

---

## When to Add a New Section

Add a new section to FILE_DEPENDENCIES.md when:

1. **Adding a major feature** that touches 3+ files
   - Example: "Feature 8: Audio Loudness Normalization"
   - Create section with: Files to update, Implementation details, Validation steps

2. **Discovering a new file coupling pattern**
   - Example: "Page index mapping must stay in sync across 3 files"
   - Creates a reusable checklist for future similar changes

3. **Making config/infrastructure changes**
   - Example: "Adding a new settings section"
   - Documents which files need updates

**Don't add:**
- Single-file changes (too granular)
- Temporary sections that only apply once (document in IMPLEMENTATION_LOG.md instead)

---

## Common Editing Patterns

### Adding a Feature Section

**When:** You implement a new feature that affects multiple files

**Format:**
```markdown
### [NUMBER]. [FEATURE NAME] (Currently: [version])
**Status:** [COMPLETE/IN PROGRESS/PLANNING]

**What changed:**
- New file: `path/to/file.py`
- Updated: `path/to/existing.py`
- Modified: `documentation/FILE` → section [N]

**Files to update:**
1. `file1.py` → [reason]
2. `file2.py` → [reason]
3. `build_system/KaraokeStudioPro.spec` → Add to hiddenimports: `'source_code.package.module'`
4. Documentation (all 5 files):
   - `FILE_DEPENDENCIES.md` → This section
   - `ARCHITECTURE.md` → Add module section
   - `FOLDER_ORGANIZATION_SUMMARY.txt` → Update structure
   - `DEVELOPMENT.md` → Add developer guidance
   - `IMPLEMENTATION_LOG.md` → Track changes

**Validation:**
- [ ] Syntax check: `python -m py_compile source_code\**\*.py`
- [ ] Tests pass: `pytest`
- [ ] All dependencies listed above were updated
```

### Adding a File Coupling Entry

**When:** You discover files that need updating together

**Format:**
```markdown
### [N]. [COUPLING NAME]
**Files to update:**
- File A → [reason for update]
- File B → [reason for update]
- File C → [reason for update]

**Why they're coupled:**
[Explanation of the dependency]

**Example:** [Concrete example of a change that touches all 3]
```

### Updating Version Information

**When:** Bumping version number

**Do this:**
1. Find all version-related sections (usually #1)
2. Update each reference: `v3` → `v4` (or similar)
3. Add entry to IMPLEMENTATION_LOG.md explaining why
4. Note: This typically affects 6-8 files simultaneously

---

## Critical Sections NOT to Remove

| Section | Why | Impact of Removal |
|---------|-----|-------------------|
| Section 3: Build Spec | Every new module needs this | New Python modules won't bundle in .exe |
| Section 3b: Bundled Binaries | FFmpeg/yt-dlp bundling | Missing executables in distribution |
| Section 4: UI Refactoring | Page indices must match | Pages load in wrong order |
| Page index map table | Central reference | Navigation breaks across pages |

---

## How Agents Use This File

**Agent workflow:**
1. User asks: "Add a feature that processes audio"
2. Agent reads FILE_DEPENDENCIES.md → finds audio feature pattern
3. Agent identifies all files to update simultaneously
4. Agent batches changes in one multi_replace call
5. Agent updates FILE_DEPENDENCIES.md last (confirms all dependencies were handled)

If this file is incomplete or wrong, the agent makes incomplete changes.

---

## After Editing

### Verification

1. **Check consistency across all listed files:**
   - Does `build_system/KaraokeStudioPro.spec` have the hiddenimports listed?
   - Does `ARCHITECTURE.md` document the new module?
   - Does `main.py` import everything listed?

2. **Verify nothing is missing:**
   - New service? Listed in FILE_DEPENDENCIES.md AND in build spec? ✓
   - New UI page? Listed in FILE_DEPENDENCIES.md AND in main.py AND in build spec? ✓
   - Changed dependencies? Updated FILE_DEPENDENCIES.md AND ARCHITECTURE.md? ✓

3. **Cross-reference check:**
   - Run build: `python build_system/build.py`
   - Build warnings about missing modules? → FILE_DEPENDENCIES.md is incomplete
   - Syntax errors? → Check all files listed in FILE_DEPENDENCIES.md

### When to Update FILE_DEPENDENCIES.md

**Always update when:**
- ✅ Adding new module/service/page
- ✅ Changing file structure (moving files, renaming packages)
- ✅ Bumping version
- ✅ Changing bundled tools
- ✅ Discovering a new file coupling pattern

**Don't update when:**
- ❌ Modifying logic inside a single file
- ❌ Fixing typos (covered by IMPLEMENTATION_LOG.md)
- ❌ Making local-only changes that don't affect builds/other files

---

## Common Mistakes

- ❌ Adding a feature section but forgetting to list build spec update → Next agent forgets to update spec
- ❌ Listing files but not explaining WHY each needs updating → Future developer confused about dependencies
- ❌ Updating FILE_DEPENDENCIES.md but forgetting to update the actual files → Documentation and code out of sync
- ❌ Removing outdated sections without archiving → Historical knowledge lost
- ❌ Page index map out of date → Pages load in wrong order, navigation breaks

---

## Related Files

- [`build_system/KaraokeStudioPro.spec`](...) — Must include all modules listed in section 3
- [`source_code/main.py`](...) — Imports must match section 4 UI list
- [`ARCHITECTURE.md`](ARCHITECTURE.md) — Should document all modules mentioned here
- [`DEVELOPMENT.md`](../DEVELOPMENT.md) — Should include developer guidance for patterns listed here
- [`IMPLEMENTATION_LOG.md`](IMPLEMENTATION_LOG.md) — Tracks which features/changes are complete

---

## Template for New Section

```markdown
### [N]. [CHANGE TYPE]
**Description:**
[What changes, why it matters]

**Files to update:**
1. `file1.py` → [what changes and why]
2. `file2.py` → [what changes and why]
3. `documentation/FILE.md` → [section updates]

**When to update:**
- [Condition 1]
- [Condition 2]

**Validation steps:**
- [ ] Check X file has Y entry
- [ ] Verify Z compiles
- [ ] Build produces correct output

**Related sections:** [Link to other FILE_DEPENDENCIES sections]
```

Use this when creating a new dependency checklist entry.
