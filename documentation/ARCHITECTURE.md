# 🎤 Karaoke Studio Pro - Architecture

## Overview

Karaoke Studio Pro is a feature-rich cross-platform karaoke application built with Python, PySide6 (Qt6), and VLC. It provides video playback, YouTube downloads, real-time audio level monitoring, and playback controls for karaoke enthusiasts.

**Technology Stack:**
- **GUI Framework**: PySide6 (Qt6 bindings for Python)
- **Media Engine**: python-vlc (VLC bindings for playback)
- **Audio Capture**: sounddevice (real-time audio stream analysis)
- **Audio Processing**: numpy (RMS calculation, buffer management)
- **YouTube Downloads**: yt-dlp (media downloader)
- **Video Encoding**: FFmpeg (transcoding and processing)
- **Build System**: PyInstaller (creates standalone executables)
- **Threading**: QThread (background task execution)

---

## High-Level Architecture

```
┌─────────────────────────────────────────────┐
│      KaraokeApp (Main Window)               │
│      ├─ MenuBar                             │
│      ├─ VideoFrame (Video Display)          │
│      ├─ AudioLevelMeter (Audio Visualization)
│      ├─ Playback Controls (Play/Pause/Seek) │
│      ├─ Speed Control                       │
│      └─ Settings Button                     │
└─────────────────────────────────────────────┘
        │              │               │
        ▼              ▼               ▼
    ┌────────┐  ┌──────────┐  ┌─────────────────┐
    │Services│  │ Workers  │  │    Dialogs      │
    ├────────┤  ├──────────┤  ├─────────────────┤
    │Player  │  │Audio     │  │SettingsDialog   │
    │Service │  │Analyzer  │  │                 │
    │        │  │Thread    │  │ • FFmpeg path   │
    │Download│  │          │  │ • yt-dlp path   │
    │Service │  │Process   │  │ • Download dir  │
    │        │  │Thread    │  │ • Video output  │
    └────────┘  └──────────┘  └─────────────────┘
        │              │
        ▼              ▼
    ┌──────────────────────────┐
    │  External Tools/Engines  │
    ├──────────────────────────┤
    │ • VLC (Playback)         │
    │ • FFmpeg (Encoding)      │
    │ • yt-dlp (Downloads)     │
    │ • sounddevice (Audio)    │
    └──────────────────────────┘
```

---

## Module Structure

```
source_code/
├── __init__.py                    # Package marker
├── main.py                        # Entry point, main application window
│
├── dialogs/
│   ├── __init__.py
│   └── settings_dialog.py         # Application settings UI
│
├── models/
│   └── __init__.py                # Data models (placeholder)
│
├── services/
│   ├── __init__.py
│   ├── player_service.py          # VLC playback abstraction
│   └── download_service.py        # YouTube/stream download service
│
├── ui/
│   └── __init__.py                # UI utilities (placeholder)
│
├── widgets/
│   ├── __init__.py
│   ├── audio_meter.py             # Real-time audio level visualizer
│   └── video_frame.py             # Video display frame with D&D support
│
└── workers/
    ├── __init__.py
    ├── audio_analyzer.py          # Audio level capture thread
    └── process_thread.py          # Generic subprocess executor
```

---

## Core Components

### main.py (Entry Point)

**Responsibilities:**
- Initialize PySide6 application
- Create main window and UI components
- Manage VLC player lifecycle
- Coordinate service interactions
- Handle user input (buttons, sliders, keyboard)
- Manage audio analyzer thread
- Clean shutdown and resource cleanup

**Key Methods:**
- `__init__()` - Initialize UI and player
- `closeEvent()` - Cleanup audio thread and player on exit
- `on_play_clicked()` - Start playback
- `on_pause_clicked()` - Pause playback
- `on_seek_slider_changed()` - Handle timeline seeking
- `on_speed_up()` / `on_speed_down()` - Adjust playback speed (0.5x - 2.0x)
- `open_file()` - Load local video files
- `download_and_play()` - Download from YouTube and play

**Dependencies:**
- All services (PlayerService, DownloadService)
- All widgets (VideoFrame, AudioLevelMeter)
- All dialogs (SettingsDialog)
- All workers (AudioAnalyzerThread, ProcessThread)

