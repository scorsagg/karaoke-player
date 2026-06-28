# 🎤 Karaoke Studio Pro v3 - Architecture

## Overview

Karaoke Studio Pro v3 is a feature-rich cross-platform karaoke application built with Python, PySide6 (Qt6), and VLC. It provides video playback, YouTube downloads, real-time audio level monitoring with configurable room calibration, and playback controls for karaoke enthusiasts.

**Technology Stack:**
- **GUI Framework**: PySide6 (Qt6 bindings for Python)
- **Media Engine**: python-vlc (VLC bindings for playback)
- **Audio Capture**: sounddevice (real-time audio stream analysis)
- **Audio Processing**: numpy (RMS calculation, SPL conversion, buffer management)
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

### Page Layout & Scroll Architecture (updated 2026-06-21)

Pages 3 and 4 in the QStackedWidget are wrapped in QScrollArea:

```
QStackedWidget
├── [0] download_page (QWidget)
├── [1] pitch_page (QWidget)
├── [2] widen_page (QWidget)
├── [3] QScrollArea → audio_tools_page (QWidget)   ← scroll area wrapper
└── [4] QScrollArea → video_tools_page (QWidget)   ← scroll area wrapper
```

Video frame height is controlled per-page in `handle_navigation_change()`:
- Pages 0/1: min=420px, no max — large video area
- Page 2: min=80px, max=350px
- Page 3: min=80px, max=100px (audio-only) / 220px (video)
- Page 4: min=80px, max=220px

**Fullscreen:** `toggle_video_fullscreen()` removes the height cap on enter (sets max=unlimited),
then calls `handle_navigation_change(current_idx)` on exit to restore page-correct constraints.

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
- Refresh sidebar status text on load start/success/failure events
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
- Bootstrap Windows VLC runtime discovery before importing `python-vlc`
    (prepends VLC root to PATH, sets `VLC_PLUGIN_PATH`, and uses `os.add_dll_directory` when available)
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

#### AudioService (services/audio_service.py)

**Purpose:** Coordinate audio analyzer thread state management and meter display modes

**Responsibilities:**
- Manage audio analyzer pause/resume state
- Reconnect level-update callbacks when analyzer thread is recreated
- Set audio meter display modes (dB vs SPL)
- Provide clean shutdown for audio subsystem
- Prevent signal conflicts during settings operations

**Public Interface:**
```python
audio_service = AudioService(analyzer, meter, level_update_handler=on_audio_level_updated)
audio_service.pause_analyzer()           # Pause audio capture
audio_service.resume_analyzer()          # Resume audio capture
audio_service.set_display_mode(mode)     # Change meter display
audio_service.cleanup()                  # Cleanup on shutdown
```

**Key Methods:**
- `pause_analyzer()` - Pauses analysis, returns previous state
- `resume_analyzer()` - Resumes analysis if previously playing and reconnects callbacks on new thread
- `set_display_mode(mode)` - Sets meter display to 'dB Output (dBFS)' or 'SPL Estimate (Room)'
- `cleanup()` - Safely stops analyzer thread on app exit

---

#### FileLoadingService (services/file_loading_service.py) - FINAL FIX ✅

**Purpose:** Thread-safe file loading with intelligent resource cleanup (no VLC deadlock)

**Problem Solved:** App hung when loading second file - VLC's `stop()` hangs with active decoder threads. Solution: pause + release media reference, let VLC auto-cleanup

**Responsibilities:**
- Check if file is currently active (playing or paused)
- If YES: Pause player, wait 1.0s, stop audio analyzer, release media reference (NO stop() call)
- If NO: Just pause audio analyzer
- Prevent overlapping file load operations
- Safely coordinate audio analyzer with file transitions
- Resume audio analyzer after successful loads

**5 File Loading Entry Points (all use this service internally via `load_video()`):**
1. Download page "Open File..." button → `load_video()`
2. Widen page "Open Widen File..." button → `browse_widen_video()` → `load_video()`
3. History list double-click → `load_video(file_path)`
4. Download & Queue button → `_on_download_finished()` → `load_video(full_p)`
5. Convert to 16:9 button → `handle_task_completion()` → `load_video(out_path)`

