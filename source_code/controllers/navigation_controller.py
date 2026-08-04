import os

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QMessageBox


class NavigationController:
    """UI navigation and page-visibility orchestration for the main shell.

    The main window stays as the compatibility façade, while this controller owns
    the view-routing rules that were previously embedded in the shell methods.
    """

    def handle_navigation_change(self, app, idx, is_audio_only=None):
        # Guard studio navigation by currently loaded media type.
        current_media_type = "unknown"
        if getattr(app, 'video_path', None):
            try:
                current_media_type = app.classify_media_type(app.video_path)
            except Exception:
                current_media_type = "unknown"

        if idx == app.PAGE_AUDIO_STUDIO and current_media_type == "video":
            QMessageBox.information(
                app,
                "Audio Studio Restricted",
                "A video file is currently loaded. Use Video Studio for video workflows."
            )
            return

        if idx == app.PAGE_VIDEO_STUDIO and current_media_type == "audio":
            QMessageBox.information(
                app,
                "Video Studio Restricted",
                "An audio-only file is currently loaded. Use Audio Studio for audio workflows."
            )
            return

        if idx == app.PAGE_PLAYBACK and getattr(app, '_live_amp_preview_active', False):
            QMessageBox.information(
                app,
                "Live Amplify Preview Active",
                "Stop Live Preview on the Amplify & Export tab before switching to Playback / Real-time Pitch."
            )
            if hasattr(app, 'amp_status_label') and app.amp_status_label is not None:
                app.amp_status_label.setText("Stop Live Preview before switching to Playback / Real-time Pitch")
            return

        if idx == app.PAGE_CONVERT_EXPORT and app._is_realtime_pitch_enabled():
            target_tab = app.convert_export_tabs.currentIndex() if app.convert_export_tabs is not None else 0
            if target_tab == 4:
                QMessageBox.information(
                    app,
                    "Real-time Pitch Active",
                    "Turn Real-time Pitch Mode OFF before opening Amplify & Export."
                )
                app._refresh_realtime_pitch_status()
                return

        if idx in (app.PAGE_AUDIO_STUDIO, app.PAGE_VIDEO_STUDIO, app.PAGE_CONVERT_EXPORT):
            app.nav_list.blockSignals(True)
            app.nav_list.clearSelection()
            app.nav_list.setCurrentRow(-1)
            app.nav_list.blockSignals(False)
        else:
            app.nav_list.blockSignals(True)
            app.nav_list.setCurrentRow(idx)
            app.nav_list.blockSignals(False)

        # Switch playback-window references based on current page.
        app._set_active_playback_window_controls(idx)

        # Use provided is_audio_only or fall back to stored flag
        if is_audio_only is None:
            is_audio_only = getattr(app, '_current_is_audio_only', False)

        # Adjust video frame height based on page
        if idx == app.PAGE_AUDIO_STUDIO:
            if is_audio_only:
                app.video_frame.setMinimumHeight(80)
                app.video_frame.setMaximumHeight(100)
            else:
                app.video_frame.setMinimumHeight(80)
                app.video_frame.setMaximumHeight(220)
            app.fullscreen_btn.setVisible(False)
        elif idx == app.PAGE_VIDEO_STUDIO:
            app.fullscreen_btn.setVisible(True)
            if app.video_path:
                fname = os.path.basename(app.video_path)
                app.video_current_file_label.setText(f"✅ Working on: {fname}")
                app.video_current_file_label.setStyleSheet("color: #2ecc71; font-size: 10px; font-style: normal; padding: 2px 5px;")
                app.widen_current_file_label.setText(f"✅ Working on: {fname}")
                app.widen_current_file_label.setStyleSheet("color: #2ecc71; font-size: 10px; font-style: normal; padding: 2px 5px;")
                app.update_extraction_ui(app.classify_media_type(app.video_path) == "video")
            else:
                app.video_current_file_label.setText("No video loaded — use the Media Loader page to load a video")
                app.video_current_file_label.setStyleSheet("color: #e67e22; font-style: italic; padding: 2px 5px; font-size: 10px;")
                app.widen_current_file_label.setText("No video loaded — use the Media Loader page to load a video")
                app.widen_current_file_label.setStyleSheet("color: #e67e22; font-style: italic; padding: 2px 5px; font-size: 10px;")
                app.update_extraction_ui(False)
        elif idx == app.PAGE_CONVERT_EXPORT:
            app.video_frame.setMinimumHeight(80)
            app.video_frame.setMaximumHeight(220)
            app.fullscreen_btn.setVisible(False)
            app.refresh_conversion_targets()
        else:
            app.video_frame.setMinimumHeight(420)
            app.video_frame.setMaximumHeight(16777215)
            app.fullscreen_btn.setVisible(True)

        app.stack.setCurrentIndex(idx)

        if app.layout():
            app.layout().invalidate()

        def reset_scroll_and_activate():
            if app.layout():
                app.layout().activate()

            if idx == app.PAGE_VIDEO_STUDIO:
                self._on_video_tools_tab_changed(app, app.video_tools_tabs.currentIndex())

            if getattr(app, '_current_is_audio_only', False):
                app.show_audio_visualization()

        QTimer.singleShot(10, reset_scroll_and_activate)

    def _on_video_tools_tab_changed(self, app, tab_idx):
        """Adjust video frame height and fullscreen button based on active Video Tools tab."""
        if tab_idx in (2, 3):
            app.video_frame.setMinimumHeight(420)
            app.video_frame.setMaximumHeight(460)
            app.fullscreen_btn.setVisible(True)
            if app.video_tools_scroll:
                app.video_tools_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        else:
            app.video_frame.setMinimumHeight(80)
            app.video_frame.setMaximumHeight(160)
            app.fullscreen_btn.setVisible(True)
            if app.video_tools_scroll:
                app.video_tools_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        app.video_frame.updateGeometry()
        if app.layout():
            app.layout().invalidate()
            app.layout().activate()

    def _on_convert_export_tab_changed(self, app, tab_idx):
        """Prevent realtime pitch and realtime amplify preview pages from crossing while active."""
        if tab_idx == 4 and app._is_realtime_pitch_enabled():
            QMessageBox.information(
                app,
                "Real-time Pitch Active",
                "Turn Real-time Pitch Mode OFF before opening Amplify & Export."
            )
            if app.convert_export_tabs is not None:
                app.convert_export_tabs.blockSignals(True)
                app.convert_export_tabs.setCurrentIndex(getattr(app, '_last_non_amplify_convert_export_tab_index', 0))
                app.convert_export_tabs.blockSignals(False)
            app._refresh_realtime_pitch_status()
            return

        if tab_idx != 4:
            app._last_non_amplify_convert_export_tab_index = tab_idx
