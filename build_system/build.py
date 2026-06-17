#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Karaoke Studio Pro - Smart Build Script
Handles PyInstaller bundling with validation, optimization, and distribution packaging.
"""

import os
import sys
import shutil
import subprocess
import json
from pathlib import Path
from datetime import datetime

# Fix encoding for Windows console
if sys.platform == "win32":
    os.environ['PYTHONIOENCODING'] = 'utf-8'

# ============================================================================
# CONFIGURATION
# ============================================================================

PROJECT_ROOT = Path(__file__).parent.parent.resolve()  # Go up one level to parent
DIST_DIR = PROJECT_ROOT / "build_system" / "dist"
BUILD_DIR = PROJECT_ROOT / "build_system" / "build"
TEMP_DIR = PROJECT_ROOT / ".build_temp"

# Required binaries and data files (now in RESOURCES folder)
REQUIRED_BINARIES = {
    "ffmpeg.exe": "FFmpeg executable",
    "yt-dlp.exe": "yt-dlp executable",
}

REQUIRED_DATA = {
    "libvlc.dll": "VLC library",
    "libvlccore.dll": "VLC core library",
    "plugins": "VLC plugins directory",
}

# Paths to resources
RESOURCES_DIR = PROJECT_ROOT / "resources"
SOURCE_DIR = PROJECT_ROOT / "source_code"
DOC_USER_DIR = PROJECT_ROOT / "documentation" / "user_guides"

# App metadata
APP_NAME = "KaraokeStudioPro"
VERSION = "2.0"  # Update this manually or read from file
SPEC_FILE = PROJECT_ROOT / "build_system" / "KaraokeStudioPro.spec"
MAIN_SCRIPT = SOURCE_DIR / "karaoke_app.py"

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def log(message, level="INFO"):
    """Print formatted log message."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    colors = {
        "INFO": "\033[94m",      # Blue
        "SUCCESS": "\033[92m",   # Green
        "WARNING": "\033[93m",   # Yellow
        "ERROR": "\033[91m",     # Red
        "RESET": "\033[0m"
    }
    color = colors.get(level, colors["INFO"])
    reset = colors["RESET"]
    try:
        print(f"{color}[{timestamp}] [{level}]{reset} {message}")
    except UnicodeEncodeError:
        print(f"[{timestamp}] [{level}] {message}")

def validate_prerequisites():
    """Check all required files exist."""
    log("Validating prerequisites...", "INFO")
    
    missing = []
    
    # Check main script
    if not MAIN_SCRIPT.exists():
        missing.append(f"Main script: {MAIN_SCRIPT}")
    
    # Check spec file
    if not SPEC_FILE.exists():
        missing.append(f"Spec file: {SPEC_FILE}")
    
    # Check required binaries
    for binary, desc in REQUIRED_BINARIES.items():
        binary_path = RESOURCES_DIR / binary
        if not binary_path.exists():
            missing.append(f"{desc}: {binary_path}")
    
    # Check required data files
    for data, desc in REQUIRED_DATA.items():
        data_path = RESOURCES_DIR / data
        if not data_path.exists():
            missing.append(f"{desc}: {data_path}")
    
    if missing:
        log("[ERROR] Missing required files/directories:", "ERROR")
        for item in missing:
            print(f"   - {item}")
        return False
    
    log("[OK] All prerequisites validated", "SUCCESS")
    return True

def clean_old_builds():
    """Remove old build artifacts."""
    log("Cleaning old builds...", "INFO")
    
    dirs_to_clean = [
        BUILD_DIR,
        DIST_DIR,
        TEMP_DIR,
    ]
    
    count = 0
    for path in dirs_to_clean:
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)
            count += 1
    
    # Clean egg-info directories
    for item in PROJECT_ROOT.glob("*.egg-info"):
        if item.is_dir():
            shutil.rmtree(item, ignore_errors=True)
            count += 1
    
    # Clean pycache
    pycache = PROJECT_ROOT / "__pycache__"
    if pycache.exists():
        shutil.rmtree(pycache, ignore_errors=True)
        count += 1
    
    log(f"[OK] Cleaned {count} old build directories", "SUCCESS")

def run_pyinstaller():
    """Execute PyInstaller with spec file."""
    log("Running PyInstaller...", "INFO")
    
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--distpath", str(DIST_DIR),
        "--workpath", str(BUILD_DIR),
        str(SPEC_FILE)
    ]
    
    try:
        result = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=False, check=True)
        log("[OK] PyInstaller completed successfully", "SUCCESS")
        return True
    except subprocess.CalledProcessError as e:
        log(f"[ERROR] PyInstaller failed with error code {e.returncode}", "ERROR")
        return False
    except FileNotFoundError:
        log("[ERROR] PyInstaller not found. Install with: pip install pyinstaller", "ERROR")
        return False

def create_manifest():
    """Create manifest of bundled files."""
    log("Creating build manifest...", "INFO")
    
    app_dir = DIST_DIR / APP_NAME
    if not app_dir.exists():
        log("[WARNING] App directory not found, skipping manifest", "WARNING")
        return
    
    manifest = {
        "app_name": APP_NAME,
        "version": VERSION,
        "build_time": datetime.now().isoformat(),
        "binaries": [],
        "data_files": [],
        "total_size_mb": 0,
    }
    
    total_size = 0
    
    for root, dirs, files in os.walk(app_dir):
        for file in files:
            file_path = Path(root) / file
            rel_path = file_path.relative_to(app_dir)
            file_size = file_path.stat().st_size
            total_size += file_size
            
            # Categorize files
            if file_path.suffix in [".exe", ".dll"]:
                manifest["binaries"].append({
                    "name": str(rel_path),
                    "size_bytes": file_size,
                })
            else:
                manifest["data_files"].append({
                    "name": str(rel_path),
                    "size_bytes": file_size,
                })
    
    manifest["total_size_mb"] = round(total_size / (1024 * 1024), 2)
    
    manifest_file = DIST_DIR / "build_manifest.json"
    with open(manifest_file, "w") as f:
        json.dump(manifest, f, indent=2)
    
    log(f"[OK] Manifest created: {manifest_file}", "SUCCESS")
    log(f"   - Total size: {manifest['total_size_mb']} MB", "INFO")
    log(f"   - Binaries: {len(manifest['binaries'])}", "INFO")
    log(f"   - Data files: {len(manifest['data_files'])}", "INFO")