**Public Interface:**
```python
file_loader = FileLoadingService(audio_service, player_service)
was_playing = file_loader.prepare_for_loading()  # Prepare (pause audio, release media)
# ... perform file load operation ...
file_loader.finish_loading(resume_audio=was_playing)  # Cleanup (resume audio)
```

**Key Methods:**
- `prepare_for_loading()` - Smart cleanup: check if active → pause → stop audio → release media. Returns previous play state
- `finish_loading(resume_audio)` - Resumes audio analyzer if specified
- `is_currently_loading()` - Check if load is in progress

**How It Works (Final Solution):**
```
if is_active():
    if is_playing():
        pause() + wait 1.0s        ← Stop decoder threads
    stop_audio_analyzer()          ← Close sounddevice InputStream
    release_media_reference()      ← NO STOP() CALL - causes hang!
    wait 0.5s
else:
    just pause_audio_analyzer()

→ New file loads
→ VLC auto-cleans old media
→ No hang! ✅
```

**Why This Avoids Deadlock:**
- VLC decoder threads stay alive even after pause
- Calling `player.stop()` tries to wait for threads → DEADLOCK
- Solution: Don't wait for stop, just release reference
- VLC auto-cleans when new media is set

---

### Audio Processing (Features 6 & 7) ✅ NEW

**Audio Trimming (Feature 6) & Format Conversion (Feature 7)**

**Purpose:** Advanced audio/video processing via FFmpeg with intelligent command building

**Responsibilities:**
- Trim audio with flexible options (first X, last X, range, combinations)
- Convert between audio/video formats intelligently
- Calculate trim points from duration data
- Build format-specific FFmpeg commands
- Execute via ProcessThread with progress updates
- Auto-reload processed files

**UI Location:** Extra Tools → Audio Tools tab (two sub-sections)

**Feature 6: Audio Trimming Methods:**
```python
trim_audio() - Orchestrates trimming based on checkboxes:
├─ trim_first: Skip first N seconds
├─ trim_last: Skip last N seconds  
├─ trim_range: Keep seconds A to B (overrides other trims)
└─ Supports all combinations (first+last, first+range, last+range, all three)
```

**Feature 7: Format Conversion Methods:**
```python
convert_audio_format() - Converts based on dropdown selections:
├─ Source format: Auto-detect or specific (MP3, WAV, M4A, AAC, DAT, MP4, MKV, AVI, WebM)
├─ Target format: MP3, WAV, M4A, AAC, MP4, MKV
└─ Quality selector: High (320k), Medium (192k), Low (128k)

build_format_conversion_cmd() - Builds FFmpeg command:
├─ Audio→Audio: Extract audio only, apply encoder
├─ Video→Audio: Strip video, extract audio
├─ Audio→Video: Wrap audio in container
└─ Video→Video: Re-encode as needed
```

**Key Methods:**
- `trim_audio()` - Check trim options, calculate times, execute
- `convert_audio_format()` - Get format selections, build command, execute
- `build_format_conversion_cmd()` - Intelligent command builder for any format pair

**FFmpeg Command Examples:**
```bash
# Trimming (fast, no re-encode)
ffmpeg -ss {start} -to {end} -i input -acodec copy output

# Format conversions
ffmpeg -i input.mp3 -acodec pcm_s16le -ar 44100 output.wav
ffmpeg -i input.wav -acodec libmp3lame -b:a 192k output.mp3
ffmpeg -i input.dat -vn -acodec libmp3lame -b:a 192k output.mp3
ffmpeg -i input.mp4 -vn -acodec aac -b:a 192k output.m4a
```

**Data Flow:**
```
User selects trim/convert options
    ↓
Validates at least one option selected
    ↓
Shows loading splash screen
    ↓
Calculates trim times / builds format command
    ↓
Executes via ProcessThread
    ↓
Progress updates stream to splash
    ↓
On completion: handle_task_completion()
    ↓
Auto-loads result into player
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
- On Windows, prefers WASAPI loopback capture from default output device
- Tries compatible InputStream configs (2ch/1ch, 44.1k/48k) before failing
- Scans WASAPI output-capable devices and host defaults to avoid machine-specific routing issues
- Gracefully stops on closeEvent()
- Uses `WasapiSettings()` without `loopback` kwarg for `sounddevice` 0.5.x compatibility
- Uses `soundcard` loopback microphone as primary Windows playback source when available,
  with `sounddevice` as fallback

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
