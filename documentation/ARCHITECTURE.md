# Karaoke App Architecture

## Purpose

Desktop karaoke/video utility built with PySide6.

Primary responsibilities:

- Video playback (VLC)
- Downloading media
- Audio/pitch processing
- FFmpeg-based export workflows
- Audio level monitoring
- Settings persistence
- Background task execution

---

## High-Level Architecture

```text
UI (PySide6)
    |
    +-- KaraokeApp (application coordinator)
    |
    +-- VideoFrame
    +-- AudioLevelMeter
    +-- SettingsDialog
    |
Workers
    |
    +-- AudioAnalyzerThread
    +-- ProcessThread
    |
External Tools
    |
    +-- VLC
    +-- FFmpeg
    +-- yt-dlp (or equivalent download backend)
```

---

## Main Classes

### KaraokeApp

Central application controller.

Owns:

- Main window
- Page navigation
- Settings
- VLC player lifecycle
- Background jobs
- Download workflow
- Export workflow
- Audio monitoring integration
- History/state management

Treat this class as the application's orchestrator.

---

### VideoFrame

Dedicated video display widget.

Responsibilities:

- Video container
- Drag-and-drop support
- VLC render target

---

### AudioLevelMeter

Custom widget used to display microphone/input levels.

Responsibilities:

- Render level bars
- Receive level updates
- Visual monitoring feedback

---

### AudioAnalyzerThread

Background thread.

Responsibilities:

- Capture/analyze audio
- Calculate levels
- Emit updates to UI

Should remain independent of UI logic.

---

### ProcessThread

Generic worker thread.

Responsibilities:

- Launch external commands
- Stream progress/output
- Prevent UI blocking

Expected users:

- FFmpeg
- Download tasks
- Long-running utilities

---

### SettingsDialog

Application configuration editor.

Responsibilities:

- User preferences
- Paths
- Runtime options
- Persistent configuration

---

## State Ownership

The following should be considered application state:

- Current media file
- Playback state
- Volume/mute state
- Current page
- Export options
- Download options
- User settings
- Audio monitoring state
- Background task state

When adding features, prefer storing state in one place and exposing it to pages.

---

## Playback Pipeline

```text
Media File
    |
    v
VLC Player
    |
    +-- VideoFrame
    |
    +-- Playback Controls
```
    
Responsibilities include:

- Play
- Pause
- Seek
- Volume
- Mute
- Fullscreen

---

## Download Pipeline

```text
URL
 |
 v
Validation
 |
 v
Download Command
 |
 v
ProcessThread
 |
 v
Local Media
```

---

## Export Pipeline

```text
Input Media
    |
    v
Processing Options
    |
    v
FFmpeg Command Builder
    |
    v
ProcessThread
    |
    v
Exported Output
```

---

## Audio Monitoring Pipeline

```text
Microphone/Input
      |
      v
AudioAnalyzerThread
      |
      v
Level Signal
      |
      v
AudioLevelMeter
```

---

## Recommended Region Layout

Keep the file organized using:

1. Imports / Constants
2. Custom Widgets
3. Worker Threads
4. Dialogs
5. KaraokeApp
   - Initialization
   - Settings
   - UI Construction
   - Navigation
   - Download Features
   - Processing Features
   - Playback Controls
   - Audio Monitoring
   - Background Tasks
   - Drag & Drop
   - Fullscreen
   - Shutdown
6. Splash Screen
7. Main Entry Point

---

## Rules for Future AI Refactoring

When modifying the application:

- Preserve VLC ownership and lifecycle.
- Preserve all signals/slots.
- Preserve settings compatibility.
- Preserve FFmpeg command behavior.
- Preserve download behavior.
- Avoid moving business logic into widgets.
- Keep worker threads UI-independent.
- Do not introduce circular imports.
- Maintain backward-compatible settings keys.

---

## Future Extraction Plan

If the application is eventually split:

```text
main.py

ui/
    main_window.py

widgets/
    video_frame.py
    audio_meter.py

workers/
    process_thread.py
    audio_analyzer.py

dialogs/
    settings_dialog.py

services/
    player_service.py
    download_service.py
    export_service.py

models/
    app_state.py
```

The goal is to keep KaraokeApp as an orchestrator rather than a feature implementation class.
