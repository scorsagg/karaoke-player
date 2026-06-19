"""File loading service - coordinates safe file loading with audio analyzer state management"""

import os
import time
from PySide6.QtWidgets import QApplication


class FileLoadingService:
    """
    Manages safe file loading by coordinating with audio analyzer state.
    Ensures all file loading operations go through a single, thread-safe point.
    """
    
    def __init__(self, audio_service, player_service):
        """
        Args:
            audio_service: AudioService instance for managing audio analyzer
            player_service: PlayerService instance for loading media
        """
        self.audio_service = audio_service
        self.player_service = player_service
        self.is_loading = False
        self.pending_load_path = None
    
    def is_currently_loading(self):
        """Check if a file is currently being loaded"""
        return self.is_loading
    
    def prepare_for_loading(self):
        """
        Prepare for file loading by safely pausing audio analyzer.
        
        Logic:
        1. Check if a file is already loaded/active
        2. If YES: Stop the player + audio analyzer using stop() commands
        3. If NO: Skip to just pausing audio
        4. Block signals and wait for cleanup
        
        Returns:
            bool: True if audio analyzer was playing before pause
        """
        print(f"\n[FileLoadingService.prepare_for_loading] 🔵 ENTRY (is_loading={self.is_loading})")
        
        # Prevent overlapping loads
        if self.is_loading:
            print("⚠️  Load already in progress, skipping")
            return False
        
        self.is_loading = True
        print(f"[FileLoadingService] ✓ Set is_loading=True")
        
        # Block all audio analyzer signals FIRST to prevent any signal processing during file load
        print(f"[FileLoadingService] 🔌 Blocking audio signals...")
        self.audio_service.disconnect_audio_signals()
        print(f"[FileLoadingService] ✓ Audio signals blocked")
        
        # STEP 1: Check if a file is currently loaded/active
        print(f"[FileLoadingService] 🔍 Checking if file is currently loaded/active...")
        is_file_loaded = self.player_service.is_active()
        print(f"[FileLoadingService] → Player is_active={is_file_loaded}")
        
        # STEP 2: If file is loaded, stop it completely
        if is_file_loaded:
            print(f"[FileLoadingService] ⚠️  File IS loaded/active - stopping it completely...")
            
            # First, check if it's PLAYING (not just paused)
            is_currently_playing = self.player_service.is_playing()
            print(f"[FileLoadingService] → Player is_playing={is_currently_playing}")
            
            # If playing, PAUSE first to stop the decoder thread
            if is_currently_playing:
                print(f"[FileLoadingService] ⏸️  Pausing player (stops decoder thread)...")
                self.player_service.pause()
                print(f"[FileLoadingService] ✓ Player paused")
                
                # Wait for pause to take effect
                print(f"[FileLoadingService] ⏱️  Waiting 1.0s for pause to complete...")
                time.sleep(1.0)
                print(f"[FileLoadingService] ✓ Pause complete")
            
            # Stop audio analyzer thread (closes InputStream context)
            print(f"[FileLoadingService] 🛑 Stopping audio analyzer thread (calls stop())...")
            was_playing = self.audio_service.pause_analyzer()
            print(f"[FileLoadingService] ✓ Audio analyzer stopped (was_playing={was_playing})")
            
            # Don't call stop() - VLC hangs on it with active decoder threads
            # Just set media to None to release current resources
            print(f"[FileLoadingService] 🗑️  Releasing player resources (without calling stop)...")
            try:
                # Release media reference (VLC will handle cleanup automatically)
                self.player_service._media = None
                print(f"[FileLoadingService] ✓ Media reference released")
            except Exception as e:
                print(f"[FileLoadingService] ⚠️  Error releasing media: {e}")
            
            # Final wait
            print(f"[FileLoadingService] ⏱️  Waiting 0.5s for cleanup...")
            time.sleep(0.5)
            print(f"[FileLoadingService] ✓ Resource cleanup complete")
        
        else:
            print(f"[FileLoadingService] ℹ️  NO file loaded - just pausing audio analyzer...")
            
            # Just pause audio, don't need to stop player
            print(f"[FileLoadingService] ⏸️  Pausing audio analyzer...")
            was_playing = self.audio_service.pause_analyzer()
            print(f"[FileLoadingService] ✓ Audio analyzer paused (was_playing={was_playing})")
        
        print(f"[FileLoadingService] ✓ prepare_for_loading() complete")
        return was_playing
    
    def finish_loading(self, resume_audio=True):
        """
        Finish file loading and optionally resume audio analyzer.
        
        Args:
            resume_audio: bool - Whether to resume audio analyzer after loading
        """
        print(f"\n[FileLoadingService.finish_loading] 🟢 ENTRY (resume_audio={resume_audio})")
        
        if resume_audio:
            print(f"[FileLoadingService] ▶️  Resuming audio analyzer...")
            self.audio_service.resume_analyzer()
            print(f"[FileLoadingService] ✓ Audio analyzer resumed")
        else:
            print(f"[FileLoadingService] ℹ️  Skipping audio resume (resume_audio=False)")
        
        # Reconnect audio analyzer signals now that file loading is complete
        print(f"[FileLoadingService] 🔌 Reconnecting audio signals...")
        self.audio_service.reconnect_audio_signals()
        print(f"[FileLoadingService] ✓ Audio signals reconnected")
        
        self.is_loading = False
        print(f"[FileLoadingService] ✓ Set is_loading=False")
        
        # Process any pending events
        print(f"[FileLoadingService] 📤 Processing pending events...")
        QApplication.processEvents()
        print(f"[FileLoadingService] ✓ finish_loading() complete\n")
    
    def safe_load_video(self, player_load_callback, file_path):
        """
        Safely load a video file with proper state management.
        
        Args:
            player_load_callback: Callable that performs the actual load (from main.py)
            file_path: Path to file to load
        
        Returns:
            bool: True if load succeeded, False otherwise
        """
        try:
            was_playing = self.prepare_for_loading()
            
            # Call the actual load callback
            player_load_callback(file_path)
            
            # Resume audio after successful load
            self.finish_loading(resume_audio=was_playing)
            
            return True
        except Exception as e:
            print(f"Error in safe file loading: {e}")
            self.is_loading = False
            return False
