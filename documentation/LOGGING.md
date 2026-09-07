# Logging System - Karaoke Studio Pro v3

## Overview

The application includes a comprehensive logging system that tracks runtime events, errors, and diagnostics. This is essential for troubleshooting issues when users report problems.

**Log Location:** `config/` folder in the application directory

---

## Log Files

### 1. `app_debug.log` (All Events)
- **Purpose:** Comprehensive debug log of all application events
- **Content:** Debug messages, info events, warnings, errors, and exceptions
- **Audience:** Developers for troubleshooting
- **Max Size:** 5 MB per file (auto-rotates to `app_debug.log.1`, `.2`, etc.)
- **Retention:** Last 5 rotated files kept (~25 MB total)

**When to collect:** When debugging app behavior, features not working as expected, or performance issues

### 2. `app_errors.log` (Errors Only)
- **Purpose:** Critical errors and exceptions only
- **Content:** Only ERROR and EXCEPTION level messages
- **Audience:** Quick reference for what went wrong
- **Max Size:** 5 MB per file (auto-rotates)
- **Retention:** Last 5 rotated files kept (~25 MB total)

**When to collect:** When app crashes or critical features fail

---

## Log Levels

The logger uses standard Python logging levels:

| Level | Usage | Example |
|-------|-------|---------|
| DEBUG | Development/troubleshooting details | `[app] loaded 156 audio files` |
| INFO | User-relevant events | `[app] Karaoke Studio Pro initialized` |
| WARNING | Unexpected but non-critical | `⚠️ FFmpeg not found, falling back to system PATH` |
| ERROR | Something went wrong | `❌ Failed to open video file: File not found` |
| EXCEPTION | Crash with full traceback | `❌ [load_video] EXCEPTION: TypeError...` |

---

## Log Format

All log entries follow this format:

```
2026-09-01 14:32:45 | DEBUG    | [app] loading karaoke track: path/to/video.mp4
2026-09-01 14:32:47 | INFO     | [playback] audio playback started at 00:12
2026-09-01 14:32:50 | WARNING  | ⚠️ [pitch_service] pitch detection took 2.3 seconds
2026-09-01 14:33:15 | ERROR    | ❌ [download_service] failed to fetch URL: Connection timeout
2026-09-01 14:33:16 | ERROR    | Traceback (most recent call last):...
```

**Format:** `TIMESTAMP | LEVEL | MESSAGE`

---

## How Users Can Find Logs

### For Source Runs
```powershell
# Log location:
# - Windows: D:\Your\Project\Path\config\
# - macOS/Linux: /Your/Project/Path/config/

# Open directly:
# Windows: explorer config\
# macOS: open config/
# Linux: xdg-open config/
```

### For Standalone Executable (.exe)
```powershell
# Log location:
# Windows: C:\Users\[YourUsername]\AppData\Local\KaraokeStudioPro\config\
# (Exact path depends on installation location)

# To find it:
# 1. Open File Explorer
# 2. Paste this in address bar:
#    %APPDATA%\..\..\AppData\Local\KaraokeStudioPro\config\
# 3. Look for app_debug.log and app_errors.log
```

---

## How to Request Logs from Users

When a user reports an issue, ask them to:

1. **Locate logs folder:**
   - For .exe: Check `AppData/Local/KaraokeStudioPro/config/` (or installation directory)
   - For source: Check `config/` in project root

2. **Collect both files:**
   - `app_debug.log` (full debug log)
   - `app_errors.log` (if it exists - errors only)
   - `app_debug.log.1`, `.2`, etc. (if error happened in previous session)

3. **Send files to developer:**
   - Attach to bug report or support ticket
   - Or paste relevant sections from error log

**Example request to user:**
```
Please send me the following files from your Karaoke Studio Pro installation:
- config/app_debug.log (the main log file)
- config/app_errors.log (if it exists)

These logs contain diagnostic information that will help me diagnose your issue.

Location: Look for a "config" folder where you installed or ran the app.
If using the executable (.exe), check:
  C:\Users\[YourName]\AppData\Local\KaraokeStudioPro\config\
```

---

## Log Rotation Behavior

To prevent logs from growing indefinitely:

