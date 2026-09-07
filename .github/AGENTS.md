---
name: AGENTS
description: Specialized agent modes for Karaoke Studio Pro development
---

# Karaoke Studio Pro v3 — Specialized Agent Modes

Use these agents for specialized development tasks. Invoke with `/add-feature`, `/fix-build`, `/update-docs`, etc.

---

## `/add-feature` — Feature Implementation Agent

**When to use:** Adding a new feature that affects multiple files (services, UI, controllers, build spec, documentation)

**Agent focus:**
- Read FILE_DEPENDENCIES.md FIRST to understand all affected files
- Plan complete change list before coding
- Ensure build spec includes new modules
- Update all 5 documentation files together

**Constraints:**
- Cannot commit changes (AI doesn't have git access)
- Must provide complete checklist of files modified
- Validates build spec against new modules

**Workflow:**
1. Consult FILE_DEPENDENCIES.md for similar features
2. Identify all affected files (services, UI, controllers, build spec, docs)
3. Make code changes
4. Update build spec if new modules added
5. Update all 5 docs in one pass
6. Verify syntax and provide summary

**Example invocation:**
```
/add-feature Add audio loudness normalization to Convert & Export page
```

---

## `/fix-build` — Build & Dependency Management Agent

**When to use:** Troubleshooting build failures, missing imports, bundled tool issues, or .exe runtime errors

**Agent focus:**
- Diagnose build failures from error logs
- Identify missing hiddenimports in build spec
- Verify resources/bundled tools exist
- Rebuild and test .exe

**Constraints:**
- Restricted to build system files and documentation
- Cannot modify core application logic
- Must validate changes before suggesting

**Workflow:**
1. Analyze build error or .exe failure
2. Check build_system/KaraokeStudioPro.spec for missing imports
3. Verify resources/ contains required binaries
4. Update build spec or copy missing files
5. Run build script and validate
6. Document solution in IMPLEMENTATION_LOG.md

**Example invocation:**
```
/fix-build ModuleNotFoundError: No module named 'source_code.services.new_service'
```

---

## `/update-docs` — Documentation Maintenance Agent

**When to use:** Updating project documentation, syncing the 5-file docs after code changes, or maintaining guides

**Agent focus:**
- Maintain the 5-file documentation sync rule
- Update FILE_DEPENDENCIES.md for new patterns
- Keep ARCHITECTURE.md current
- Add entries to IMPLEMENTATION_LOG.md

**Constraints:**
- Cannot modify code
- Focuses on documentation consistency
- Must follow the 5-file sync workflow

**Workflow:**
1. Read all 5 documentation files to understand current state
2. Identify what needs updating based on changes
3. Update FILE_DEPENDENCIES.md → ARCHITECTURE.md → FOLDER_ORGANIZATION → DEVELOPMENT.md → IMPLEMENTATION_LOG.md
4. Verify cross-references are correct
5. Provide summary of changes

**Example invocation:**
```
/update-docs New realtime_audio_analyzer service added, need to sync documentation
```

---

## `/refactor` — Code Refactoring Agent

**When to use:** Restructuring code, renaming modules, improving architecture, extracting duplicated logic

**Agent focus:**
- Understand current architecture before changes
- Maintain functionality during refactoring
- Update FILE_DEPENDENCIES.md with new structure
- Verify all imports still work
- Run tests to confirm no regressions

**Constraints:**
- Must run tests before completing
- Cannot change external interfaces without updating all callers
- Must update documentation to reflect new structure
- Build must succeed after changes

**Workflow:**
1. Map all files affected by refactoring
2. Create refactoring plan and verify with FILE_DEPENDENCIES.md
3. Make code changes
4. Update all imports and references
5. Run tests: `pytest`
6. Build: `python build_system/build.py`
7. Update all 5 docs
8. Provide list of all modified files

**Example invocation:**
```
/refactor Extract common audio processing logic into shared utility module
```

---

## `/debug-issue` — Debugging & Diagnostics Agent

**When to use:** Debugging runtime errors, app crashes, feature not working, or investigating unexpected behavior

**Agent focus:**
- Read error messages and stack traces
- Trace code execution path
- Identify root cause
- Propose fix and verify
- Document solution in IMPLEMENTATION_LOG.md

**Constraints:**
- Limited to diagnosis and investigation (not automatic fixes)
- Should run app or tests to reproduce issue
- Must verify fix doesn't break other functionality
- Should document debugging process for future reference

**Workflow:**
1. Gather error details (stack trace, conditions to reproduce)
2. Trace code path from error to source
3. Identify root cause
4. Propose minimal fix
5. Verify fix works and doesn't break tests
6. Document solution and learnings in IMPLEMENTATION_LOG.md

**Example invocation:**
```
/debug-issue App hangs when loading second video file after playing first one
```

---

## `/validate-changes` — Quality Assurance Agent

**When to use:** Before committing, validating that all changes are complete and correct

**Agent focus:**
- Verify all modified files are syntactically correct
- Confirm FILE_DEPENDENCIES.md entries were followed
- Run tests to ensure no regressions
- Build .exe to ensure distribution readiness
- Provide comprehensive validation report

**Constraints:**
- Read-only verification (doesn't make changes)
- Must run all validation checks
- Reports any incomplete updates or errors

**Workflow:**
1. Identify all modified files
2. Check syntax: `python -m py_compile`
3. Run tests: `pytest`
4. Build: `python build_system/build.py`
5. Verify documentation sync (all 5 files updated)
6. Provide validation checklist with pass/fail for each item

**Example invocation:**
```
/validate-changes Check if all changes are complete and ready to commit
```

---

## Agent Selection Guide

| Task | Agent | Why |
|------|-------|-----|
| Adding new feature | `/add-feature` | Handles multiple file updates + build spec + docs |
| Build failure | `/fix-build` | Specialized for build system issues |
| Update docs | `/update-docs` | Maintains 5-file sync rule |
| Restructure code | `/refactor` | Ensures tests pass + docs updated |
| App crash/bug | `/debug-issue` | Traces root cause + documents solution |
| Ready to commit? | `/validate-changes` | Comprehensive pre-commit checks |

---

## Important: Pre-Agent Checklist

Before invoking any agent, ensure:
- [ ] You've read [`.github/copilot-instructions.md`](copilot-instructions.md) (project overview & critical rules)
- [ ] For code changes: Familiar with [documentation/FILE_DEPENDENCIES.md](documentation/FILE_DEPENDENCIES.md)
- [ ] For debugging: Have error message or steps to reproduce
- [ ] For docs: Know which files were modified since last documentation update

---

## Cross-References

- **Main instructions:** [`.github/copilot-instructions.md`](copilot-instructions.md)
- **File dependencies:** [`documentation/FILE_DEPENDENCIES.md`](documentation/FILE_DEPENDENCIES.md)
- **Architecture:** [`documentation/ARCHITECTURE.md`](documentation/ARCHITECTURE.md)
- **Development guide:** [`DEVELOPMENT.md`](../DEVELOPMENT.md)
- **Implementation log:** [`documentation/IMPLEMENTATION_LOG.md`](documentation/IMPLEMENTATION_LOG.md)
- **Development tasks skill:** [`.github/skills/development-tasks/SKILL.md`](skills/development-tasks/SKILL.md)

---

## Notes for Developers

These agent modes are designed to:
1. **Reduce friction** — Specialized agents know exactly what to check/update
2. **Prevent missed updates** — Agents check FILE_DEPENDENCIES.md before starting
3. **Maintain consistency** — Agents follow the 5-file documentation sync rule
4. **Save tokens** — Agents batch related changes and read files in parallel
5. **Improve quality** — Agents run tests and validation before completing

If an agent mode doesn't exist for your task, ask for it or use the default agent with explicit guidance from copilot-instructions.md and FILE_DEPENDENCIES.md.
