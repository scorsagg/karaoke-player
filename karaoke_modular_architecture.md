# Karaoke Studio Pro v3 - Modular Architecture Design

## Overview

This document outlines a complete modular architecture for Karaoke Studio Pro v3 that decouples front-end from back-end services, enabling independent development, testing, and deployment of individual features while maintaining system integration.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              KARAOKE STUDIO PRO                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                    ┌─────────────────────────────────────┐                  │
│                    │       FRONTEND LAYER                │                  │
│                    │  ┌───────────────────────────────┐  │                  │
│                    │  │    UI Components              │  │                  │
│                    │  │  ├── Audio Studio Page        │  │                  │
│                    │  │  ├── Video Studio Page        │  │                  │
│                    │  │  ├── Pitch Page               │  │                  │
│                    │  │  └── Settings Page            │  │                  │
│                    │  └───────────────────────────────┘  │                  │
│                    └─────────────────────────────────────┘                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                   ┌─────────────────────────────────────────┐                 │
│                   │     APPLICATION CONTROLLER LAYER        │                 │
│                   │  ┌─────────────────────────────────────┐  │                 │
│                   │  │    Core Application Logic           │  │                 │
│                   │  │  ├── Playback Controller            │  │                 │
│                   │  │  ├── Media Controller               │  │                 │
│                   │  │  ├── Processing Controller          │  │                 │
│                   │  │  └── Navigation Controller          │  │                 │
│                   │  └─────────────────────────────────────┘  │                 │
│                   └─────────────────────────────────────────┘                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                  ┌──────────────────────────────────────────────────┐         │
│                  │        SERVICE LAYER (INDEPENDENT MODULES)       │         │
│                  │  ┌─────────────────────────────────────────────┐  │         │
│                  │  │     Core Services                            │  │         │
│                  │  │  ├── Player Service                        │  │         │
│                  │  │  ├── Audio Service                         │  │         │
│                  │  │  ├── Download Service                      │  │         │
│                  │  │  └── File Loading Service                  │  │         │
│                  │  └─────────────────────────────────────────────┘  │         │
│                  │  ┌─────────────────────────────────────────────┐  │         │
│                  │  │     Feature Services                         │  │         │
│                  │  │  ├── Pitch Shift Service                   │  │         │
│                  │  │  ├── Speed Control Service                 │  │         │
│                  │  │  ├── Amplification Service                 │  │         │
│                  │  │  ├── Vocal Separation Service              │  │         │
│                  │  │  ├── Audio Trimming Service                │  │         │
│                  │  │  └── Format Conversion Service             │  │         │
│                  │  └─────────────────────────────────────────────┘  │         │
│                  │  ┌─────────────────────────────────────────────┐  │         │
│                  │  │     Utility Services                         │  │         │
│                  │  │  ├── Subprocess Service                    │  │         │
│                  │  │  ├── FFprobe Service                       │  │         │
│                  │  │  ├── Media Path Service                    │  │         │
│                  │  │  └── Splash Service                        │  │         │
│                  │  └─────────────────────────────────────────────┘  │         │
│                  └──────────────────────────────────────────────────┘         │
├─────────────────────────────────────────────────────────────────────────────┤
│                ┌─────────────────────────────────────────────────────────┐   │
│                │        EXTERNAL TOOLS & ENGINES                         │   │
│                │  ┌─────────────────────────────────────────────────────┐  │   │
│                │  │    Media Processing Tools                           │  │   │
│                │  │  ├── VLC (Playback)                               │  │   │
│                │  │  ├── FFmpeg (Encoding/Processing)               │  │   │
│                │  │  ├── yt-dlp (Downloads)                         │  │   │
│                │  │  ├── sounddevice (Audio Capture)                │  │   │
│                │  │  └── Demucs (Vocal Separation)                  │  │   │
│                │  └─────────────────────────────────────────────────────┘  │   │
│                └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Module Structure

### 1. Core Services (Independent)
These services provide fundamental functionality that can be used by multiple features:

#### Player Service
- VLC playback abstraction layer
- Media loading and management
- Playback control (play, pause, stop, seek)
- Audio/video synchronization
- Volume control and mute functionality

#### Audio Service  
- Real-time audio analysis
- Audio level monitoring (SPL & dBFS)
- Audio buffer management
- Audio format conversion utilities
- Audio processing pipeline coordination

#### Download Service
- YouTube URL parsing and validation
- yt-dlp integration for downloads
- Download progress tracking
- File management after download completion

#### File Loading Service
- Safe media loading with cleanup coordination
- File type detection and validation
- Media metadata extraction
- Path normalization and validation

### 2. Feature Services (Independent Modules)
Each feature is a self-contained module that can be developed, tested, and deployed independently:

#### Pitch Shift Service
- Real-time pitch shifting capabilities
- Pitch control with frequency adjustment
- Integration with audio processing pipeline
- Speed synchronization
- Note detection and display

#### Speed Control Service
- Playback speed adjustment (0.5x - 2.0x)
- Speed synchronization between audio and visual elements
- Playback timeline management
- User interface integration

#### Amplification Service
- Volume control and amplification
- Gain calculation and application
- Peak limiting for distortion prevention
- Export-time processing
- UI integration with amplification controls

#### Vocal Separation Service
- Demucs integration for vocal separation
- Model selection and configuration
- Audio stem extraction
- Music recovery and blending
- Progress tracking and error handling

#### Audio Trimming Service
- Range selection and management
- Time-based trimming operations
- Export formatting control
- Range validation and optimization

#### Format Conversion Service
- Audio/video format conversion
- Quality control settings
- Batch processing capabilities
- Progress monitoring and reporting