def copy_user_documentation():
    """Copy user documentation to dist folder."""
    log("Copying user documentation...", "INFO")
    
    app_dir = DIST_DIR / APP_NAME
    if not app_dir.exists():
        log("[WARNING] App directory not found, skipping documentation copy", "WARNING")
        return
    
    doc_files = [
        "README.md",
        "QUICK_START.txt",
        "INSTALLATION.txt"
    ]
    
    copied = 0
    for doc_file in doc_files:
        src = DOC_USER_DIR / doc_file
        dst = app_dir / doc_file
        if src.exists():
            shutil.copy2(src, dst)
            copied += 1
            log(f"   [OK] Copied {doc_file}", "INFO")
        else:
            log(f"   [WARNING] Not found: {doc_file}", "WARNING")
    
    log(f"[OK] Documentation copied ({copied} files)", "SUCCESS")

def copy_image_resources():
    """Copy image resources (splash and loading images) to dist folder."""
    log("Copying image resources...", "INFO")
    
    app_dir = DIST_DIR / APP_NAME
    if not app_dir.exists():
        log("[WARNING] App directory not found, skipping image copy", "WARNING")
        return
    
    image_files = [
        "splash.png",
        "Loading.png"
    ]
    
    copied = 0
    for image_file in image_files:
        src = RESOURCES_DIR / image_file
        dst = app_dir / image_file
        if src.exists():
            shutil.copy2(src, dst)
            copied += 1
            log(f"   [OK] Copied {image_file}", "INFO")
        else:
            log(f"   [WARNING] Not found: {image_file}", "WARNING")
    
    log(f"[OK] Image resources copied ({copied} files)", "SUCCESS")

def create_distribution_zip():
    """Create .zip file for distribution."""
    log("Creating distribution package...", "INFO")
    
    app_dir = DIST_DIR / APP_NAME
    if not app_dir.exists():
        log("[ERROR] App directory not found", "ERROR")
        return False
    
    zip_name = f"{APP_NAME}_v{VERSION}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    zip_path = DIST_DIR / zip_name
    
    try:
        shutil.make_archive(
            str(zip_path),
            "zip",
            DIST_DIR,
            APP_NAME
        )
        
        zip_file = Path(str(zip_path) + ".zip")
        zip_size_mb = round(zip_file.stat().st_size / (1024 * 1024), 2)
        
        log(f"[OK] Distribution zip created", "SUCCESS")
        log(f"   - File: {zip_file.name}", "INFO")
        log(f"   - Size: {zip_size_mb} MB", "INFO")
        return True
    except Exception as e:
        log(f"[ERROR] Failed to create zip: {e}", "ERROR")
        return False

def print_summary():
    """Print build summary."""
    print("\n" + "="*70)
    log("BUILD SUMMARY", "INFO")
    print("="*70)
    
    app_dir = DIST_DIR / APP_NAME
    if app_dir.exists():
        log(f"[OK] Application bundle: {app_dir}", "SUCCESS")
        
        # Count files
        file_count = sum(1 for _ in app_dir.rglob("*") if _.is_file())
        dir_count = sum(1 for _ in app_dir.rglob("*") if _.is_dir())
        
        log(f"   - Files: {file_count}", "INFO")
        log(f"   - Directories: {dir_count}", "INFO")
        
        # Check for manifest
        manifest_file = DIST_DIR / "build_manifest.json"
        if manifest_file.exists():
            with open(manifest_file) as f:
                manifest = json.load(f)
            log(f"   - Total size: {manifest['total_size_mb']} MB", "INFO")
    
    # Check for zip
    zip_files = list(DIST_DIR.glob(f"{APP_NAME}_v{VERSION}_*.zip"))
    if zip_files:
        zip_file = zip_files[0]
        zip_size_mb = round(zip_file.stat().st_size / (1024 * 1024), 2)
        log(f"[OK] Distribution package: {zip_file.name} ({zip_size_mb} MB)", "SUCCESS")
    
    print("="*70)
    log("Next steps:", "INFO")
    print("  1. Test the built executable: dist/KaraokeStudioPro/KaraokeStudioPro.exe")
    print("  2. Distribute the .zip file from dist/")
    print("  3. Users extract and run: KaraokeStudioPro/KaraokeStudioPro.exe")
    print("="*70 + "\n")

def main():
    """Main build orchestration."""
    log(f"Starting build process for {APP_NAME} v{VERSION}", "INFO")
    print()
    
    # Step 1: Validate
    if not validate_prerequisites():
        log("Build failed: Prerequisites not met", "ERROR")
        return False
    
    # Step 2: Clean
    clean_old_builds()
    
    # Step 3: Build
    if not run_pyinstaller():
        log("Build failed: PyInstaller error", "ERROR")
        return False
    
    # Step 4: Create manifest
    create_manifest()
    
    # Step 4b: Copy documentation
    copy_user_documentation()
    
    # Step 4c: Copy image resources
    copy_image_resources()
    
    # Step 5: Create distribution zip
    create_distribution_zip()
    
    # Step 6: Summary
    print_summary()
    
    log("[OK] Build completed successfully!", "SUCCESS")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
