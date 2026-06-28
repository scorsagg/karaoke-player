# Karaoke Studio Pro - File Dependencies & Update Checklist

**IMPORTANT:** Before making ANY changes to the codebase, consult this file to identify all related files that need updating together.

## When Making Changes to These Areas, Update These Files:

### 1. VERSION UPDATES (Currently: v3)
**Files to update:**
- `build_system/build.py` → `VERSION = "3"`
- `build_system/KaraokeStudioPro.spec` → Comment at top mentions v3
- `README.md` → Title and version references
- `build_system/BUILD_GUIDE.md` → Title includes v3
- `documentation/INSTALLATION.txt` → Title and file name references
- `documentation/FOLDER_ORGANIZATION_SUMMARY.txt` → Title includes v3
- `documentation/ARCHITECTURE.md` → Title includes v3

### 2. EXE NAME CHANGES
**Current:** `KaraokeStudioProV3.exe`
**Files to update:**
- `build_system/KaraokeStudioPro.spec` → `name='KaraokeStudioProV3'` in EXE section
- `documentation/INSTALLATION.txt` → All executable references

### 3. BUILD SPEC HIDDEN IMPORTS (Add new modules here when creating new Python files)
**File:** `build_system/KaraokeStudioPro.spec` → `hiddenimports=[]` list
**Update when:**
- Creating new service: `source_code.services.new_service`
- Creating new UI component: `source_code.ui.new_component`
- Creating new widget: `source_code.widgets.new_widget`
- Creating new dialog: `source_code.dialogs.new_dialog`
- Creating new worker: `source_code.workers.new_worker`

### 4. UI REFACTORING (Modularized Components)
**Current structure:** `source_code/ui/` folder with:
- main_layout.py, sidebar.py, playback_bar.py, download_page.py, pitch_page.py, extra_page.py, video_tools_page.py

**Files to update when modifying UI:**
- `build_system/KaraokeStudioPro.spec` → hiddenimports for new UI modules
- `source_code/main.py` → imports from ui package, setup_ui() method
- `documentation/FOLDER_ORGANIZATION_SUMMARY.txt` → UI folder structure
- `documentation/ARCHITECTURE.md` → UI architecture section

**Page index map (CRITICAL — do not change):**
- 0: Downloader | 1: Pitch & Speed | 2: Widen Video | 3: Audio Tools | 4: Video Tools

**Scroll Areas (added 2026-06-21):**
- Pages 3 (Audio Tools) and 4 (Video Tools) are wrapped in `QScrollArea` in `main_layout.py`
- This means `stack.widget(3)` is a `QScrollArea`, not the page widget directly
- The actual page widget is accessed via `scroll_area.widget()`
- `QScrollArea` and `Qt` must be imported in main_layout.py

**Video Frame Height Rules (handle_navigation_change in main.py):**
- idx 0/1 (Downloader, Pitch & Speed): min=420, max=unlimited
- idx 2 (Widen Video): min=80, max=350
- idx 3 (Audio Tools): min=80, max=100 (audio-only) or max=220 (video)
- idx 4 (Video Tools): min=80, max=220

**Navigation Signal (IMPORTANT):**
- Use `nav_list.itemClicked` NOT `nav_list.currentRowChanged`
- `currentRowChanged` fires on programmatic changes and causes spurious navigation
- After `nav_list.setCurrentRow(0)` in `__init__`, call `handle_navigation_change(0)` explicitly

### 5. AUDIO FEATURES (SPL, dBFS, Auto-Reduce, AudioService)
**Related files:**
- `source_code/services/audio_service.py` → AudioService implementation
- `source_code/widgets/audio_meter.py` → Measurement mode logic, SPL calculation, **HAS BOTH set_level() and update_level() methods (aliases)**
- `source_code/main.py` → Audio level handler, settings integration
- `source_code/dialogs/settings_dialog.py` → Audio settings fields
- `config/settings.json` → measurement_mode, auto_reduce_threshold fields
- `build_system/KaraokeStudioPro.spec` → audio_service hidden import
- `documentation/INSTALLATION.txt` → Audio calibration section, features
- `documentation/ARCHITECTURE.md` → Audio system section
- `documentation/FOLDER_ORGANIZATION_SUMMARY.txt` → AudioService in services/

