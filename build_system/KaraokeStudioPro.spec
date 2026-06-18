# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller Spec File for Karaoke Studio Pro v3

This spec file defines how to bundle the Karaoke application into a standalone executable.
Build with: python build_system/build.py (from project root)
OR: cd build_system && python build.py

All required tools are bundled:
- ffmpeg.exe, yt-dlp.exe 
- VLC libraries (libvlc.dll, libvlccore.dll, plugins/)
Team members need ZERO external dependencies!
"""

block_cipher = None

a = Analysis(
    ['../source_code/main.py'],  # Point to source_code folder
    pathex=['..'],  # Add project root to path so imports work
    
    # Binaries to include (FFmpeg and yt-dlp from resources folder)
    binaries=[
        ('../resources/ffmpeg.exe', '.'),
        ('../resources/yt-dlp.exe', '.'),
    ],
    
    # Data files and directories (from resources folder)
    # All tools bundled so team members need NO external installations
    datas=[
        ('../resources/libvlc.dll', '.'),
        ('../resources/libvlccore.dll', '.'),
        ('../resources/plugins', 'plugins'),
        ('../resources/splash.png', '.'),
        ('../resources/Loading.png', '.'),
    ],
    
    # Hidden imports (packages not automatically detected)
    hiddenimports=[
        'PySide6',
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'source_code.dialogs.settings_dialog',
        'source_code.services.download_service',
        'source_code.services.player_service',
        'source_code.widgets.audio_meter',
        'source_code.widgets.video_frame',
        'source_code.workers.audio_analyzer',
        'source_code.workers.process_thread',
        'vlc',
    ],    
    # Modules to exclude (reduces bundle size)
    excludes=[
        'tkinter',
        'matplotlib',
        'scipy',
        'pandas',
        'test',
        'tests',
        'pytest',
    ],
    noarchive=False,
    optimize=1,  # Optimization level: 1 = keep docstrings (numpy needs them)
)

# Create Python archive
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Create executable
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='KaraokeStudioPro',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,           # Use UPX compression if available
    upx_exclude=[],
    console=False,      # No console window (GUI only)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,          # Add 'icon.ico' here if you create one
)

# Collect all files into distribution folder
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='KaraokeStudioPro',
)