---

### Services

#### PlayerService (player_service.py)

**Purpose:** VLC media playback abstraction

**Responsibilities:**
- Create and manage VLC instance
- Load media files
- Play, pause, stop operations
- Seek to timeline positions
- Adjust volume and playback speed
- Monitor playback state changes
- Emit state change signals to UI

**Public Interface:**
```python
player = PlayerService()
player.open(file_path)          # Load media
player.play()                   # Start playback
player.pause()                  # Pause playback
player.stop()                   # Stop playback
player.set_time(milliseconds)   # Seek to position
player.set_speed(factor)        # Set playback speed (0.5 to 2.0)
player.set_volume(0-100)        # Set volume level
```

---

#### DownloadService (download_service.py)

**Purpose:** Download media from YouTube and stream sources

**Responsibilities:**
- Download video/audio from YouTube URLs
- Save to configured directory
- Show download progress
- Handle download errors
- Integrate with ProcessThread for background execution

**Public Interface:**
```python
download = DownloadService(yt_dlp_path, output_dir)
download.download_video(url, callback)  # Download with progress
```

---

### Widgets

#### VideoFrame (widgets/video_frame.py)

**Purpose:** Custom Qt widget for video display

**Responsibilities:**
- Serve as VLC rendering target
- Support drag-and-drop file loading
- Pass dropped files to parent application

**Features:**
- Implements QFrame subclass
- Handles QDragEnterEvent for drag detection
- Handles QDropEvent to process dropped files

---

#### AudioLevelMeter (widgets/audio_meter.py)

**Purpose:** Real-time audio level visualization

**Responsibilities:**
- Receive audio level updates (dB values)
- Display gradient bar with color coding
- Smooth level transitions (exponential moving average)
- Show threshold markers (50%, 85%)

**Features:**
- Green gradient for levels <50%
- Orange gradient for 50-85%
- Red gradient for >85%
- Smooth animation using EMA: `new_level = 0.8 * old_level + 0.2 * input`

**Signal Connection:**
```python
audio_analyzer.level_updated.connect(audio_meter.set_level)
```

---

### Dialogs

#### SettingsDialog (dialogs/settings_dialog.py)

**Purpose:** Application configuration editor

**Responsibilities:**
- Display current settings
- Allow user to configure:
  - FFmpeg executable path
  - yt-dlp executable path
  - Download directory
  - Video output options
- Save settings to config/settings.json
- Load saved settings on startup

**Settings Storage:**
```json
{
  "ffmpeg_path": "path/to/ffmpeg.exe",
  "yt_dlp_path": "path/to/yt-dlp.exe",
  "download_dir": "path/to/downloads",
  "video_output": "auto"
}
```

---

### Workers

#### AudioAnalyzerThread (workers/audio_analyzer.py)

**Purpose:** Background thread for real-time audio level monitoring

**Responsibilities:**
- Capture audio from system input
- Calculate RMS (root mean square) levels
- Convert to decibel (dB) scale
- Emit level updates to UI at 10Hz frequency
- Manage thread lifecycle safely

**Key Features:**
- Uses sounddevice for audio capture
- Runs in separate QThread (non-blocking)
- Emits `level_updated(level)` signal
- Proper cleanup with timeout and forced termination
- Stop method waits up to 2000ms for graceful shutdown

**Signal:**
```python
level_updated = pyqtSignal(float)  # Emits dB values (-80 to 0)
```

---

#### ProcessThread (workers/process_thread.py)

**Purpose:** Generic background subprocess executor

**Responsibilities:**
- Execute external commands (FFmpeg, yt-dlp)
- Capture and parse process output
- Stream progress updates
- Handle process errors
- Prevent UI blocking during long operations

**Typical Usage:**
```python
# Download with progress
process = ProcessThread(
    command="yt-dlp.exe https://youtube.com/watch?v=...",
    working_dir="."
)
process.progress.connect(ui_update_callback)
process.start()
```

---

## Data Flow