**CRITICAL SIGNAL CONNECTIONS:**
- When audio analyzer thread is recreated (pause/resume), `AudioService` reconnects
  `new_thread.level_updated` to the main handler (`on_audio_level_updated`) when provided,
  with meter direct-connect as fallback.
- AudioLevelMeter widget MUST have BOTH methods:
  - `set_level(db_value)` - Called directly from main.py's on_audio_level_updated()
  - `update_level(db_value)` - Fallback path used by AudioService if no main handler is provided
- Audio analyzer stream startup in `source_code/workers/audio_analyzer.py` now uses
  channel/sample-rate fallbacks (2ch/1ch, 44.1k/48k) so meters work on mono/default devices too.
- On Windows, analyzer now tries WASAPI loopback (default output device) first so
  the meter reflects actual playback output, then falls back to default input capture.
- WASAPI loopback selection is adaptive: it scans WASAPI host defaults and output-capable
  devices, then tries candidates with device-aware sample-rate/channel fallbacks.
- `sounddevice` 0.5.x compatibility: `WasapiSettings()` must be used without a `loopback` kwarg.
- Windows capture backend order in `audio_analyzer.py`:
  1. `soundcard` speaker loopback microphone (hardware-agnostic playback capture)
  2. `sounddevice` adaptive WASAPI/default-input fallback configs
- Auto-reduce threshold is user-adjustable in dB SPL; `90` is the default, not a hard minimum.
- Manual volume slider changes temporarily suspend auto-reduce for a short override window
  so the user can raise/lower volume without the reducer immediately fighting the change.
- Sidebar status text should be refreshed in `load_video()` on load start/success/failure
  to avoid stale auto-reduce messages persisting across file changes.

### 6. SETTINGS/CONFIG CHANGES
**File:** `config/settings.json`
**When adding new settings:**
- Add field to settings.json default structure
- Add field to `source_code/dialogs/settings_dialog.py` schema
- Add field handling in settings_dialog.py `build_pages()` method
- Add field handling in settings_dialog.py `accept_changes()` method
- Update documentation if user-facing

### 7. NEW SERVICE/WORKER CREATION
**When creating:** `source_code/services/new_service.py` or `source_code/workers/new_worker.py`
**Update:**
- `build_system/KaraokeStudioPro.spec` → Add to hiddenimports
- `source_code/main.py` → Import and instantiate
- `source_code/[services|workers]/__init__.py` → Export if needed
- `documentation/ARCHITECTURE.md` → Document new component
- `documentation/FOLDER_ORGANIZATION_SUMMARY.txt` → Add to folder listing

### 8. THREAD-SAFE FILE LOADING (File Loading Operations - FINAL FIX ✅)
**Current Service:** `source_code/services/file_loading_service.py`
**Related files:**
- `source_code/services/file_loading_service.py` → FileLoadingService implementation
- `source_code/services/audio_service.py` → Coordinates with audio analyzer state
- `source_code/services/player_service.py` → Player state checks and pause
- `source_code/main.py` → Initializes FileLoadingService, uses prepare_for_loading()/finish_loading()
- `build_system/KaraokeStudioPro.spec` → file_loading_service in hiddenimports

