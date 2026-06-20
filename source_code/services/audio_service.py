"""Audio management service - handles audio analyzer and meter display coordination"""

import time

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
        """Pause the audio analyzer by stopping the thread and closing sounddevice stream"""
        print(f"[AudioService.pause_analyzer] ⏸️  ENTRY (audio_analyzer={self.audio_analyzer is not None})")
        if self.audio_analyzer and hasattr(self.audio_analyzer, 'is_playing'):
            was_playing = self.audio_analyzer.is_playing
            print(f"[AudioService.pause_analyzer] is_playing={was_playing}")
            
            if was_playing:
                print(f"[AudioService.pause_analyzer] Calling stop() to close sounddevice InputStream...")
                try:
                    self.audio_analyzer.stop()
                    print(f"[AudioService.pause_analyzer] ✓ Audio analyzer stopped and sounddevice stream closed")
                except Exception as e:
                    print(f"[AudioService.pause_analyzer] ❌ Error stopping thread: {e}")
            else:
                print(f"[AudioService.pause_analyzer] Thread not playing, skipping stop")
            
            print(f"[AudioService.pause_analyzer] ✓ EXIT (was_playing={was_playing})")
            return was_playing
        print(f"[AudioService.pause_analyzer] ℹ️  Audio analyzer not available, returning False")
        print(f"[AudioService.pause_analyzer] ✓ EXIT (was_playing=False)")
        return False
    
    def resume_analyzer(self):
        """Resume the audio analyzer - recreate and restart the thread"""
        print(f"[AudioService.resume_analyzer] ▶️  ENTRY (audio_analyzer={self.audio_analyzer is not None})")
        
        if self.audio_analyzer:
            is_running = self.audio_analyzer.isRunning() if hasattr(self.audio_analyzer, 'isRunning') else False
            print(f"[AudioService.resume_analyzer] Thread isRunning={is_running}")
            
            if not is_running:
                print(f"[AudioService.resume_analyzer] Thread was stopped, creating new AudioAnalyzerThread...")
                try:
                    from source_code.workers.audio_analyzer import AudioAnalyzerThread
                    
                    # Create new thread
                    new_thread = AudioAnalyzerThread()
                    
                    # Reconnect the level_updated signal to the meter
                    if self.audio_meter and hasattr(self.audio_meter, 'update_level'):
                        print(f"[AudioService.resume_analyzer] Connecting new thread to audio meter...")
                        new_thread.level_updated.connect(self.audio_meter.update_level)
                    
                    # Replace old thread with new one
                    old_thread = self.audio_analyzer
                    self.audio_analyzer = new_thread
                    
                    # Start the new thread
                    print(f"[AudioService.resume_analyzer] Starting new thread...")
                    self.audio_analyzer.start()
                    print(f"[AudioService.resume_analyzer] ✓ New thread created and started")
                    
                    # Mark for playing
                    self.audio_analyzer.set_playing(True)
                    print(f"[AudioService.resume_analyzer] ✓ set_playing(True) called")
                    
                except Exception as e:
                    print(f"[AudioService.resume_analyzer] ❌ Error creating new thread: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                print(f"[AudioService.resume_analyzer] Thread still running, setting is_playing=True")
                self.audio_analyzer.set_playing(True)
                print(f"[AudioService.resume_analyzer] ✓ set_playing(True) called")
            
            print(f"[AudioService.resume_analyzer] ✓ EXIT")
        else:
            print(f"[AudioService.resume_analyzer] ℹ️  Audio analyzer not available, skipping")
            print(f"[AudioService.resume_analyzer] ✓ EXIT")
    
    def get_audio_analyzer(self):
        """Get the current audio analyzer thread instance"""
        return self.audio_analyzer
    
    def start_audio_monitoring(self):
        """Start monitoring audio (resume playing state) using current audio analyzer"""
        print(f"[AudioService.start_audio_monitoring] 🎙️  ENTRY")
        if self.audio_analyzer:
            print(f"[AudioService.start_audio_monitoring] Calling set_playing(True) on current audio analyzer...")
            self.audio_analyzer.set_playing(True)
            print(f"[AudioService.start_audio_monitoring] ✓ Audio monitoring started")
        else:
            print(f"[AudioService.start_audio_monitoring] ❌ Audio analyzer not available")
        print(f"[AudioService.start_audio_monitoring] ✓ EXIT")
    
    def stop_audio_monitoring(self):
        """Stop monitoring audio (pause playing state) using current audio analyzer"""
        print(f"[AudioService.stop_audio_monitoring] ⏸️  ENTRY")
        if self.audio_analyzer:
            print(f"[AudioService.stop_audio_monitoring] Calling set_playing(False) on current audio analyzer...")
            self.audio_analyzer.set_playing(False)
            print(f"[AudioService.stop_audio_monitoring] ✓ Audio monitoring stopped")
        else:
            print(f"[AudioService.stop_audio_monitoring] ❌ Audio analyzer not available")
        print(f"[AudioService.stop_audio_monitoring] ✓ EXIT")
    
    def disconnect_audio_signals(self):
        """Block audio analyzer signals to prevent interference during file loading"""
        print(f"[AudioService.disconnect_audio_signals] 🔌 ENTRY")
        if self.audio_analyzer:
            try:
                print(f"[AudioService.disconnect_audio_signals] Blocking audio analyzer signals...")
                self.audio_analyzer.blockSignals(True)
                print(f"[AudioService.disconnect_audio_signals] ✓ Signals blocked")
            except Exception as e:
                print(f"[AudioService.disconnect_audio_signals] ❌ Error: {e}")
        print(f"[AudioService.disconnect_audio_signals] ✓ EXIT")
    
    def reconnect_audio_signals(self):
        """Unblock audio analyzer signals after file loading"""
        print(f"[AudioService.reconnect_audio_signals] 🔌 ENTRY")
        if self.audio_analyzer:
            try:
                print(f"[AudioService.reconnect_audio_signals] Unblocking audio analyzer signals...")
                self.audio_analyzer.blockSignals(False)
                print(f"[AudioService.reconnect_audio_signals] ✓ Signals unblocked")
            except Exception as e:
                print(f"[AudioService.reconnect_audio_signals] ❌ Error: {e}")
        print(f"[AudioService.reconnect_audio_signals] ✓ EXIT")
    
    
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
    
    # ===== Helper Functions for Features 5, 20, 12 =====
    
    def get_file_duration(self, ffprobe_path, file_path):
        """Feature 20: Get audio/video file duration in seconds"""
        import subprocess
        import os
        import sys
        
        if not os.path.exists(file_path):
            return 0.0
        
        try:
            cmd = [ffprobe_path, "-v", "error", "-show_entries", "format=duration",
                   "-of", "default=noprint_wrappers=1:nokey=1", file_path]
            startupinfo = None
            if sys.platform == "win32":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = 0
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    startupinfo=startupinfo, text=True, timeout=3)
            return float(result.stdout.strip())
        except Exception as e:
            print(f"[AudioService.get_file_duration] Error: {e}")
            return 0.0
    
    def get_volume_adjustment_command(self, ffmpeg_path, input_file, output_file, volume_db, apply_limiter=True):
        """Feature 5: Build FFmpeg command for volume adjustment"""
        volume_filter = f"volume={volume_db}dB"
        
        if apply_limiter:
            volume_filter += ",alimiter=limit=0.95"
        
        return [ffmpeg_path, "-y", "-i", input_file, "-af", volume_filter,
                "-c:v", "copy", "-c:a", "aac", output_file]
    
    def calculate_speed_ratio(self, duration_a, duration_b):
        """Feature 12: Calculate speed ratio to match two files"""
        if duration_b == 0:
            return 1.0
        return duration_a / duration_b
    
    def get_speed_adjustment_command(self, ffmpeg_path, input_file, output_file, speed_ratio):
        """Feature 12: Build FFmpeg command for speed synchronization"""
        filter_complex = f"[0:v]setpts={1/speed_ratio}*PTS[v];[0:a]atempo={speed_ratio}[a]"
        
        return [ffmpeg_path, "-y", "-i", input_file, "-filter_complex", filter_complex,
                "-map", "[v]", "-map", "[a]", output_file]
