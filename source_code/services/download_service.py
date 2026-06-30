import os
import re
import subprocess
from pathlib import Path
from PySide6.QtCore import QObject, Signal, QTimer

class DownloadService(QObject):
    download_progress = Signal(int, str) # progress_value (0-100), message
    download_finished = Signal(str) # Path to downloaded file
    download_error = Signal(str)

    def __init__(self, settings_manager, process_thread_factory, parent=None):
        super().__init__(parent)
        self.settings_manager = settings_manager
        self.process_thread_factory = process_thread_factory # Factory to create ProcessThread instances
        self.download_thread = None
        self.download_url = None
        self.current_download_filename = None
        self.last_download_error = None
        self.error_emitted = False

    def _download_progress_hook(self, d):
        if d['status'] == 'downloading':
            if 'total_bytes' in d:
                total = d['total_bytes']
                downloaded = d['downloaded_bytes']
                percent = int(downloaded / total * 100) if total else 0
                speed = d.get('speed', 0) # bytes/sec
                eta = d.get('eta', 0) # seconds

                speed_str = f"{(speed / 1024 / 1024):.2f}MB/s" if speed > 0 else "N/A"
                eta_str = f"{eta}s" if eta > 0 else "N/A"

                message = f"Downloading: {percent}% at {speed_str} ETA {eta_str}"
                self.download_progress.emit(percent, message)
            elif 'total_bytes_estimate' in d:
                total = d['total_bytes_estimate']
                downloaded = d['downloaded_bytes']
                percent = int(downloaded / total * 100) if total else 0
                message = f"Downloading: {percent}% (estimated)"
                self.download_progress.emit(percent, message)
        elif d['status'] == 'finished':
            filename = d['filename']
            # yt-dlp might download multiple files or rename them based on format
            # We need to find the final video file if it's not directly in filename
            self.current_download_filename = filename # This might be a temporary name or a folder
            self.download_progress.emit(100, "Finalizing download...")
            # The actual path will be determined by the post-processing

        elif d['status'] == 'error':
            self.download_error.emit(f"Download error: {d.get('error')}")

    def download_video(self, url, download_dir, preferred_format='bv[vcodec^=avc1]+ba[acodec^=mp4a]/b'):
        self.download_url = url
        self.last_download_error = None
        self.error_emitted = False
        ytdlp_path = self.settings_manager.get("ytdlp_path", "yt-dlp")

        target_dir = Path(download_dir)
        target_dir.mkdir(parents=True, exist_ok=True)

        command = [
            ytdlp_path,
            "-f", preferred_format,
            "-o", str(target_dir / '%(title)s.%(ext)s'),
            "--no-playlist",
            "--newline",
            "--merge-output-format", "mp4",
            "--force-overwrites",
            "--no-warnings",
            url
        ]

        self.download_thread = self.process_thread_factory(cmd=command, duration=0)
        self.download_thread.line_output.connect(self._parse_download_status)
        self.download_thread.finished.connect(self._download_process_finished)
        self.download_thread.start()

    def _parse_download_status(self, status_line):
        line = status_line.strip()

        # Use character classes for literal square brackets to avoid SyntaxWarning
        # Changed \s to [ ] to avoid SyntaxWarning with raw strings
        progress_match = re.search(r'[[]download[]].*?([0-9]+\.?[0-9]*)%', line)
        if progress_match:
            percent = int(float(progress_match.group(1)))
            message = f"Downloading: {percent}%"
            self.download_progress.emit(percent, message)
            return

        # Handle post-processing messages (merging, converting)
        # These are simple string checks, no complex regex escape needed
        if '[ffmpeg] Merging formats' in line or '[ExtractAudio]' in line:
            self.download_progress.emit(95, "Post-processing: Merging audio/video...")
            return

        # Final file name when download is finished
        # yt-dlp prints the final file path like: '[download] Destination: /path/to/file.mp4'
        destination_match = re.search(r'[[]download[]] Destination:[ ]+(.*)', line)
        if destination_match:
            self.current_download_filename = destination_match.group(1).strip()
            self.download_progress.emit(100, "Download complete.")
            return

        # Handle final path lines for post-processed outputs
        final_file_match = re.search(r'[[]Merger[]] Merging formats into "(.*)"', line)
        if final_file_match:
            self.current_download_filename = final_file_match.group(1).strip()
            self.download_progress.emit(100, "Download complete.")
            return

        extracted_audio_match = re.search(r'[[]ExtractAudio[]] Destination:[ ]+(.*)', line)
        if extracted_audio_match:
            self.current_download_filename = extracted_audio_match.group(1).strip()
            self.download_progress.emit(100, "Download complete.")
            return

        # Handle errors reported via stdout
        if 'ERROR:' in line:
            self.last_download_error = line
            if not self.error_emitted:
                self.error_emitted = True
                self.download_error.emit(line)

    def _download_process_finished(self, success):
        if success:
            self.download_finished.emit(self.current_download_filename or "")
        elif not self.download_thread.is_killed and not self.error_emitted:
            self.download_error.emit(self.last_download_error or "Download process failed unexpectedly.")
            self.error_emitted = True

        self.download_thread = None
        self.download_url = None
        self.current_download_filename = None
        self.last_download_error = None
        self.error_emitted = False

    def stop_download(self):
        if self.download_thread and self.download_thread.isRunning():
            self.download_thread.is_killed = True
            self.download_thread.terminate()
            self.download_thread.wait()
            self.download_error.emit("Download cancelled by user.")
            self.download_thread = None
            self.download_url = None
            self.current_download_filename = None
            self.last_download_error = None
            self.error_emitted = False
