import json
import os
import shutil
import time
from pathlib import Path

from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

from source_code.utils.audio_activity import (
    ACTIVITY_THRESHOLD_DBFS,
    active_ranges_from_rms_metadata,
    build_activity_scan_command,
)
from source_code.utils.splash_utils import create_loading_splash
from source_code.workers.process_thread import ProcessThread


class MediaController:
    """Media loading, history, and load-finalization orchestration."""

    def stop_audio_activity_scan(self, app):
        """Stop an in-flight timeline scan before replacing media or closing the app."""
        app._audio_activity_scan_generation = getattr(app, "_audio_activity_scan_generation", 0) + 1
        thread = getattr(app, "_audio_activity_scan_thread", None)
        if thread is not None and thread.isRunning():
            thread.stop()
            thread.wait(2000)
        app._audio_activity_scan_thread = None

    def _start_audio_activity_scan(self, app, media_path):
        """Analyze audio in the background and update seek-bar highlights on completion."""
        self.stop_audio_activity_scan(app)
        seek_slider = getattr(app, "seek_slider", None)
        if "ffmpeg_path" not in app.settings or not hasattr(seek_slider, "set_activity_ranges"):
            return

        ffmpeg_path = str(app.settings["ffmpeg_path"]).strip()
        if not ffmpeg_path or shutil.which(ffmpeg_path) is None:
            app.log_warning(f"[audio_activity] FFmpeg executable is unavailable: {ffmpeg_path!r}")
            return

        generation = app._audio_activity_scan_generation
        lines = []
        thread = ProcessThread(build_activity_scan_command(ffmpeg_path, media_path))
        app._audio_activity_scan_thread = thread
        thread.line_output.connect(lines.append)
        thread.finished.connect(
            lambda success: self._finish_audio_activity_scan(
                app, thread, media_path, generation, lines, success
            )
        )
        thread.start()

    def _finish_audio_activity_scan(self, app, thread, media_path, generation, lines, success):
        if getattr(app, "_audio_activity_scan_thread", None) is thread:
            app._audio_activity_scan_thread = None
        thread.deleteLater()
        if generation != getattr(app, "_audio_activity_scan_generation", 0):
            return

        current_path = getattr(app, "video_path", "")
        if not current_path or os.path.normcase(os.path.abspath(current_path)) != os.path.normcase(
            os.path.abspath(media_path)
        ):
            return
        if not success:
            app.log_warning(f"[audio_activity] FFmpeg scan failed for {media_path}")
            return

        duration = 0.0
        try:
            duration = max(0, int(app.player.get_length())) / 1000.0
        except Exception as e:
            app.log_debug(f"[audio_activity] player duration unavailable: {e}")
        if duration <= 0:
            duration = app.get_video_duration_via_ffprobe(media_path)
        if duration <= 0:
            app.log_warning(f"[audio_activity] Could not determine duration for {media_path}")
            return

        ranges = active_ranges_from_rms_metadata(lines, duration)
        app.seek_slider.set_activity_ranges(ranges)
        app.log_info(
            f"[audio_activity] Detected {len(ranges)} active ranges above "
            f"{ACTIVITY_THRESHOLD_DBFS} dBFS source RMS for {os.path.basename(media_path)}"
        )

    def add_to_history(self, app, file_path):
        if not file_path or not os.path.exists(file_path):
            return
        filename = os.path.basename(file_path)
        for i in range(app.history_list.count()):
            if app.history_list.item(i).toolTip() == file_path:
                app.history_list.takeItem(i)
                break
        app.history_list.insertItem(0, filename)
        app.history_list.item(0).setToolTip(file_path)
        while app.history_list.count() > 10:
            app.history_list.takeItem(app.history_list.count() - 1)
        self.save_history_to_disk(app)

    def save_history_to_disk(self, app):
        paths = [app.history_list.item(i).toolTip() for i in range(app.history_list.count())]
        history_file = Path(app.settings_file.parent) / "history.json"
        try:
            with open(history_file, "w", encoding="utf-8") as f:
                json.dump(paths, f, indent=2)
        except Exception as e:
            app.log_exception("save_history_to_disk", e)

    def load_history_from_disk(self, app):
        history_file = Path(app.settings_file.parent) / "history.json"
        if history_file.exists():
            try:
                with open(history_file, "r", encoding="utf-8") as f:
                    paths = json.load(f)
                    for path in reversed(paths):
                        if os.path.exists(path):
                            filename = os.path.basename(path)
                            app.history_list.insertItem(0, filename)
                            app.history_list.item(0).setToolTip(path)
            except Exception as e:
                app.log_exception("load_history_from_disk", e)

    def clear_history(self, app):
        app.history_list.clear()
        history_file = Path(app.settings_file.parent) / "history.json"
        if history_file.exists():
            history_file.unlink()

    def toggle_history(self, app):
        app.state.history_is_expanded = not app.state.history_is_expanded
        app.history_container.setVisible(app.state.history_is_expanded)
        app.history_toggle_btn.setText(f"{'▼' if app.state.history_is_expanded else '▶'} History")

    def toggle_extra_tools(self, app):
        app.state.extra_tools_is_expanded = not app.state.extra_tools_is_expanded
        app.extra_tools_container.setVisible(app.state.extra_tools_is_expanded)
        app.extra_tools_toggle_btn.setText(f"{'▼' if app.state.extra_tools_is_expanded else '▶'} 🧭 Studios")

    def load_video(self, app, file_path=None, splash_screen=None, is_audio_only=None):
        print(f"\n\n{'='*80}")
        print(f"[main.load_video] 🎬 ENTRY (file_path={file_path})")

        try:
            if hasattr(app, 'realtime_pitch') and app.realtime_pitch.is_active():
                app.realtime_pitch.stop()
            if hasattr(app, '_clear_live_amplify_preview_state'):
                app._clear_live_amplify_preview_state()
            app.player.set_mute(False)
        except Exception as e:
            app.log_exception("load_video.pre_load_cleanup", e)

        if not file_path:
            print(f"[main.load_video] 📂 No file path provided, opening dialog...")
            f, _ = QFileDialog.getOpenFileName(
                app,
                "Open Audio/Video Track Resource",
                app.settings["base_directory"],
                "Media Feeds (*.mp4 *.avi *.mkv *.mov *.mp3 *.wav *.aac *.m4a *.webm);;All System Inputs (*.*)",
            )
            if not f:
                print(f"[main.load_video] ❌ Dialog cancelled")
                return
            file_path = f
            print(f"[main.load_video] ✓ File selected: {file_path}")

        detected_audio_only = app.classify_media_type(file_path) == "audio"
        if is_audio_only is None:
            is_audio_only = detected_audio_only
        elif detected_audio_only and not is_audio_only:
            is_audio_only = True

        if splash_screen is None:
            loader = create_loading_splash()
            loader.show()
        else:
            loader = splash_screen

        loader.set_progress(10, "Preparing Media Loader...")
        QApplication.processEvents()

        print(f"[main.load_video] Calling file_loading_service.prepare_for_loading()...")
        was_playing = app.file_loading_service.prepare_for_loading()
        print(f"[main.load_video] ✓ prepare_for_loading returned (was_playing={was_playing})")

        loader.set_progress(25, "Preparing Playback Resources...")
        QApplication.processEvents()
        app.state._pending_video_path = file_path
        self.add_to_history(app, file_path)
        app.status_label.setText(f"Status: Loading {os.path.basename(file_path)}...")
        app._reset_pitch_display()

        try:
            print(f"[main.load_video] 🎯 Starting core loading logic...")
            loader.set_progress(40, "Mapping Core Encoders...")
            app.video_path = app.state._pending_video_path
            print(f"[main.load_video] 📝 Setting video_path: {app.video_path}")
            seek_slider = getattr(app, "seek_slider", None)
            if hasattr(seek_slider, "set_activity_ranges"):
                seek_slider.set_activity_ranges([])
            self._start_audio_activity_scan(app, app.video_path)

            print(f"[main.load_video] 🎬 Calling player.set_media({os.path.abspath(app.video_path)})...")
            app.player.set_media(os.path.abspath(app.video_path))
            print(f"[main.load_video] ✓ player.set_media() complete")

            print(f"[main.load_video] 🖥️  Calling player.set_video_widget()...")
            app.player.set_video_widget(int(app.video_frame.winId()))
            print(f"[main.load_video] ✓ Video widget set")

            loader.set_progress(70, "Synchronizing Canvas Matrix Pipeline...")
            time.sleep(0.1)
            print(f"[main.load_video] ⏱️  Waited 0.1s before playback...")

            print(f"[main.load_video] ▶️  Calling player.play()...")
            app.player.play()
            print(f"[main.load_video] ✓ player.play() called")

            app.time_label.setText("00:00")

            print(f"[main.load_video] 🔊 Waiting for audio track (retries up to 20)...")
            retries = 0
            while app.player.get_audio_track() == -1 and retries < 20:
                time.sleep(0.05)
                QApplication.processEvents()
                retries += 1
            print(f"[main.load_video] ✓ Audio track detected after {retries} retries")

            print(f"[main.load_video] 🔉 Setting volume to {app.vol_slider.value()}...")
            app.set_volume(app.vol_slider.value())
            print(f"[main.load_video] ✓ Volume set")

            print(f"[main.load_video] 🎙️  Starting audio analyzer (via audio_service)...")
            app.audio_service.start_audio_monitoring()
            print(f"[main.load_video] ✓ Audio analyzer started")

            print(f"[main.load_video] 📊 Calling finish_loading(loader)...")
            app.finish_loading(loader, is_audio_only)
            print(f"[main.load_video] ✓ finish_loading() complete")

            app.status_label.setText(f"Status: Playing {os.path.basename(app.video_path)}")
            app._refresh_realtime_pitch_status()
        except Exception as e:
            self.stop_audio_activity_scan(app)
            seek_slider = getattr(app, "seek_slider", None)
            if hasattr(seek_slider, "set_activity_ranges"):
                seek_slider.set_activity_ranges([])
            app.log_exception("main.load_video", e)
            loader.close()
            app.status_label.setText("Status: Load failed")
            app._refresh_realtime_pitch_status()
        finally:
            print(f"[main.load_video] 🔚 Calling file_loading_service.finish_loading(resume_audio={was_playing})...")
            app.file_loading_service.finish_loading(resume_audio=was_playing)
            app._refresh_realtime_pitch_status()
            print(f"[main.load_video] ✓ file_loading_service.finish_loading() complete")
            print(f"{'='*80}\n")

    def finish_loading(self, app, loader, is_audio_only=False):
        app.pitch_input.setValue(0.0)
        app.speed_input.setValue(1.0)
        app._reset_pitch_display()
        app._reset_all_page_timers_on_load()
        app._reset_all_page_controls_on_load(is_audio_only)
        if app.video_path:
            app.filename_label.setText(f"Playing: {os.path.basename(app.video_path)}")

        loader.set_progress(100, "Ready")
        loader.finish(app)

        app.state._current_is_audio_only = is_audio_only

        current_page = app.stack.currentIndex()
        if current_page == app.PAGE_AUDIO_STUDIO:
            if is_audio_only:
                app.video_frame.setMinimumHeight(80)
                app.video_frame.setMaximumHeight(100)
            else:
                app.video_frame.setMinimumHeight(280)
                app.video_frame.setMaximumHeight(320)
        elif current_page == app.PAGE_VIDEO_STUDIO:
            app.update_extraction_ui(app.classify_media_type(app.video_path) == "video")

        if is_audio_only:
            app.show_audio_visualization()
        else:
            app.hide_audio_visualization()

        app._sync_all_page_timer_defaults_from_media()

    def update_extraction_ui(self, app, is_video):
        if is_video and app.video_path:
            filename = os.path.basename(app.video_path)
            app.video_extract_status_label.setText(f"✅ Ready to extract from: {filename}")
            app.video_extract_status_label.setStyleSheet("color: #2ecc71; font-size: 10px; padding: 2px 4px;")
            app.extract_format_combo.setEnabled(True)
            app.extract_btn.setEnabled(True)
        else:
            app.video_extract_status_label.setText("Load a video from the Media Loader page to extract audio")
            app.video_extract_status_label.setStyleSheet("color: #e67e22; font-size: 10px; font-style: italic; padding: 2px 4px;")
            app.extract_format_combo.setEnabled(False)
            app.extract_btn.setEnabled(False)

    def load_audio_tools_file(self, app):
        f, _ = QFileDialog.getOpenFileName(
            app,
            "Open Audio File for Processing",
            app.settings["base_directory"],
            "Audio Files (*.mp3 *.wav *.aac *.m4a *.flac *.ogg *.opus *.wma);;All Files (*.*)",
        )
        if f:
            f = os.path.normpath(f)
            media_type = app.classify_media_type(f)
            if media_type != "audio":
                QMessageBox.warning(
                    app,
                    "Audio Studio Only",
                    "Audio Studio accepts only audio files. Use Media Loader to open video or mixed media files.",
                )
                return

            app.audio_tools_file_path = f
            filename = os.path.basename(f)
            app.audio_file_status.setText(f"✅ {filename} (Audio)")
            app.load_video(f, is_audio_only=True)

    def load_history_item(self, app, file_path):
        if not os.path.exists(file_path):
            QMessageBox.warning(app, "File Not Found", f"File no longer exists:\n{file_path}")
            return

        media_type = app.classify_media_type(file_path)
        is_audio = media_type == "audio"
        is_video = media_type == "video"

        current_page = app.stack.currentIndex()
        if current_page == app.PAGE_AUDIO_STUDIO:
            if is_video:
                QMessageBox.information(
                    app,
                    "Routed to Video Studio",
                    "This file contains a video stream. Opening it in Video Studio.",
                )
                app.load_video(file_path, is_audio_only=False)
                app.handle_navigation_change(app.PAGE_VIDEO_STUDIO)
                return

            app.audio_tools_file_path = file_path
            filename = os.path.basename(file_path)
            if is_video:
                app.audio_file_status.setText(f"✅ {filename}")
            else:
                app.audio_file_status.setText(f"✅ {filename} (Audio)")

        app.load_video(file_path, is_audio_only=is_audio)
        app.refresh_conversion_targets(file_path)