### Playback Flow
```
User clicks "Open File"
    ↓
File dialog opens
    ↓
User selects video file
    ↓
PlayerService.open(file_path) called
    ↓
VideoFrame displays video
    ↓
User clicks Play
    ↓
PlayerService.play() executes
    ↓
AudioAnalyzerThread starts (if enabled)
    ↓
level_updated signals sent to AudioLevelMeter at 10Hz
    ↓
UI updates in real-time
```

### Download Flow
```
User enters YouTube URL
    ↓
DownloadService.download_video() called
    ↓
ProcessThread executes yt-dlp.exe
    ↓
progress signals sent to UI
    ↓
File saved to download directory
    ↓
PlayerService.open(downloaded_file)
    ↓
Playback starts
```

### Speed Control Flow
```
User clicks Speed Up (+)
    ↓
Speed increments by 0.05x (0.01x for keyboard arrow)
    ↓
PlayerService.set_speed(new_speed)
    ↓
VLC updates playback speed
    ↓
Audio pitch remains constant (VLC handles this)
```

---

## Threading Model

**Main Thread (GUI):**
- Runs PySide6 event loop
- Handles all user interactions
- Updates UI widgets

**Audio Analyzer Thread:**
- Independent QThread instance
- Captures audio continuously
- Emits level_updated signals
- Gracefully stops on closeEvent()

**Process Thread:**
- Independent QThread for subprocess execution
- Used for long-running operations (downloads, encoding)
- Prevents UI freezing

**Thread Safety:**
- Qt signals/slots ensure thread-safe communication
- Audio analyzer stops before app exits
- All threads join during cleanup

---

## Build System

**PyInstaller Configuration:**
- `build_system/KaraokeStudioPro.spec` defines the build
- All external tools bundled:
  - FFmpeg (ffmpeg.exe)
  - yt-dlp (yt-dlp.exe)
  - VLC libraries (libvlc.dll, libvlccore.dll)
  - VLC plugins directory
- Standalone executable requires zero external dependencies
- Output: `build_system/dist/KaraokeStudioPro/KaraokeStudioPro.exe`

**Build Command:**
```bash
python build_system/build.py
```

---

## State Management

**Global Application State:**
- Current media file path
- Playback state (playing/paused/stopped)
- Current playback time
- Playback speed (0.5x - 2.0x)
- Volume level (0-100)
- Audio analyzer state (enabled/disabled)
- User settings (persistent in config/settings.json)

**Best Practice:**
- State owned by main.py
- Services expose read-only access
- UI updates via signals when state changes
- Settings persist to disk automatically

---

## Error Handling

**File Not Found:**
- Check if file exists before opening
- Show error dialog to user

**VLC Errors:**
- Check if VLC libraries present in resources/
- Ensure libvlc.dll and plugins/ are bundled

**Audio Capture Errors:**
- Gracefully disable audio analyzer if sounddevice fails
- Log error but continue playback

**Download Errors:**
- Catch yt-dlp failures
- Show error message with retry option
- Log to debug console

---

## Recent Fixes (2026-06-17)

✅ **Fixed Import Issues**
- Converted relative to absolute imports
- Added sys.path manipulation for module discovery
- Added missing PySide6 imports (QPen, QEvent, etc.)

✅ **Fixed VLC State References**
- Changed `.State.Playing` to `vlc.State.Playing` (3 locations)

✅ **Fixed Thread Cleanup**
- Enhanced audio_analyzer.stop() with timeout + forced termination
- Properly cleanup resources on closeEvent()
- Prevent app hang on close after multiple songs

✅ **Fixed Speed Control**
- Buttons now correctly increment by 0.05x
- Arrow keys now correctly increment by 0.01x
- All controls properly bounded (0.5x - 2.0x)

✅ **Improved Build System**
- All external tools now bundled
- Updated requirements-build.txt
- Created BUILD_GUIDE.md for team distribution

---

## Future Enhancements

- [ ] Pitch shifting without speed change
- [ ] Equalizer UI
- [ ] Recording/export functionality
- [ ] Playlist support
- [ ] Advanced audio filtering
- [ ] Custom key bindings
- [ ] Theme support (light/dark)

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