**Final Solution (After Debugging):**
The key fix: **Never call player.stop() when decoder is active** instead:
1. Call `player.pause()` to stop decoder threads
2. Wait 1.0s for pause to take effect
3. Call `audio_analyzer.stop()` to close sounddevice InputStream
4. Release media reference: `player._media = None` (DON'T call stop()!)
5. Wait 0.5s for cleanup
6. Load new file - VLC auto-cleans old media

**Why This Works:**
- VLC decoder threads stay active even after pause
- Calling `player.stop()` hangs waiting for threads to exit
- Solution: pause + release media reference + let VLC auto-cleanup when new media loads

**Entry Points (all use load_video() internally):**
1. Download page "Open File..." button
2. Widen page "Open Widen File..." button
3. History list double-click
4. Download & Queue button completion
5. Convert to 16:9 button completion

### 9. AUDIO PROCESSING FEATURES (Features 6 & 7) ✅ COMPLETE
**Status:** Fully Implemented & Enhanced in v3

**Related files:**
- `source_code/ui/extra_page.py` → UI with tabbed interface + TimePickerWidget class
- `source_code/main.py` → trim_audio(), convert_audio_format(), build_format_conversion_cmd() methods, audio overlay, history loading
- `documentation/ARCHITECTURE.md` → Audio Processing section
- `documentation/IMPLEMENTATION_LOG.md` → Features 6 & 7 + UX improvements entry

**Feature 6: Audio Trimming ✅ COMPLETE**
- Trim first X seconds, last X seconds, keep range, or combinations
- Supports all audio formats (MP3, WAV, AAC, M4A)
- FFmpeg command: `-ss {start} -to {end} -acodec copy`
- **UI Component:** `TimePickerWidget` class with three spinboxes
  - Separate Hour/Minute/Second controls (0-59 range each)
  - Total time calculated as: hours * 3600 + minutes * 60 + seconds
  - Display format: HH:MM:SS
  - Each unit increments independently
- **UI Location:** Extra Tools → Audio Tools tab → Trimming section
- **Checkbox Controls:**
  - ☑ Trim First X seconds (with H/M/S picker)
  - ☑ Trim Last X seconds (with H/M/S picker)
  - ☑ Keep Range (from A to B) with Start and End H/M/S pickers
  - Output format selector (MP3, WAV, AAC, M4A)

**Feature 7: Format Conversion ✅ COMPLETE**
- Convert between audio/video formats: MP3, WAV, M4A, AAC, DAT, MP4, MKV, AVI, WebM
- Quality selector for lossy formats (High 320kbps, Medium 192kbps, Low 128kbps)
- Intelligent FFmpeg command builder handles all format combinations
- **UI Location:** Extra Tools → Audio Tools tab → Converter section
- **Controls:**
  - Source format dropdown (Auto-detect + specific formats)
  - Target format dropdown
  - Quality selector (for lossy formats)
  - Convert & Export button

**Quality Mappings (for MP3 and other lossy formats):**
- High (320kbps) → bitrate=320k
- Medium (192kbps) → bitrate=192k
- Low (128kbps) → bitrate=128k

**Format Conversion Examples:**
- MP3 → WAV: `ffmpeg -i input.mp3 -acodec pcm_s16le -ar 44100 output.wav`
- WAV → MP3: `ffmpeg -i input.wav -acodec libmp3lame -b:a 192k output.mp3`
- DAT → MP3: `ffmpeg -i input.dat -vn -acodec libmp3lame -b:a 192k output.mp3`
- MP4 → M4A: `ffmpeg -i input.mp4 -vn -acodec aac -b:a 192k output.m4a`

**UX Improvements ✅ COMPLETE**
- **Audio Visualization Overlay:** Green glowing widget shows "🎵 Audio File Loaded" for audio-only files
- **Navigation Fix:** After trim/convert/extract, page stays on Audio Tools (auto-navigates back)
- **TimePickerWidget:** Custom QWidget with separate H/M/S spinners for better UX
  - Methods: `get_total_seconds()`, `set_total_seconds(seconds)`, `get_display_text()`
  - Displays time clearly in HH:MM:SS format
- **History Detection:** Audio files loaded from history now show visualization automatically

**Auto-Reload:** After export, file automatically loads into player (via handle_task_completion)

### 10. AUDIO EXTRACTION UI STATE MANAGEMENT ✅ COMPLETE
**Status:** Fixed - Extraction UI now properly updates for all loading scenarios

**Related files:**
- `source_code/main.py` → 
  - `update_extraction_ui(is_video)` helper method (new)
  - `load_audio_tools_file()` updated to call helper
  - `load_history_item()` updated to call helper
  - `handle_navigation_change()` updated to call helper
  - `show_audio_visualization()` enhanced with retry logic
  - `finish_loading()` delay increased to 150ms

**What Changed:**
- **New helper method `update_extraction_ui(is_video)`** centralizes all extraction UI logic
  - Shows extraction controls (checkbox, button, format selector) when is_video=True
  - Shows "Load a video to extract audio" message when is_video=False
  - Called from three locations to ensure consistency

- **Updated `load_audio_tools_file()`**
  - Detects file type (video vs audio) from extension
  - Calls `update_extraction_ui(is_video)` to update controls
  - Updates audio_file_status label with detected type

- **Updated `load_history_item()`**
  - Detects file type using extension sets (audio_exts and video_exts)
  - If on Audio Tools page, updates audio_tools_file_path and calls `update_extraction_ui()`
  - Ensures extraction UI is correct for files loaded from history

- **Updated `handle_navigation_change()`**
  - When navigating to Audio Tools page, detects current file type
  - Updates audio_file_status label if showing "No file loaded"
  - Calls `update_extraction_ui()` to show appropriate controls
  - Ensures UI is consistent when navigating after file is already loaded elsewhere

- **Enhanced `show_audio_visualization()`**
  - Retries with 100ms delay if frame dimensions are 0
  - Prevents early return before frame layout completes
  - Better visibility with 250 alpha (instead of 240)

**File Type Detection Logic:**
```python
video_exts = {'.mp4', '.avi', '.mkv', '.mov', '.webm'}
audio_exts = {'.mp3', '.wav', '.aac', '.m4a', '.flac', '.ogg', '.opus', '.wma'}
is_video = os.path.splitext(file_path)[1].lower() in video_exts
```

**Three File Loading Scenarios Now Handled:**
1. User opens file via "Load File" button → calls `load_audio_tools_file()`
2. User double-clicks file in history → calls `load_history_item()`
3. User loads file on another page, then navigates to Audio Tools → `handle_navigation_change()` detects and updates

### 12. WIDEN VIDEO FIXES (2026-06-23) ✅ COMPLETE
**Files changed:** `source_code/main.py` only

**What changed:**
- `widen_active_video_canvas()` → restored original working FFmpeg filter + added `-preset ultrafast`
  - Filter: `crop=in_w:in_h*0.3:0:in_h*0.2,scale=1920*1.1:1080*1.1:force_original_aspect_ratio=increase,crop=1920:1080`
  - Speed flag: `-preset ultrafast` (without `-c:v`, `-threads 0`, or `-pix_fmt` to avoid VLC h264 warnings)
- `toggle_video_fullscreen()` → removes `video_frame` height cap on enter, restores on exit
- `handle_task_completion()` → widen_task post-completion now updates status label, path, and navigates to page 2

**Known issue (resolved):** `-threads 0` caused `[h264] get_buffer() failed` VLC decoder warnings
  because multi-threaded encoding produces complex frame dependencies that VLC's decoder trips over.
  Solution: omit `-threads 0`, keep only `-preset ultrafast`.

### 11. AUDIO LOUDNESS NORMALIZATION (Feature 8) ✅ COMPLETE
**Status:** Fully Implemented - Normalizes audio to consistent LUFS level

**Related files:**
- `source_code/ui/extra_page.py` → Normalization tab with controls
- `source_code/main.py` → `normalize_audio()` method with FFmpeg loudnorm filter
- `documentation/IMPLEMENTATION_LOG.md` → Feature 8 implementation entry

**Feature 8: Audio Loudness Normalization ✅ COMPLETE**
- Normalizes audio files to consistent loudness levels using FFmpeg `loudnorm` filter
- Three preset LUFS targets for different use cases
- **UI Location:** Extra Tools → Audio Tools tab → Normalization section (Tab 4)
- **Controls:**
  - ☑ Normalize Loudness (checkbox, checked by default)
  - Target LUFS dropdown with three presets:
    - -14 LUFS (Streaming) - Spotify, Apple Music, YouTube
    - -16 LUFS (Broadcast) - TV, Radio standard
    - -18 LUFS (Loud) - Maximum output
  - "Normalize & Export" button (green, 35px height)

**FFmpeg Implementation:**
- Uses `loudnorm` audio filter with configurable LUFS targets
- Filter parameters: `loudnorm=I={LUFS_VALUE}:LRA=11:tp=-1.5`
  - I (Integrated LUFS): Target loudness level (-14, -16, or -18)
  - LRA (Loudness Range): 11 LUFS (standard range)
  - tp (True Peak): -1.5 dB (prevents clipping)
- Output format: WAV with 44100 Hz sample rate (CD quality)
- Output file naming: `{original_name}_normalized.wav`

**LUFS Standards:**
- **-14 LUFS**: Streaming platforms (loudest)
  - Spotify, Apple Music, YouTube Music use loudness normalization around this level
  - Best for: Modern streaming delivery, consistent across platforms
- **-16 LUFS**: Broadcast standard (medium)
  - Industry standard for broadcast TV and radio
  - Best for: Professional audio that needs to match broadcast specifications
- **-18 LUFS**: Loud output (quietest target)
  - Less common, use when maximum perceived loudness is needed
  - Caution: May risk clipping or audio artifacts

**Workflow:**
1. User loads audio or video file (any format)
2. Selects target LUFS from dropdown (default: -14 LUFS)
3. Ensures "Normalize Loudness" checkbox is checked
4. Clicks "Normalize & Export" button
5. FFmpeg analyzes audio and applies normalization filter
6. Output saved as `{filename}_normalized.wav` in download directory
7. File automatically loads into player (via handle_task_completion)

**Technical Details:**
- Two-pass processing: FFmpeg handles analysis and application in single command
- Loudnorm filter automatically detects input loudness and applies correct gain
- Output always PCM WAV format for maximum compatibility
- Sample rate standardized to 44100 Hz (CD quality)
- Processing preserves original duration and audio quality

### 13. HELPER FUNCTIONS FOR FUTURE FEATURES (Features 5, 20, 12, 9) ✅ IMPLEMENTED
**Status:** Helper functions created, ready for integration with full UI

**Related files:**
- `source_code/services/audio_service.py` → Audio processing helpers (Features 5, 20, 12)
- `source_code/services/player_service.py` → Video processing helpers (Feature 9)
- `source_code/main.py` → Can call these helper methods when implementing full features

**Feature 5 - Volume Adjustment (Helper):**
- Method: `AudioService.get_volume_adjustment_command(ffmpeg_path, input_file, output_file, volume_db, apply_limiter)`
- Builds FFmpeg command for amplitude adjustment in dB
- Optional audio limiter to prevent clipping
- Usage: Adjust audio volume before export/streaming

**Feature 20 - Duration Analysis (Helper):**
- Method: `AudioService.get_file_duration(ffprobe_path, file_path)`
- Returns file duration in seconds as float
- Uses ffprobe for fast, accurate duration detection
- Returns 0.0 on error
- Usage: Essential for Features 12, 14, and other sync operations

**Feature 12 - Speed Synchronization (Helpers):**
- Methods:
  - `AudioService.calculate_speed_ratio(duration_a, duration_b)` - Calculates ratio needed to match two files
  - `AudioService.get_speed_adjustment_command(ffmpeg_path, input_file, output_file, speed_ratio)` - Builds FFmpeg command
- Adjusts both video and audio speed using setpts and atempo filters
- Usage: Match video/audio speed for perfect synchronization

**Feature 9 - Video Speed Adjustment (Helper):**
- Method: `PlayerService.get_video_speed_adjustment_command(ffmpeg_path, input_file, output_file, speed_factor)`
- Adjusts video speed independently from audio (audio stays at 1x)
- Useful for playback speed control without audio pitch shift
- Usage: Speed up/slow down video while keeping audio normal

### 14. DAT/WHATSAPP FILE CONVERSION (Feature 19) ✅ COMPLETE
**Status:** Fully Implemented with UI and full FFmpeg support

**Related files:**
- `source_code/ui/extra_page.py` → New Tab 5 "📱 DAT Converter"
- `source_code/main.py` → `convert_dat_file()` and `build_dat_conversion_cmd()` methods
- `build_system/KaraokeStudioPro.spec` → No new imports needed (uses existing ffmpeg)
- `documentation/IMPLEMENTATION_LOG.md` → Feature 19 entry

**Feature 19: DAT/WhatsApp File Conversion ✅ COMPLETE**
- Converts DAT files and other WhatsApp formats to standard formats
- Supports: WAV, MP3, M4A, MP4
- Auto-detect codec or manual format selection
- Quality control for lossy formats (High 320kbps, Medium 192kbps, Low 128kbps)
- **UI Location:** Extra Tools → Audio Tools → Tab 5 "📱 DAT Converter"

**Supported Input Formats:**
- `.dat` - Generic DAT container (WhatsApp media, karaoke machines)
- `.opus` - Opus audio codec (WhatsApp voice messages)
- `.amr` - Narrow-band AMR (older audio format)
- `.aac` - AAC audio codec
- `.m4a` - MPEG-4 audio files

**Supported Output Formats:**
- `wav` - PCM WAV (lossless, CD quality 44100 Hz)
- `mp3` - MP3 (high quality, smaller file size)
- `m4a` - AAC in MP4 container (Apple standard)
- `mp4` - Full MP4 video/audio container

**UI Controls:**
- **Source Format Dropdown:**
  - Auto-detect (Recommended) - Analyzes file automatically
  - .dat (Generic)
  - .opus (Audio Codec)
  - .amr (Narrow-band)
  - .aac (Audio Codec)
  - .m4a (Audio MPEG-4)

- **Target Format Dropdown:**
  - WAV (Lossless, CD Quality) - Default
  - MP3 (High Quality, Smaller)
  - MP4 (Video Container)
  - M4A (Audio MPEG-4)

- **Quality Selector (for MP3/M4A):**
  - High (320kbps) - Default
  - Medium (192kbps)
  - Low (128kbps)

- **Auto-detect Codec** checkbox (checked by default)
  - Optional: Analyzes file before conversion
  - Helps ffprobe detect correct codec format

**FFmpeg Commands Generated:**
```bash
# DAT to WAV (lossless)
ffmpeg -y -i input.dat -vn -acodec pcm_s16le -ar 44100 output.wav

# DAT to MP3 (high quality)
ffmpeg -y -i input.dat -vn -acodec libmp3lame -b:a 320k output.mp3

# DAT to M4A (AAC)
ffmpeg -y -i input.dat -vn -acodec aac -b:a 192k output.m4a

# DAT to MP4 (with video if present)
ffmpeg -y -i input.dat -c:v libx264 -preset fast -acodec aac -b:a 192k output.mp4
```

**Workflow:**
1. No file loaded: Click "Convert DAT File" → File dialog opens
2. File loaded: Select source format (or use Auto-detect)
3. Select target format (WAV, MP3, M4A, or MP4)
4. For lossy formats, choose quality (High/Medium/Low)
5. Click "🚀 Convert DAT File"
6. FFmpeg analyzes and converts file
7. Output auto-loads into player
8. Status shows: "✅ Conversion complete: {filename}"

**Common Use Cases:**
- Convert WhatsApp `.dat` voice messages to MP3 playable format
- Convert karaoke machine `.dat` files to standard audio
- Extract audio from `.opus` files for use in other apps
- Batch convert old audio formats to modern MP3/WAV

**File Output Naming:**
- Input: `recording.dat`
- Output: `recording_converted.wav` (or .mp3/.m4a/.mp4)
- Location: Download directory (configurable in settings)

**Processing Speed:**
- WAV/MP3 conversion: ~1-2 seconds per minute of audio
- MP4 conversion: ~5-10 seconds per minute (may re-encode video)
- Depends on file size and target format

### 15. VIDEO TOOLS - VIDEO TRIMMING ✅ COMPLETE
**Status:** Fully Implemented with Video Tools page and trim functionality

**Related files:**
- `source_code/ui/video_tools_page.py` → New UI page for video tools
- `source_code/ui/sidebar.py` → New "Video Tools" button in Extra Tools
- `source_code/ui/main_layout.py` → Added video_tools_page to stacked widget (Index 3)
- `source_code/main.py` → `trim_video()` and `build_video_trim_cmd()` methods
- `build_system/KaraokeStudioPro.spec` → Added source_code.ui.video_tools_page to hiddenimports
- `documentation/IMPLEMENTATION_LOG.md` → Video Tools entry

**Feature: Video Trimming ✅ COMPLETE**
- Trim first X seconds, last X seconds, keep range, or combinations
- Supports multiple output formats: MP4, MKV, WebM, AVI
- Format-specific codec optimization (H.264 for MP4, VP9 for WebM, etc.)
- **UI Location:** Extra Tools → Video Tools (new sidebar button)
- **Controls:**
  - ☑ Trim First X seconds (with H/M/S picker using TimePickerWidget)
  - ☑ Trim Last X seconds (with H/M/S picker)
  - ☑ Keep Range (from A to B) with Start and End H/M/S pickers
  - Output format selector (MP4, MKV, WebM, AVI)
  - "✂️ Trim Video" button (orange)

**Output Format Details:**
- **MP4**: H.264 video codec (fast preset), AAC audio (192kbps) - Best for web/streaming
- **MKV**: Copy video codec (fastest), AAC audio (192kbps) - Preserves original quality
- **WebM**: VP9 video codec (crf 30), Opus audio (192kbps) - Modern web format
- **AVI**: MPEG-4 video (q 5), MP3 audio (192kbps) - Legacy format compatibility

**FFmpeg Commands Generated:**
```bash
# Trim to MP4 (H.264 re-encode)
ffmpeg -y -ss 30 -to 120 -i input.mp4 -c:v libx264 -preset fast -c:a aac -b:a 192k output.mp4

# Trim to MKV (fast, preserves codec)
ffmpeg -y -ss 30 -to 120 -i input.mp4 -c:v copy -c:a aac -b:a 192k output.mkv

# Trim to WebM (VP9 encoding)
ffmpeg -y -ss 30 -to 120 -i input.mp4 -c:v libvpx-vp9 -crf 30 -b:v 0 -c:a libopus -b:a 192k output.webm

# Trim to AVI (MPEG-4)
ffmpeg -y -ss 30 -to 120 -i input.mp4 -c:v mpeg4 -q:v 5 -c:a libmp3lame -b:a 192k output.avi
```

**Workflow:**
1. Navigate to Video Tools (via sidebar "Video Tools" button)
2. Load a video file (any format supported by FFmpeg)
3. Select trim options:
   - Check "Trim First" and set hours/minutes/seconds to skip from beginning
   - Check "Trim Last" and set hours/minutes/seconds to remove from end
   - OR Check "Keep Range" and set exact start and end times
4. Select output format (MP4, MKV, WebM, AVI)
5. Click "✂️ Trim Video" button
6. FFmpeg trims and encodes video
7. Output saved as `{filename}_trimmed.{format}` in download directory
8. Status shows trimming progress
9. File automatically loads into player after completion

**Processing Speed:**
- MP4 output: ~1-2 seconds per 10 seconds of video (H.264 encoding)
- MKV output: ~0.5-1 second per 10 seconds (codec copy, fastest)
- WebM output: ~2-3 seconds per 10 seconds (VP9 encoding, slower)
- AVI output: ~1-2 seconds per 10 seconds (MPEG-4 encoding)

**Output File Naming:**
- Input: `video.mp4`
- Output: `video_trimmed.mp4` (or .mkv/.webm/.avi)
- Location: Download directory (configurable in settings)

**Key Features:**
- ✅ TimePickerWidget for precise H:M:S time selection
- ✅ Multiple trim options: trim first, trim last, keep range
- ✅ Auto-validates time ranges before processing
- ✅ Format-optimized FFmpeg commands
- ✅ Progress splash screen with cancel button
- ✅ Auto-loads trimmed video into player after completion
- ✅ Status feedback during trimming

### 16. DEPRECATED/DELETED FILES
**Current deprecated / removed files:**
- karaoke_app.py (REMOVED - consolidated into `source_code/main.py`)
- v2-karaoke_app - Copy.py
- v2-VLC_version.py

**When removing files:**
- Delete actual file
- Remove from version control (git)
- Update documentation (mark as deprecated or remove mention)
- Check build_system/KaraokeStudioPro.spec doesn't reference it
- Check .gitignore if needed

### 17. GITIGNORE & LOCAL FILES
**Current:**
- config/history.json (local user data, not tracked)
- __pycache__/, *.pyc
- build_system/build/, build_system/dist/

**When adding local-only files:**
- Add to .gitignore
- Document in FOLDER_ORGANIZATION_SUMMARY.txt

### 18. DOCUMENTATION SYNC CHECKLIST
**When updating docs, ensure consistency across:**
- README.md (project overview, features)
- ARCHITECTURE.md (technical design, components)
- INSTALLATION.txt (user guide, features, settings)
- FOLDER_ORGANIZATION_SUMMARY.txt (structure, recent improvements)
- BUILD_GUIDE.md (build version, prerequisites)

---

## Quick Reference: Common Tasks

### Adding a new Python module to source_code/
1. Create file: `source_code/[package]/new_file.py`
2. Add import to `build_system/KaraokeStudioPro.spec` hiddenimports
3. Import in parent file (main.py or relevant module)
4. Update documentation if structural change

### Version bump (e.g., v3 → v4)
1. Update VERSION in build.py
2. Update spec file comment
3. Update all doc titles and references
4. Update exe name in spec and docs

### Adding new audio feature
1. Implement in audio_service.py or audio_meter.py
2. Add settings fields to settings.json and settings_dialog.py
3. Integrate in main.py
4. Document in INSTALLATION.txt (Audio Calibration section)
5. Document in ARCHITECTURE.md (Audio System section)
6. Update FOLDER_ORGANIZATION_SUMMARY.txt (recent improvements)

### UI refactoring
1. Create/modify files in source_code/ui/
2. Update hiddenimports in spec file
3. Update imports in main.py
4. Update FOLDER_ORGANIZATION_SUMMARY.txt with folder structure
5. Update ARCHITECTURE.md with UI section

### Windows VLC runtime loading (python-vlc bootstrap)
1. Update `source_code/services/player_service.py` (runtime path/bootstrap logic)
2. Verify runtime files exist: `resources/libvlc.dll`, `resources/libvlccore.dll`, `resources/plugins/`
3. Update `documentation/ARCHITECTURE.md` (PlayerService responsibilities)
4. Update `DEVELOPMENT.md` (dev run guidance)
5. Update `documentation/IMPLEMENTATION_LOG.md` (record behavior change)

---

## 📋 FEATURE IMPLEMENTATION STATUS

### ✅ FULLY IMPLEMENTED & ACTIVE
- **Feature 6**: Audio Trimming with H/M/S controls
- **Feature 7**: Format Conversion (MP3, WAV, M4A, AAC, MP4, MKV, AVI, WebM)
- **Feature 8**: Audio Loudness Normalization (LUFS presets)
- **Feature 15**: Audio Stream Extraction from videos
- **Feature 19**: DAT/WhatsApp File Conversion
- **Feature 21**: YouTube video downloads (already in app)
- **Feature 32**: Playback with start/end time controls
- **Feature 33**: Stop/unload video functionality

### ⚙️ HELPER FUNCTIONS ONLY (Not requiring full UI)
These are available as service methods for future feature use:
- **Feature 5**: Volume Adjustment (`AudioService.get_volume_adjustment_command()`)
- **Feature 9**: Video Speed Adjustment (`PlayerService.get_video_speed_adjustment_command()`)
- **Feature 12**: Speed Synchronization (`AudioService.calculate_speed_ratio()`, `get_speed_adjustment_command()`)
- **Feature 20**: Duration Analysis (`AudioService.get_file_duration()`)

### ❌ NOT REQUIRED - FUTURE CONSIDERATION ONLY
These features have been marked as not required for the current roadmap. They can be added in future versions if needed.

| Feature # | Name | Status | Reason |
|-----------|------|--------|--------|
| 1 | Pitch/Key Adjustment | Not Required | Use case unclear, complex audio filter chain |
| 2 | Tempo/Speed Adjustment (Audio Only) | Not Required | Speed sync (Feature 12) available for video+audio |
| 3 | Combined Pitch-Tempo | Not Required | Would require rubberband filter, not prioritized |
| 4 | Basic Audio Format Conversion | Not Required | Feature 7 already covers all format conversion |
| 10 | Sample Rate Management | Not Required | All features auto-standardize to 44100 Hz |
| 11 | Video Speed Adjustment (Independent) | Not Required | Feature 12 handles video-audio sync |
| 13 | Subtitle Burning/Embedding | Not Required | SRT integration not in scope |
| 14 | Video Codec Handling (Optimization) | Not Required | Current setup uses -c:v copy where appropriate |
| 16 | Karaoke Video Creation | Not Required | Combines video+audio, less priority |
| 17 | Duration Matching (Feature) | Not Required | Helper functions exist via Feature 20+12 |
| 18 | Multi-Audio Track Mixing | Not Required | Complex amix filter, not prioritized |
| 19 | Frame-by-Frame Sync (PTS) | Not Required | Video-audio sync via atempo/setpts sufficient |
| 24 | BPM Detection Prep | Not Required | Would require music analysis library |
| 26 | Vocal Separation | Not Required | Requires external tool, out of scope |
| 27 | File Merging/Concatenation | Not Required | Concat demuxer complex, low priority |
| 28 | Background Image Overlay | Not Required | Video editing features lower priority |
| 29 | Platform Codec Compatibility | Not Required | Can add presets if needed later |
| 30 | Batch Processing | Not Required | Single-file operations sufficient for MVP |
| 9 | Mono Conversion | Not Required | Stereo conversion not required |
| 25 | Advanced Loudness (LUFS) | ✅ IMPLEMENTED | This is Feature 8 |

### 🎯 IMPLEMENTATION COMPLETE

**Current Version:** v3  
**Total Features in Scope:** 8 fully implemented  
**Helper Functions:** 4 available for future UI wrapping  

**What This Means:**
- ✅ All required features are COMPLETE
- ✅ Helper functions are available if needed for future expansion
- ✅ No additional features are required for current roadmap
- ✅ If you add new features in the future, update this section
