from PySide6.QtCore import QObject, Signal, QTimer
import vlc
import sys


class PlayerService(QObject):
    media_changed = Signal(str)
    playback_started = Signal()
    playback_paused = Signal()
    playback_stopped = Signal()
    position_changed = Signal(float) # 0.0 to 1.0
    time_changed = Signal(int) # milliseconds
    volume_changed = Signal(int) # 0 to 100

    def __init__(self, parent=None):
        super().__init__(parent)
        vlc_args = ["--aout=directx"] if sys.platform == "win32" else []
        self._instance = vlc.Instance(vlc_args)
        self._player = self._instance.media_player_new()
        self._media = None # Currently loaded media

        # Setup VLC event manager
        self._event_manager = self._player.event_manager()
        self._event_manager.event_attach(vlc.EventType.MediaPlayerTimeChanged, self._handle_time_changed)
        self._event_manager.event_attach(vlc.EventType.MediaPlayerPositionChanged, self._handle_position_changed)
        self._event_manager.event_attach(vlc.EventType.MediaPlayerPlaying, self._handle_playing)
        self._event_manager.event_attach(vlc.EventType.MediaPlayerPaused, self._handle_paused)
        self._event_manager.event_attach(vlc.EventType.MediaPlayerStopped, self._handle_stopped)
        self._event_manager.event_attach(vlc.EventType.MediaPlayerEndReached, self._handle_end_reached)

    def _handle_time_changed(self, event):
        self.time_changed.emit(self._player.get_time())

    def _handle_position_changed(self, event):
        self.position_changed.emit(self._player.get_position())

    def _handle_playing(self, event):
        self.playback_started.emit()

    def _handle_paused(self, event):
        self.playback_paused.emit()

    def _handle_stopped(self, event):
        self.playback_stopped.emit()

    def _handle_end_reached(self, event):
        self.playback_stopped.emit() # Treat end reached as stopped

    def set_media(self, media_path):
        print(f"[PlayerService.set_media] 🎬 ENTRY (media_path={media_path})")
        # Release old media if any
        if self._media is not None:
            try:
                self._media = None
                print(f"[PlayerService.set_media] ✓ Old media released")
            except:
                pass
        
        # Create and set new media
        print(f"[PlayerService.set_media] Creating new media...")
        self._media = self._instance.media_new(media_path)
        print(f"[PlayerService.set_media] ✓ Media object created")
        
        print(f"[PlayerService.set_media] Setting media to player...")
        self._player.set_media(self._media)
        print(f"[PlayerService.set_media] ✓ Media set to player")
        
        print(f"[PlayerService.set_media] Emitting media_changed signal...")
        self.media_changed.emit(media_path)
        print(f"[PlayerService.set_media] ✓ EXIT")

    def play(self):
        print(f"[PlayerService.play] ▶️  ENTRY")
        result = self._player.play()
        if result == -1:
            print(f"[PlayerService.play] ❌ Error playing media.")
        else:
            print(f"[PlayerService.play] ✓ Play command sent")
        print(f"[PlayerService.play] ✓ EXIT")

    def pause(self):
        """Pause playback"""
        print(f"[PlayerService.pause] ⏸️  ENTRY")
        if self._player:
            self._player.pause()
            print(f"[PlayerService.pause] ✓ Pause command sent")
        print(f"[PlayerService.pause] ✓ EXIT")
    
    def clear_media(self):
        """Clear the current media - stops playback and releases resources"""
        print(f"[PlayerService.clear_media] 🗑️  ENTRY")
        try:
            # Clear the media from the player
            self._player.set_media(None)
            print(f"[PlayerService.clear_media] ✓ Player media cleared")
        except Exception as e:
            print(f"[PlayerService.clear_media] ℹ️  set_media(None) not fully supported: {e}")
        
        # Release our reference
        if self._media is not None:
            try:
                self._media = None
                print(f"[PlayerService.clear_media] ✓ Media object released")
            except Exception as e:
                print(f"[PlayerService.clear_media] ⚠️  Error releasing media: {e}")
        
        print(f"[PlayerService.clear_media] ✓ EXIT")

    def stop(self):
        """Stop playback - use pause-based cleanup to prevent VLC decoder thread hang"""
        import time
        print(f"[PlayerService.stop] 🛑 ENTRY")
        try:
            if self._player:
                # Don't call stop() directly - it hangs with active decoder threads
                # Instead use pause and let VLC auto-cleanup
                self._player.pause()
                print(f"[PlayerService.stop] ⏸️  Paused instead of stop to prevent hang")
                
                # Wait for decoder threads to reach safe state
                time.sleep(1.0)
                
                # Clear media reference to allow VLC cleanup
                if self._media is not None:
                    try:
                        self._media = None
                        print(f"[PlayerService.stop] ✓ Media released")
                    except:
                        pass
        except Exception as e:
            print(f"[PlayerService.stop] ⚠️  Error during stop: {e}")
        print(f"[PlayerService.stop] ✓ EXIT")

    def is_playing(self):
        return self._player.is_playing()

    def get_time(self):
        return self._player.get_time()

    def set_time(self, ms):
        self._player.set_time(ms)

    def get_length(self):
        return self._player.get_length()

    def get_position(self):
        return self._player.get_position()

    def set_position(self, pos): # pos is float from 0.0 to 1.0
        self._player.set_position(pos)

    def set_volume(self, volume): # volume is int from 0 to 100
        self._player.audio_set_volume(volume)
        self.volume_changed.emit(volume)

    def get_volume(self):
        return self._player.audio_get_volume()

    def set_video_widget(self, video_widget_id):
        if sys.platform.startswith('linux'): # for X11
            self._player.set_xwindow(video_widget_id)
        elif sys.platform == 'win32': # for Windows
            self._player.set_hwnd(video_widget_id)
        elif sys.platform == 'darwin': # for macOS
            self._player.set_nsobject(video_widget_id)
        else:
            print("Unsupported platform for VLC video widget.")

    def set_rate(self, rate):
        self._player.set_rate(rate)

    def get_mute(self):
        return self._player.audio_get_mute()

    def set_mute(self, mute):
        self._player.audio_set_mute(mute)

    def get_audio_track(self):
        return self._player.audio_get_track()

    def is_active(self):
        """Returns True if player is playing or paused (not stopped/idle)."""
        state = self._player.get_state()
        return state in [vlc.State.Playing, vlc.State.Paused]

    def release(self):
        """Detach VLC event callbacks then release player and instance resources."""
        try:
            self._event_manager.event_detach(vlc.EventType.MediaPlayerTimeChanged, self._handle_time_changed)
            self._event_manager.event_detach(vlc.EventType.MediaPlayerPositionChanged, self._handle_position_changed)
            self._event_manager.event_detach(vlc.EventType.MediaPlayerPlaying, self._handle_playing)
            self._event_manager.event_detach(vlc.EventType.MediaPlayerPaused, self._handle_paused)
            self._event_manager.event_detach(vlc.EventType.MediaPlayerStopped, self._handle_stopped)
            self._event_manager.event_detach(vlc.EventType.MediaPlayerEndReached, self._handle_end_reached)
        except Exception:
            pass
        try:
            self._player.release()
        except Exception:
            pass
        try:
            self._instance.release()
        except Exception:
            pass
    
    # ===== Helper Function for Feature 9 =====
    
    def get_video_speed_adjustment_command(self, ffmpeg_path, input_file, output_file, speed_factor):
        """Feature 9: Build FFmpeg command for video-only speed adjustment"""
        video_pts_factor = 1 / speed_factor
        filter_complex = f"[0:v]setpts={video_pts_factor}*PTS[v];[0:a]atempo=1.0[a]"
        
        return [ffmpeg_path, "-y", "-i", input_file, "-filter_complex", filter_complex,
                "-map", "[v]", "-map", "[a]", output_file]
