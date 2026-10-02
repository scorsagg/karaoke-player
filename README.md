# 🎤 Karaoke Studio Pro v3

A feature-rich karaoke application built with Python, PySide6, VLC, FFmpeg, and Qt-driven media workflows for playback, conversion, trimming, reporting, and audio monitoring.

## ✨ Core capabilities

- **🎬 Multi-format playback** with VLC and video/audio file support
- **📥 YouTube downloads** via `yt-dlp`
- **🔊 Real-time audio levels** with SPL and dBFS monitoring modes
- **🎚️ Playback controls** including play/pause/seek, speed adjustment, and stop/rebind reliability
- **🎛️ Audio calibration** with configurable auto-reduction and room-specific thresholds
- **✨ Audio tools**
  - audio extraction from video
  - audio trimming with keep-range controls
  - format conversion and normalization
  - vocal separation / karaoke stem generation
  - amplification preview and export
- **🖥️ Video tools**
  - trim, playback-window controls, extraction, widen crop/zoom workflows
  - join/merge support for media combinations
- **📦 Standalone packaging** for Windows via PyInstaller
- **🧭 Documentation sync** across the project’s five-file developer workflow

## 🚀 Quick start

### Run from source

```powershell
cd d:\Srikanth\Academics\Python\karaoke-player
python .\source_code\main.py
```

### Build the packaged executable

```powershell
cd d:\Srikanth\Academics\Python\karaoke-player
C:/Users/Srikanth/AppData/Local/Programs/Python/Python313/python.exe .\build_system\build.py
```

The build output is created under `build_system/dist/KaraokeStudioPro/`.

## 📁 Project structure

```text
karaoke-player/
├── source_code/
│   ├── main.py
│   ├── controllers/
│   ├── dialogs/
│   ├── models/
│   ├── services/
│   ├── ui/
│   ├── utils/
│   ├── widgets/
│   └── workers/
├── build_system/
│   ├── build.py
│   ├── KaraokeStudioPro.spec
│   ├── BUILD_GUIDE.md
│   └── requirements-build.txt
├── config/
│   ├── settings.json
│   ├── history.json
│   ├── app_debug.log
│   └── app_errors.log
├── documentation/
│   ├── ARCHITECTURE.md
│   ├── FILE_DEPENDENCIES.md
│   ├── FOLDER_ORGANIZATION_SUMMARY.txt
│   ├── IMPLEMENTATION_LOG.md
│   ├── LOGGING.md
│   └── requirements.txt
├── resources/
│   ├── ffmpeg.exe
│   ├── ffprobe.exe
│   ├── yt-dlp.exe
│   ├── libvlc.dll
│   ├── libvlccore.dll
│   ├── plugins/
│   └── offline_models/
├── tests/
├── DEVELOPMENT.md
├── README.md
├── pytest.ini
├── KaraokePlayer.code-workspace
└── .gitignore
```

## 🧩 Important developer docs

- [DEVELOPMENT.md](DEVELOPMENT.md) — setup, developer guide, and usage patterns
- [documentation/FILE_DEPENDENCIES.md](documentation/FILE_DEPENDENCIES.md) — source-of-truth checklist for coupled file updates
- [documentation/ARCHITECTURE.md](documentation/ARCHITECTURE.md) — system design and module relationships
- [documentation/LOGGING.md](documentation/LOGGING.md) — log locations and troubleshooting workflow
- [documentation/IMPLEMENTATION_LOG.md](documentation/IMPLEMENTATION_LOG.md) — change history and completed fixes

## 🧪 Requirements

### Development/runtime

- Python 3.10+ recommended
- PySide6
- python-vlc
- numpy
- sounddevice
- yt-dlp
- FFmpeg and FFprobe available for media processing

### Build toolchain

- PyInstaller
- Python 3.13 verified runtime for the current packaging flow

## 🐛 Troubleshooting

### App does not start
- verify Python is installed and active
- install dependencies from the project requirements
- ensure bundled media tool binaries are present under `resources/`

### Audio / meter issues
- check the settings and calibration values
- review the app logs under `config/`
- see [documentation/LOGGING.md](documentation/LOGGING.md)

### Missing build/runtime tools
- confirm `ffmpeg.exe`, `ffprobe.exe`, `yt-dlp.exe`, and VLC runtime files exist in `resources/`
- follow the guidance in [build_system/BUILD_GUIDE.md](build_system/BUILD_GUIDE.md)

## 🔄 Current status

This project is in an active v3 state with modular UI, controller extraction, shared utility helpers, logging, and the current documentation sync workflow in place.

## 📝 License

Internal use for the karaoke project workflow.
