# Karaoke Studio Pro - Build Guide

## Overview
This guide explains how to build a **complete standalone executable** of Karaoke Studio Pro that includes all required tools (FFmpeg, yt-dlp, VLC libraries) so team members need **zero external dependencies**.

## Prerequisites

### For Building:
1. **Python 3.8+** installed on your system
2. **All runtime dependencies** installed:
   ```powershell
   pip install -r requirements-build.txt
   ```

3. **All bundled tools present** in `resources/` folder:
   - ⚠️ `ffmpeg.exe` - Video processing
   - ⚠️ `yt-dlp.exe` - YouTube/stream downloading
   - ⚠️ `libvlc.dll` - VLC video library
   - ⚠️ `libvlccore.dll` - VLC core library
   - ⚠️ `plugins/` - VLC plugins directory
   - ✅ `splash.png` - Splash screen image
   - ✅ `Loading.png` - Loading screen image

### ⚠️ Important: Acquiring Resource Files

The EXE and DLL files are **NOT included in the repository** because they are large binaries and belong in a shared resource location. Here's how to set them up:

#### Option 1: From Shared Storage (Recommended for Teams)
Contact your team lead to get the `resources/` folder with all files already included.

#### Option 2: Manual Setup (Individual Setup)
1. **Download FFmpeg**
   - Go to: https://ffmpeg.org/download.html
   - Download Windows build (static)
   - Extract and copy `ffmpeg.exe` to `resources/`

2. **Download yt-dlp**
   - Go to: https://github.com/yt-dlp/yt-dlp/releases
   - Download `yt-dlp.exe` 
   - Copy to `resources/`

3. **Download VLC Libraries**
   - Go to: https://www.videolan.org/vlc/download-windows.html
   - Download Windows installer
   - Extract VLC and copy:
     - `libvlc.dll` → `resources/`
     - `libvlccore.dll` → `resources/`
     - `plugins/` folder → `resources/plugins/`

**Verify setup:**
```powershell
ls resources/
# Should show: ffmpeg.exe, yt-dlp.exe, libvlc.dll, libvlccore.dll, plugins/, splash.png, Loading.png
```

## Building the Executable

### Method 1: From Project Root
```powershell
cd D:\Srikanth\Academics\Python\karaoke-player

pip install -r build_system\requirements-build.txt

python build_system\build.py
```

### Method 2: From Build System Folder
```powershell
cd D:\Srikanth\Academics\Python\karaoke-player\build_system

pip install -r requirements-build.txt

python build.py
```

## Build Output

### Folder Structure
```
build_system/
├── dist/
│   └── KaraokeStudioPro/          # ← Final executable folder
│       ├── KaraokeStudioPro.exe   # ← Main executable (RUN THIS)
│       ├── ffmpeg.exe             # Bundled
│       ├── yt-dlp.exe             # Bundled
│       ├── libvlc.dll             # Bundled
│       ├── libvlccore.dll         # Bundled
│       ├── plugins/               # Bundled (VLC plugins)
│       ├── splash.png             # Bundled
│       ├── Loading.png            # Bundled
│       └── ... (other support files)
│
├── build/                          # (Temporary - can be deleted)
├── KaraokeStudioPro_v2.0_*.zip    # Distribution package
└── build_manifest.json             # Build information
```

## Distribution

### For Team Members:

**Option 1: Direct Folder (Fastest)**
1. Copy the `dist/KaraokeStudioPro/` folder to your team member
2. They simply run: `KaraokeStudioPro.exe`
3. No installation, no dependencies, just works!

**Option 2: ZIP File (Professional)**
1. The build automatically creates `KaraokeStudioPro_v2.0_*.zip`
2. Share this ZIP file with your team
3. Team extracts and runs `KaraokeStudioPro/KaraokeStudioPro.exe`

### System Requirements for End Users:
- **Windows 7 or later** (64-bit recommended)
- **No additional software needed** - Everything is bundled!
- That's it! 🎉

## What's Included in the Build

### Tools (Bundled)
- ✅ **FFmpeg** - Video encoding/decoding
- ✅ **yt-dlp** - YouTube and stream downloading
- ✅ **VLC** - Video/audio playback libraries

### Python Libraries (Bundled)
- ✅ PySide6 - GUI framework
- ✅ python-vlc - VLC bindings
- ✅ sounddevice - Audio capture
- ✅ numpy - Numerical processing
- ✅ All other dependencies

### Application Files (Bundled)
- ✅ All source code from `source_code/` folder
- ✅ Splash screen and loading images
- ✅ Configuration framework

## Troubleshooting

### Build Fails: "Missing required files"
**Cause:** The EXE and DLL files are not in the `resources/` folder (they're git-ignored).

**Solution:** Follow the **Acquiring Resource Files** section above to download and place them in `resources/`:
```powershell
ls resources/
```
Required files:
- ffmpeg.exe
- yt-dlp.exe
- libvlc.dll
- libvlccore.dll
- plugins/ (folder)

### Build Takes a Long Time
**Normal behavior!** First build compiles and bundles everything (~5-15 minutes depending on system).

### Executable Won't Run
1. Run from `build_system/dist/KaraokeStudioPro/KaraokeStudioPro.exe`
2. Try running with administrator privileges
3. Check Windows Defender/Antivirus - may be blocking (add exception)

### File Size Too Large
The standalone executable is typically **400-800 MB** due to bundled tools. This is normal.

## Build Customization

### Exclude Dependencies (Reduce Size)
Edit `KaraokeStudioPro.spec`:
- Remove items from `excludes=[]` list
- Example: Remove `'tkinter'` if you use Tkinter elsewhere

### Add Custom Resources
Edit `KaraokeStudioPro.spec` and add to `datas=[...]`:
```python
datas=[
    ('../resources/myfile.txt', '.'),
]
```

### Change Version
Edit `build.py`, line ~50:
```python
VERSION = "2.1"  # Update version number
```

## Advanced: Updating Bundled Tools

### Update FFmpeg
1. Download from https://ffmpeg.org/download.html
2. Replace `resources/ffmpeg.exe` with new version
3. Rebuild with `python build.py`

### Update yt-dlp
1. Download from https://github.com/yt-dlp/yt-dlp/releases
2. Replace `resources/yt-dlp.exe` with new version
3. Rebuild with `python build.py`

### Update VLC Libraries
1. Download VLC portable from https://www.videolan.org/
2. Extract VLC binaries and plugins
3. Replace `resources/libvlc.dll`, `libvlccore.dll`, `plugins/`
4. Rebuild with `python build.py`

## Performance Optimization

### Reduce Build Time (Subsequent Builds)
```powershell
# Clean only cache, keep dist
rm -r build_system\build

# Then rebuild (faster)
python build_system\build.py
```

### Reduce Bundle Size
Edit `build.py`, line ~75, increase `optimize` level:
```python
optimize=2,  # 0 = none, 1 = small, 2 = medium, 3 = aggressive
```

## Support & Help

For issues:
1. Check the troubleshooting section above
2. Check build logs in console output
3. Verify all resources are present in `resources/` folder
4. Ensure PyInstaller is installed: `pip install pyinstaller>=6.0.0`

---

**Happy Building! 🎵**
Your team can now use Karaoke Studio Pro with zero setup required!
