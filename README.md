# 🎤 Karaoke Studio Pro v3

A feature-rich cross-platform karaoke application built with Python, PySide6, and VLC. Perfect for karaoke enthusiasts and groups!

## ✨ Features

- **🎬 Multi-Format Playback**: Play MP4, MKV, AVI, WebM and more with VLC backend
- **📥 YouTube Downloads**: Fetch karaoke tracks directly from YouTube URLs
- **🔊 Real-Time Audio Levels**: Live audio level meter with SPL and dBFS display options
- **🎚️ Playback Control**: Play, pause, seek, and speed adjustment (0.5x - 2.0x)
- **📊 Audio Analysis**: Background audio level monitoring with configurable auto-volume reduction
- **🎛️ Audio Calibration**: Switchable measurement modes (dB Output vs SPL Estimate) for room calibration
- **💾 Settings**: Persistent storage of app preferences and recent files
- **✨ Audio Tools** (NEW v3):
  - 🎵 **Audio Extraction**: Extract audio from video files (WAV format)
  - ✂️ **Audio Trimming**: Trim first/last seconds or keep specific range (with H/M/S controls)
  - 🔄 **Format Conversion**: Convert between MP3, WAV, M4A, AAC, MP4, MKV, and more with quality control
- **🖥️ Cross-Platform**: Works on Windows, macOS, and Linux
- **📦 Standalone Distribution**: Build as a single .exe with all dependencies bundled (zero external setup needed)

## 🚀 Quick Start

### Option 1: Run from Source (Development)

**Prerequisites:**
- Python 3.8 or higher
- FFmpeg (optional, for advanced audio/video processing)
- yt-dlp (optional, for YouTube downloads via CLI)

**Installation:**
```bash
cd d:\Srikanth\Academics\Python\karaoke-player
pip install -r requirements.txt
```

**Run the Application:**
```bash
python .\source_code\main.py
```

### Option 2: Run Standalone Executable (Distribution)

If you have a built executable, simply double-click:
```
KaraokeStudioPro.exe
```

**No dependencies needed!** Everything is bundled.

## 🔨 Building a Standalone Executable

For team distribution, create a self-contained .exe:

**⚠️ Important:** Before building, ensure you have the required external tools in the `resources/` folder:
- `ffmpeg.exe`, `yt-dlp.exe`, `libvlc.dll`, `libvlccore.dll`, `plugins/`

See [BUILD_GUIDE.md](build_system/BUILD_GUIDE.md#acquiring-resource-files) for instructions on acquiring these files.

**1. Install build dependencies:**
```bash
cd d:\Srikanth\Academics\Python\karaoke-player
pip install -r build_system\requirements-build.txt
```

**2. Build the executable:**
```bash
python build_system\build.py
```

**3. Output:**
- Location: `build_system/dist/KaraokeStudioPro/`
- File: `KaraokeStudioPro.exe`

**4. Distribute:**
Copy the entire `build_system/dist/KaraokeStudioPro/` folder to your team. They can run the .exe directly!

## 📁 Project Structure

```
karaoke-player/
├── source_code/           # Main application package
│   ├── main.py           # Entry point
│   ├── dialogs/          # Settings and configuration dialogs
│   ├── services/         # Player and download services
│   ├── widgets/          # Custom UI components
│   ├── workers/          # Background threads (audio analysis)
│   └── models/           # Data models
├── build_system/         # Build configuration
│   ├── build.py          # Build orchestrator
│   ├── KaraokeStudioPro.spec  # PyInstaller config
│   └── BUILD_GUIDE.md    # Detailed build instructions
├── resources/            # External tools and assets (git-ignored binaries)
│   ├── ffmpeg.exe        # FFmpeg binary (download required)
│   ├── yt-dlp.exe        # YouTube downloader (download required)
│   ├── libvlc.dll        # VLC library (download required)
│   ├── plugins/          # VLC plugins (download required)
│   ├── splash.png        # Included
│   └── Loading.png       # Included
├── config/               # User settings
│   ├── settings.json     # Application preferences
│   └── history.json      # Recent files
└── documentation/        # Project documentation
    └── ARCHITECTURE.md   # System design
```

## 🎮 How to Use

### Loading Media
1. Click **Open File** to load a local video file
2. Or paste a YouTube URL and click **Download & Play**

### Playback
- **Play/Pause**: Click play button or press Space
- **Seek**: Click on the timeline or use arrow keys
- **Speed**: Use +/- buttons to adjust playback speed (0.5x to 2.0x)
- **Volume**: Adjust with the volume slider
- **Audio Level**: Monitor the real-time audio meter on the right

### Settings
- Click **Settings** to configure:
  - FFmpeg location
  - yt-dlp location
  - Download directory
  - Video output settings

## 📋 System Requirements

### For Development
- Python 3.8+
- 200 MB free space (for dependencies)
- Windows, macOS, or Linux

### For Standalone Executable
- Windows 7 SP1 or later (for .exe)
- 500 MB free space
- No external software required!

## 🐛 Troubleshooting

### Application won't start
- Ensure Python 3.8+ is installed: `python --version`
- Verify all dependencies: `pip install -r requirements.txt`
- Check for missing VLC libraries in resources/

### No audio output
- Verify VLC libraries are in `resources/` folder
- Check system audio settings
- Ensure sounddevice package is installed

### YouTube downloads not working
- Verify yt-dlp.exe is in `resources/` folder (or installed via pip)
- Update yt-dlp: `pip install --upgrade yt-dlp`
- Check internet connection

### App hangs on close
- This should not happen with the latest version
- If it does, force-quit and report the issue

## 📦 Dependencies

**Runtime:**
- `PySide6` - Qt6 GUI framework
- `python-vlc` - VLC media backend
- `sounddevice` - Audio level capture
- `numpy` - Audio processing
- `yt-dlp` - YouTube downloads

**External Tools (Bundled in Standalone):**
- FFmpeg - Video encoding/transcoding
- yt-dlp - YouTube content downloader
- VLC - Media playback engine

## 🔄 Updates

To update dependencies:
```bash
pip install --upgrade -r requirements.txt
```

To rebuild the standalone executable:
```bash
python build_system\build.py
```

## 📝 License

Internal use for Karaoke group.

## 🤝 Support

For issues or feature requests, refer to `build_system/BUILD_GUIDE.md` for advanced configuration.