### 3. Utility Services (Shared Components)
These provide common functionality used across multiple modules:

#### Subprocess Service
- Hidden console subprocess execution
- UTF-8 decoding with error handling
- Process monitoring and management
- Command building utilities

#### FFprobe Service
- Media metadata extraction
- Duration, sample rate, resolution probing
- Stream type detection
- Safe default value handling

#### Media Path Service
- FFmpeg path normalization
- Export output naming
- File path validation
- Cross-platform compatibility

#### Splash Service
- Loading splash creation and teardown
- Task progress tracking
- Download status management

## Component Interfaces

### Core Service Interfaces

#### PlayerService Interface
```python
class PlayerService:
    def load_media(self, media_path: str) -> bool:
        pass
    
    def play(self) -> bool:
        pass
        
    def pause(self) -> None:
        pass
        
    def stop(self) -> None:
        pass
        
    def seek(self, position_ms: int) -> bool:
        pass
        
    def set_volume(self, volume: float) -> None:
        pass
        
    def get_duration(self) -> int:
        pass
        
    def get_position(self) -> float:
        pass
```

#### AudioService Interface  
```python
class AudioService:
    def analyze_audio(self, audio_path: str) -> dict:
        pass
        
    def monitor_levels(self, callback: callable) -> None:
        pass
        
    def set_calibration_mode(self, mode: str) -> None:
        pass
```

### Feature Service Interfaces

#### PitchShiftService Interface
```python
class PitchShiftService:
    def apply_pitch_shift(self, input_path: str, output_path: str, 
                         pitch_semitones: float) -> bool:
        pass
        
    def get_supported_models(self) -> list:
        pass
        
    def set_realtime_mode(self, enabled: bool) -> None:
        pass
```

#### AmplificationService Interface
```python
class AmplificationService:
    def apply_amplification(self, input_path: str, output_path: str, 
                          gain_factor: float) -> bool:
        pass
        
    def set_amplification_mode(self, mode: str) -> None:
        pass
        
    def get_peak_level(self) -> float:
        pass
```

## Module Dependencies

### Service Layer Dependencies
```
Service Dependencies:
┌─────────────────┬───────────────────────┬───────────────────────┐
│ Service         │ Depends On            │ Used By               │
├─────────────────┼───────────────────────┼───────────────────────┤
│ PlayerService   │ -                     │ All Feature Services  │
│ AudioService    │ PlayerService         │ All Feature Services  │
│ DownloadService │ SubprocessService     │ Media Controller      │
│ FileLoadingService│ -                   │ Media Controller      │
│ PitchShiftService│ PlayerService,       │ Pitch Page            │
│                 │ AudioService          │                       │
│ SpeedControlService│ PlayerService      │ Playback Controller   │
│ AmplificationService│ PlayerService,    │ Convert & Export Page │
│                 │ AudioService          │                       │
│ VocalSeparationService│ SubprocessService,│ Convert & Export Page │
│                 │ FFprobeService        │                       │
│ AudioTrimmingService│ PlayerService,     │ Audio Studio Page     │
│                 │ AudioService          │                       │
│ FormatConversionService│ SubprocessService,│ Convert & Export Page │
│                 │ FFprobeService        │                       │
└─────────────────┴───────────────────────┴───────────────────────┘
```

## Benefits of This Architecture

### 1. **Independent Development**
- Each feature service can be developed and tested separately
- Teams can work on different modules without affecting others
- Feature-specific requirements can be implemented independently

### 2. **Easy Maintenance**
- Changes to one feature don't impact other features
- Bug fixes are localized to specific services
- Documentation and testing are modular

### 3. **Scalability**
- New features can be added by implementing new service interfaces
- Existing services can be enhanced without breaking existing functionality
- Feature dependencies are clearly defined

### 4. **Testability**
- Each service can be unit tested independently
- Mock services can be created for integration testing
- End-to-end testing remains possible

### 5. **Flexibility**
- Features can be enabled/disabled based on configuration
- Different implementations of the same interface can be swapped
- Versioning and compatibility management becomes easier

## Implementation Roadmap

### Phase 1: Core Service Layer
1. Create independent service interfaces
2. Implement PlayerService, AudioService, DownloadService
3. Implement FileLoadingService with proper cleanup
4. Establish common utility services

### Phase 2: Feature Services
1. Implement PitchShiftService
2. Implement SpeedControlService  
3. Implement AmplificationService
4. Implement VocalSeparationService
5. Implement AudioTrimmingService
6. Implement FormatConversionService

### Phase 3: Integration
1. Update controllers to use new service interfaces
2. Refactor UI components to work with modular services
3. Ensure all feature dependencies are properly connected
4. Test complete integration

## Configuration Management

The architecture supports different configuration options:

### Feature Enable/Disable
```yaml
# config/features.yaml
pitch_shift:
  enabled: true
  default_model: "htdemucs_ft"
  
amplification:
  enabled: true
  default_mode: "dB_output"
  
vocal_separation:
  enabled: true
  default_backend: "demucs"
  
speed_control:
  enabled: true
```

### Service Configuration
```yaml
# config/services.yaml
player_service:
  vlc_path: "/usr/bin/vlc"
  audio_device: "default"

audio_service:
  sampling_rate: 44100
  buffer_size: 1024

download_service:
  yt_dlp_path: "/usr/bin/yt-dlp"
  download_dir: "./downloads"
```

This modular architecture ensures that each component can be developed, tested, and deployed independently while maintaining full system integration. It provides the flexibility needed to add new features or modify existing ones without affecting other parts of the application.