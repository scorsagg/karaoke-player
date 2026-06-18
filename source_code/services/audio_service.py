"""Audio management service - handles audio analyzer and meter display coordination"""

class AudioService:
    """Service to manage audio analyzer and meter display modes"""
    
    def __init__(self, audio_analyzer, audio_meter):
        """
        Args:
            audio_analyzer: AudioAnalyzerThread instance
            audio_meter: AudioLevelMeter widget instance
        """
        self.audio_analyzer = audio_analyzer
        self.audio_meter = audio_meter
    
    def pause_analyzer(self):
        """Pause the audio analyzer - returns True if it was playing"""
        if self.audio_analyzer and hasattr(self.audio_analyzer, 'is_playing'):
            was_playing = self.audio_analyzer.is_playing
            self.audio_analyzer.set_playing(False)
            return was_playing
        return False
    
    def resume_analyzer(self):
        """Resume the audio analyzer"""
        if self.audio_analyzer:
            self.audio_analyzer.set_playing(True)
    
    def set_display_mode(self, mode):
        """Set the audio meter display mode ('dB Output (dBFS)' or 'SPL Estimate (Room)')"""
        if self.audio_meter:
            self.audio_meter.set_measurement_mode(mode)
    
    def pause_and_apply_settings(self, display_mode):
        """Pause analyzer, apply settings, return pause state for later resuming"""
        was_playing = self.pause_analyzer()
        self.set_display_mode(display_mode)
        return was_playing
    
    def cleanup(self):
        """Clean up audio service on shutdown"""
        if self.audio_analyzer:
            try:
                self.audio_analyzer.set_playing(False)
                self.audio_analyzer.stop()
                self.audio_analyzer.wait(1000)
            except Exception as e:
                print(f"Error cleaning up audio service: {e}")