- **File size limit:** 5 MB per log file
- **When limit reached:** File is automatically rotated
- **Archive naming:** `app_debug.log` → `app_debug.log.1` → `app_debug.log.2` (etc.)
- **Retention:** Last 5 backup files kept
- **Total storage:** ~25 MB for debug logs + ~25 MB for error logs = ~50 MB maximum

**Example rotation sequence:**
```
Start:   app_debug.log (0 KB)

After 5 MB:
         app_debug.log.1 (5 MB) ← rotated
         app_debug.log (new file, 0 KB) ← current log

After 10 MB total:
         app_debug.log.2 (5 MB)
         app_debug.log.1 (5 MB)
         app_debug.log (new file, ~0 KB)

After 6 backups (30 MB total):
         app_debug.log.5 (5 MB) ← oldest, kept
         app_debug.log.4 (5 MB)
         app_debug.log.3 (5 MB)
         app_debug.log.2 (5 MB)
         app_debug.log.1 (5 MB)
         app_debug.log (new file, ~0 KB)
         (oldest files deleted when limit reached)
```

---

## Session Tracking

Each time the app starts, logs record:
```
2026-09-01 14:30:00 | INFO  | ======================================================================
2026-09-01 14:30:00 | INFO  | APPLICATION STARTED
2026-09-01 14:30:00 | INFO  | ======================================================================
```

And when it closes:
```
2026-09-01 15:45:30 | INFO  | ======================================================================
2026-09-01 15:45:30 | INFO  | APPLICATION SHUTDOWN
2026-09-01 15:45:30 | INFO  | ======================================================================
```

This makes it easy to find logs for a specific session.

---

## Common Log Search Patterns

### Finding errors
```powershell
# Windows PowerShell: Search for ERROR in debug log
Select-String "ERROR|EXCEPTION" config\app_debug.log | Select-Object -First 20

# Then check app_errors.log for critical issues
```

### Finding recent issues
```powershell
# Find logs from last session (look for APPLICATION STARTED marker)
Select-String "APPLICATION STARTED" config\app_debug.log | Select-Object -Last 5
```

### Checking specific features
```powershell
# Search for video loading
Select-String "load_video" config\app_debug.log | Select-Object -Last 10

# Search for audio processing
Select-String "audio_studio|pitch_service|audio_separator" config\app_debug.log
```

---

## Integration with Application

The logging service is automatically initialized when the app starts. Key components that log:

- **Main application:** Startup, shutdown, initialization
- **Playback controller:** Video play/pause/stop events
- **Download service:** YouTube URL processing, download progress
- **Audio service:** Audio analysis, pitch detection, processing
- **Processing controller:** FFmpeg commands, task status, completion
- **File loading service:** File open/close, cleanup
- **Error handlers:** All exceptions with full traceback

---

## Troubleshooting: No Logs Generated

If users report no logs appear:

1. **Check permissions:** User must have write access to config/ folder
2. **Check disk space:** Ensure 50+ MB free space for log rotation
3. **Check log level:** Logger initializes to DEBUG level by default
4. **Verify config folder exists:** `config/` folder should be created automatically

If logs still don't appear, this indicates an issue with file permissions or disk access.

---

## For Developers

### Adding Logging to New Code

```python
# In a controller or service:
app.log_debug("[feature_name] something happened")
app.log_info("[feature_name] user action completed")
app.log_warning("[feature_name] unexpected condition")
app.log_error("[feature_name] operation failed")

# For exceptions:
try:
    # do something
except Exception as e:
    app.log_exception("feature_name", e)
```

### Checking Logs During Development

```powershell
# Watch logs in real-time (Windows PowerShell)
Get-Content config\app_debug.log -Tail 20 -Wait

# Or open in editor and refresh to see updates
```

---

## Log File Locations Summary

| Environment | Location | Notes |
|---|---|---|
| **Source Run (Windows)** | `project_root\config\` | Relative to main.py location |
| **Source Run (macOS/Linux)** | `project_root/config/` | Relative to main.py location |
| **Standalone .exe** | `InstallDir\config\` or `%APPDATA%\KaraokeStudioPro\config\` | Depends on installation |
| **Portable .exe** | `exe_directory\config\` | Same folder as .exe |

---

## References

- **Main Application:** `source_code/main.py` — Logging initialization
- **Logging Service:** `source_code/services/logging_service.py` — Implementation
- **Configuration:** `build_system/KaraokeStudioPro.spec` — Logging in .exe builds
