---
name: docs-sync-editing
description: 'Editing the 5-file documentation sync (FILE_DEPENDENCIES.md, ARCHITECTURE.md, FOLDER_ORGANIZATION_SUMMARY.txt, DEVELOPMENT.md, IMPLEMENTATION_LOG.md). Use when: completing feature implementations, updating project structure, refactoring code, ensuring documentation consistency.'
---

# Maintaining Documentation Sync (5-File Rule)

## The Rule

**These 5 files MUST stay in sync:**

1. [`documentation/FILE_DEPENDENCIES.md`](../../documentation/FILE_DEPENDENCIES.md) — Source of truth for dependencies
2. [`documentation/ARCHITECTURE.md`](../../documentation/ARCHITECTURE.md) — Technical design, module structure
3. [`documentation/FOLDER_ORGANIZATION_SUMMARY.txt`](../../documentation/FOLDER_ORGANIZATION_SUMMARY.txt) — Project folder structure
4. [`DEVELOPMENT.md`](../../DEVELOPMENT.md) — Developer guide, patterns, setup instructions
5. [`documentation/IMPLEMENTATION_LOG.md`](../../documentation/IMPLEMENTATION_LOG.md) — Change history and solutions

**If any changes are made to code or files, update all 5 docs together in one pass.**

---

## Each File's Role

| File | Owns | Updates When |
|------|------|--------------|
| FILE_DEPENDENCIES.md | What files need updating together | Adding features, version bumps, new modules |
| ARCHITECTURE.md | System design, module relationships, data flow | Adding components, changing architecture |
| FOLDER_ORGANIZATION_SUMMARY.txt | Visual project tree, file locations | Renaming folders, moving files |
| DEVELOPMENT.md | Developer patterns, setup, common tasks | Adding new patterns, workflow changes |
| IMPLEMENTATION_LOG.md | Recent changes, solutions, and debugging info | After completing features, significant fixes |

---

## Update Workflow

### Step 1: Plan Your Changes

Before coding, read FILE_DEPENDENCIES.md to identify all affected files.

### Step 2: Make Code Changes

Implement your feature across all affected files.

### Step 3: Update Documentation (In This Order)

#### 1️⃣ Update FILE_DEPENDENCIES.md

**What to add:**
- New section describing what files to update for similar future changes
- List affected files with specific reasons
- Include validation steps

**Example** (if adding new service):
```markdown
### N. NEW SERVICE SETUP
**Files to update:**
1. `source_code/services/new_service.py` → Create new service
2. `source_code/main.py` → Import and instantiate
3. `build_system/KaraokeStudioPro.spec` → Add to hiddenimports
4. [Link to this file] → Add this entry
5. ARCHITECTURE.md → Document new module
6. FOLDER_ORGANIZATION_SUMMARY.txt → Update services folder listing
7. DEVELOPMENT.md → Add pattern documentation
8. IMPLEMENTATION_LOG.md → Track completion
```

#### 2️⃣ Update ARCHITECTURE.md

**What to add:**
- New module section with responsibility description
- Integration points (what calls it, what it calls)
- Data flow (what it receives/returns)
- Any new patterns or design decisions

**Example** (if adding new service):
```markdown
### new_service.py
**Purpose:** [Description]
**Interfaces:** 
- Called by: [controller/page]
- Calls: [other services/external tools]
**Key Methods:**
- `method_name()` → [What it does]
**Integration:** Connected in main.py during `__init__`, accessible to controllers
```

#### 3️⃣ Update FOLDER_ORGANIZATION_SUMMARY.txt

**What to add:**
- Add new file to correct folder section
- Update folder descriptions if changed
- Keep tree structure consistent

**Example** (if adding new service):
```
source_code/services/
├── __init__.py
├── audio_service.py
├── download_service.py
├── file_loading_service.py
├── new_service.py              ← Add here
├── player_service.py
└── realtime_pitch_service.py
```

#### 4️⃣ Update DEVELOPMENT.md

**What to add:**
- New section in "Common Patterns" or "Architecture" if you introduced a new pattern
- Update examples if behavior changed
- Add troubleshooting if you discovered gotchas

**Example** (if adding new service):
```markdown
### Using New Service

To use the new service in your code:
```python
# In a controller
from services.new_service import NewService
class MyController:
    def __init__(self, new_service):
        self.new_service = new_service
```

See [ARCHITECTURE.md](documentation/ARCHITECTURE.md) for module structure.
```

#### 5️⃣ Update IMPLEMENTATION_LOG.md

