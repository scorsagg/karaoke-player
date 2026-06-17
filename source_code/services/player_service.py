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
        self._media = self._instance.media_new(media_path)
        self._player.set_media(self._media)
        self.media_changed.emit(media_path)

    def play(self):
        if self._player.play() == -1:
            print("Error playing media.")

    def pause(self):
        self._player.pause()

    def stop(self):
        self._player.stop()

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
