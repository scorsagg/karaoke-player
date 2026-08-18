import os
from typing import Optional

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QMessageBox

from source_code.utils import range_rows


class PlaybackController:
    """Playback lifecycle orchestration extracted from the main window class.

    This keeps the app shell smaller while preserving the current playback UX and
    behavior. The controller acts as a focused boundary for play/pause/stop,
    seek, timing rebinds, and playback-window range execution.
    """

    def __init__(self):
        self._pw_end_ms = None
        self._pw_ranges = []
        self._pw_range_idx = 0

    def jump_time(self, app, ms: int):
        if not app.player.is_active() and not self._ensure_media_loaded_for_playback(app):
            return
        if app.player.has_media() or app.player.is_active():
            current = app.player.get_time()
            duration = app.player.get_length()
            if duration <= 0:
                return
            new_time = max(0, min(current + ms, duration - 1))
            app.player.set_position(new_time / duration)
            self._resync_realtime_audio_after_seek(app)

    def _ensure_media_loaded_for_playback(self, app):
        """Rebind media when a prior stop/end path has released VLC's active media reference."""
        needs_rebind = False
        try:
            if not app.player.has_media():
                needs_rebind = True
            elif hasattr(app.player, 'is_ended') and app.player.is_ended():
                needs_rebind = True
        except Exception:
            needs_rebind = True

        if not needs_rebind:
            return True

        if not app.video_path or not os.path.exists(app.video_path):
            return False

        try:
            app.player.set_media(app.video_path)
            return True
        except Exception as e:
            app.log_debug(f"[playback_rebind] failed for {app.video_path}: {e}")
            return False

    def _apply_pending_seek_after_play(self, app, retries=10):
        """Apply a deferred seek target after Play when media timing is available."""
        pending = getattr(app, '_pending_seek_ratio', None)
        if pending is None:
            return

        dur = int(app.player.get_length()) if app.player else -1
        if dur <= 0 and retries > 0:
            QTimer.singleShot(90, lambda: self._apply_pending_seek_after_play(app, retries - 1))
            return

        target = max(0.0, min(float(pending), 1.0))
        try:
            if dur > 0:
                app.player.set_time(int(target * dur))
            else:
                app.player.set_position(target)
        except Exception:
            pass

        app.state._pending_seek_ratio = None
        self._resync_realtime_audio_after_seek(app)

    def _resync_realtime_audio_after_seek(self, app):
        """After timeline seeks, restart shifted audio from current position when realtime mode is active."""
        try:
            if not app._is_realtime_pitch_enabled():
                return
            if not app.realtime_pitch.is_active():
                return
            if not app.player.is_active():
                return
        except Exception:
            return

        try:
            app.realtime_pitch.stop()
        except Exception:
            pass

        try:
            app.realtime_pitch.load_file(app.video_path)
            app.play_shifted(start_from_current=True)
        except Exception:
            pass

    def handle_play(self, app):
        """Play button handler — applies Playback Window settings then plays."""
        if app._is_realtime_pitch_enabled() and app.stack.currentIndex() == app.PAGE_PLAYBACK:
            app.play_shifted(start_from_current=True)
            return

        if not self._ensure_media_loaded_for_playback(app):
            QMessageBox.warning(app, "Playback", "No media available to play. Please load a file.")
            return

        self.apply_playback_window(app)
        try:
            if hasattr(app, 'realtime_pitch') and app.realtime_pitch.is_active():
                app._clear_live_amplify_preview_state()
                app.realtime_pitch.stop()
        except Exception:
            pass
        try:
            app.player.set_mute(False)
        except Exception:
            pass
        app.player.play()
        self._apply_pending_seek_after_play(app)
        app._refresh_realtime_pitch_status()

    def handle_pause(self, app):
        """Pause button handler — pause video and stop real-time shifted stream."""
        app.player.pause()
        try:
            if hasattr(app, 'realtime_pitch') and app.realtime_pitch.is_active():
                app._clear_live_amplify_preview_state()
                app.realtime_pitch.stop()
        except Exception:
            pass
        app._refresh_realtime_pitch_status()

    def handle_stop(self, app):
        """Stop button handler — rewinds to the start and detaches VLC output."""
        try:
            if hasattr(app, 'realtime_pitch') and app.realtime_pitch.is_active():
                app._clear_live_amplify_preview_state()
                app.realtime_pitch.stop()
        except Exception:
            pass

        app.player.stop()
        app.audio_service.stop_audio_monitoring()
        app.state._player_was_active = False
        app.seek_slider.setValue(0)
        app.time_label.setText("00:00")
        if app.video_path:
            app.status_label.setText(f"Status: Stopped {os.path.basename(app.video_path)}")
        else:
            app.status_label.setText("Status: Stopped")
        app._refresh_realtime_pitch_status()

    def apply_playback_window(self, app):
        """Apply active Playback Window settings: collect ranges, seek to first start, register first end cutoff."""
        self._pw_end_ms = None
        self._pw_ranges = []
        self._pw_range_idx = 0

        try:
            self._pw_ranges = range_rows.collect_ranges_ms(
                getattr(app, 'pw_ranges_container', None), merge=False
            )
        except Exception:
            self._pw_ranges = []

        try:
            print(f"[main.apply_playback_window] collected ranges: {self._pw_ranges}")
        except Exception:
            pass

        try:
            dur_ms = int(app.player.get_length()) if app.player else -1
        except Exception:
            dur_ms = -1
        if len(self._pw_ranges) == 1 and dur_ms > 0:
            only_start, only_end = self._pw_ranges[0]
            if only_start <= 0 and only_end >= max(0, dur_ms - 500):
                self._pw_ranges = []

        if not self._pw_ranges:
            app.pw_status_label.setText("No playback window active")
            app.pw_status_label.setStyleSheet("color: #888; font-size: 10px;")
            return

        start_ms, end_ms = self._pw_ranges[0]
        if start_ms > 0:
            app.player.set_time(int(start_ms))
        self._pw_range_idx = 0
        self._pw_end_ms = end_ms
        app._pw_end_ms = self._pw_end_ms
        app._pw_ranges = self._pw_ranges
        app._pw_range_idx = self._pw_range_idx

        parts = [f"{(s//1000)//60:02d}:{(s//1000)%60:02d}-{(e//1000)//60:02d}:{(e//1000)%60:02d}" for s, e in self._pw_ranges]
        app.pw_status_label.setText("Ranges: " + ", ".join(parts))
        app.pw_status_label.setStyleSheet("color: #2ecc71; font-size: 10px;")

    def clear_playback_window(self, app):
        """Reset Playback Window to a single initial range row."""
        app._pw_end_ms = None
        app._pw_ranges = []
        app._pw_range_idx = 0
        self._pw_end_ms = None
        self._pw_ranges = []
        self._pw_range_idx = 0

        try:
            total_s = app._get_current_video_duration_seconds()
            app._reset_rows_to_single_range(
                getattr(app, 'pw_ranges_container', None),
                getattr(app, 'pw_add_range', None),
                0,
                total_s,
            )
        except Exception:
            pass

        app.pw_status_label.setText("No playback window active")
        app.pw_status_label.setStyleSheet("color: #888; font-size: 10px;")

    def _on_pw_add_range(self, app):
        """Handler for Add Range button: compute sensible defaults based on last row and video length."""
        try:
            total_ms = max(0, int(app.player.get_length()))
            total_s = total_ms // 1000

            prev_end_s = range_rows.last_row_end_seconds(
                getattr(app, 'pw_ranges_container', None)
            )

            if prev_end_s >= total_s:
                try:
                    app.pw_status_label.setText("Cannot add range — already covers to video end")
                    app.pw_status_label.setStyleSheet("color: #e67e22; font-size: 10px;")
                except Exception:
                    pass
                return

            new_start = max(0, int(prev_end_s) + 1)
            new_end = max(new_start, int(total_s))

            if hasattr(app, 'pw_add_range') and callable(app.pw_add_range):
                app.pw_add_range(new_start, new_end)
        except Exception:
            pass