**What to add:**
- **Status:** COMPLETE / IN PROGRESS / PLANNING
- **Date:** When completed
- **Change Summary:** What was changed and why
- **Files Modified:** List all modified files
- **Testing:** What was tested and how
- **Notes:** Any gotchas, workarounds, or follow-up work

**Example** (if adding new service):
```markdown
## Feature: [Feature Name] (v3)

**Status:** ✅ COMPLETE  
**Date:** 2026-09-01  

**What Changed:**
- Added: `source_code/services/new_service.py`
- Updated: `source_code/main.py` (import + instantiate)
- Updated: `build_system/KaraokeStudioPro.spec` (hiddenimports)
- Updated: All 5 documentation files

**Validation:**
- ✅ Syntax check: Exit code 0
- ✅ Tests pass: pytest passes
- ✅ .exe builds without warnings
- ✅ Feature works as expected

**Notes:**
- [Any gotchas or implementation details]
- [Follow-up work if needed]

See FILE_DEPENDENCIES.md section [N] for complete checklist.
```

---

## Consistency Checklist

After updating all 5 files:

- [ ] FILE_DEPENDENCIES.md lists all affected files
- [ ] ARCHITECTURE.md documents new/modified modules
- [ ] FOLDER_ORGANIZATION_SUMMARY.txt shows updated file structure
- [ ] DEVELOPMENT.md explains how to use new features/patterns
- [ ] IMPLEMENTATION_LOG.md tracks the change with status and date
- [ ] All cross-references (links) are correct
- [ ] No duplicate information across files
- [ ] IMPLEMENTATION_LOG.md status matches actual completion state

---

## What Each File Links To

```
FILE_DEPENDENCIES.md
  ↓ Points to:
  └── ARCHITECTURE.md (for full module descriptions)
  └── build_system/KaraokeStudioPro.spec (for hidden imports)
  └── DEVELOPMENT.md (for developer patterns)
  
ARCHITECTURE.md
  ↓ Points to:
  └── DEVELOPMENT.md (for usage patterns)
  └── IMPLEMENTATION_LOG.md (for implementation details)
  
DEVELOPMENT.md
  ↓ Points to:
  └── FILE_DEPENDENCIES.md (for dependency checklists)
  └── ARCHITECTURE.md (for module structure)
  └── IMPLEMENTATION_LOG.md (for recent solutions)
  
IMPLEMENTATION_LOG.md
  ↓ Points to:
  └── FILE_DEPENDENCIES.md (for what was updated)
  └── ARCHITECTURE.md (for affected modules)
```

---

## Common Mistakes

- ❌ Update code but not all 5 docs → Documentation and code drift apart
- ❌ Update only 3 of 5 docs → Future developer confused about design
- ❌ Copy content instead of linking → Duplication causes maintenance burden
- ❌ Forget to update IMPLEMENTATION_LOG.md → No record of what changed or when
- ❌ Update docs but not ARCHITECTURE.md module descriptions → New developers don't understand design
- ❌ Old sections in IMPLEMENTATION_LOG.md not marked with status → Unclear what's current vs outdated

---

## When to Break the 5-File Rule (Almost Never)

**Only skip documentation if:**
- Fixing a typo (single file, 1-2 words)
- Updating comments only (no behavior change)
- Local testing that won't be committed

**Always update all 5 when:**
- Adding new modules/features
- Changing architecture/structure
- Modifying workflows
- Version bumps
- Significant bug fixes with pattern implications

---

## Editor Tip: Multi-Edit Approach

**Efficient workflow:**
1. Read all 5 files in sequence to understand current state
2. Plan what each file needs
3. Use multi_replace_string_in_file to update all 5 files in one operation
4. Verify cross-references are correct

This saves tokens and ensures consistency.

---

## Related Files & Resources

- [`documentation/FILE_DEPENDENCIES.md`](../../documentation/FILE_DEPENDENCIES.md) — Source of truth
- [`documentation/ARCHITECTURE.md`](../../documentation/ARCHITECTURE.md) — Technical reference
- [`documentation/FOLDER_ORGANIZATION_SUMMARY.txt`](../../documentation/FOLDER_ORGANIZATION_SUMMARY.txt) — Structure
- [`DEVELOPMENT.md`](../../DEVELOPMENT.md) — Developer guide
- [`documentation/IMPLEMENTATION_LOG.md`](../../documentation/IMPLEMENTATION_LOG.md) — Change history
- [`.github/copilot-instructions.md`](...) — Points to this rule as critical
