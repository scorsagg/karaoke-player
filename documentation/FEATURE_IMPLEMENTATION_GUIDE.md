# Karaoke Application - Feature Implementation Guide
**Status:** Planning & Documentation  
**Date:** 2026-06-20  
**Priority:** Medium & High Impact Features

---

## Table of Contents
1. [Core Audio Features](#core-audio-features)
2. [Video Processing Features](#video-processing-features)
3. [Audio-Video Synchronization](#audio-video-synchronization)
4. [File Management & Conversion](#file-management--conversion)
5. [Analysis & Detection](#analysis--detection)
6. [Advanced Features](#advanced-features)
7. [Implementation Priorities](#implementation-priorities)

---

## Core Audio Features

### Feature 1: Pitch/Key Adjustment (Semitone Shifting)
**Priority:** HIGH  
**Difficulty:** Medium  
**Status:** Ready to implement

**Purpose:** Allow users to adjust vocal pitch by semitones without changing tempo

**Semitone Reference Table:**
```
-1 semitone:   asetrate=44100*0.94387,  atempo=1.05946
-2 semitones:  asetrate=44100*0.89,     atempo=1.125
-2.5 semitones: asetrate=44100*0.8715,  atempo=1.15
-2.7 semitones: asetrate=44100*0.8464,  atempo=1.181  (Surendra's range)
-3 semitones:  asetrate=44100*0.8342,   atempo=1.2    (Anita's range)
-4 semitones:  asetrate=44100*0.7937,   atempo=1.26
```

**FFmpeg Command:**
```bash
ffmpeg -i input_audio.wav -filter:a "asetrate=44100*RATE_FACTOR,atempo=TEMPO_FACTOR" output_audio.wav
```

**Real-World Examples:**
```bash
# Extract audio first
ffmpeg -i "extracted_audio.wav" -filter:a "asetrate=44100*0.94387,atempo=1.05946" "output_audio-1.wav"  # -1 semitone

# -2 semitones for Srikanth
ffmpeg -i "extracted_audio.wav" -filter:a "asetrate=44100*0.89,atempo=1.125" "output_audio-2.wav"

# -3 semitones for Anita
ffmpeg -i "extracted_audio.wav" -filter:a "asetrate=44100*0.8342,atempo=1.2" "output_audio-3.wav"

# -2.7 semitones for Surendra
ffmpeg -i "extracted_audio.wav" -filter:a "asetrate=44100*0.8464,atempo=1.181" "output_audio-2.7.wav"
```

**Application Integration:**
- UI Slider: -4 to +4 semitones (calculate rate/tempo factors)
- Store adjustment in settings
- Apply during playback or export

**Better Approaches:**
- Consider using librubberband filter (if available) for higher quality: `-af "rubberband=pitch=SEMITONES"`
- Alternative: Use `asetrate` with pitch shifting library (SoX/librubberband)
- Limitation: asetrate method has timbral distortion at extreme values

---

### Feature 2: Tempo/Speed Adjustment
**Priority:** HIGH  
**Difficulty:** Low  
**Status:** Ready to implement

**Purpose:** Speed up or slow down audio independently of pitch

**FFmpeg Command:**
```bash
ffmpeg -i input_audio.wav -filter:a "atempo=FACTOR" output_audio.wav
```

**Common Factors:**
- 0.8333x (slow down ~20%)
- 1.05x (speed up ~5%)
- 1.125x (speed up ~12.5%)
- 1.2x (speed up ~20%)
- 2.0x (double speed)

**Real-World Examples:**
```bash
# Speed up video by 1.125x (audio and video together)
ffmpeg -i "Bhanware Ki Gunjan Hai Mera Dil-karaoke-org.mp4" \
  -filter_complex "[0:v]setpts=1/1.125*PTS[v];[0:a]atempo=1.125[a]" \
  -map "[v]" -map "[a]" "Bhanware Ki Gunjan Hai Mera Dil-karaoke-org-tempo.mp4"

# Speed up video by 2x
ffmpeg -i "Kiska Rasta Dekhe Karaoke.mp4" \
  -filter_complex "[0:v]setpts=0.5*PTS[v];[0:a]atempo=2.0[a]" \
  -map "[v]" -map "[a]" "Kiska Rasta Dekhe Karaoke-tempo.mp4"

# Only audio tempo (no video change)
ffmpeg -i input_audio.wav -filter:a "atempo=1.05" output_audio.wav
```

**Limitations:**
- atempo filter accuracy: 0.5x to 2.0x range recommended
- Below 0.5x or above 2.0x requires multiple passes or alternative method

**Better Approaches:**
- Use `librubberband` filter for better quality: `-af "rubberband=tempo=FACTOR"`
- For extreme speeds, chain multiple passes: `atempo=1.5,atempo=1.5` = 2.25x

---

### Feature 3: Combined Pitch-Tempo Adjustment
**Priority:** HIGH  
**Difficulty:** Medium  
**Status:** Ready to implement

**Purpose:** Apply pitch shift AND tempo adjustment simultaneously

**Method 1: Basic Combined (asetrate + atempo):**
```bash
ffmpeg -i input_audio.wav -filter:a "asetrate=44100*RATE_FACTOR,atempo=TEMPO_FACTOR" output_audio.wav
```

**Real Example (Video with pitch + tempo):**
```bash
ffmpeg -i "Baadi Hoda Balli Inda-org.mp4" -filter_complex "[0:v]setpts=PTS/0.97[v];[0:a]asetrate=44100*1.05946,aresample=44100[a]" -map "[v]" -map "[a]" output.mp4
```

**Method 2: Professional (Using Rubberband + setpts):**
```bash
ffmpeg -i "Baadi Hoda Balli Inda-org.mp4" -filter_complex "[0:a]rubberband=pitch=0.943874,atempo=0.97[a];[0:v]setpts=PTS/0.97[v]" -map "[v]" -map "[a]" output.mp4
```

**Use Cases:**
- Match vocal lines to different karaoke tracks
- Transpose while maintaining original timing
- Create custom versions in different keys

**Implementation Note:**
- For video+audio: Use filter_complex with both [0:v] and [0:a]
- Order matters: asetrate → atempo → aresample (for best results)
- Rubberband provides better quality but slower processing

**Better Method - Using Rubberband Filter (Higher Quality):**
```bash
# Pitch shift with tempo adjustment using rubberband
ffmpeg -i "Baadi Hoda Balli Inda-org.mp4" \
  -filter_complex "[0:a]rubberband=pitch=0.943874,atempo=0.97[a];[0:v]setpts=PTS/0.97[v]" \
  -map "[v]" -map "[a]" output.mp4
```

**Rubberband Parameters:**
- `pitch`: Pitch shift factor (0.5 to 2.0)
  - 0.943874 ≈ -1 semitone
  - 0.89 ≈ -2 semitones
  - 0.84 ≈ -2.5 semitones
- `atempo`: Tempo factor for audio-video sync

---

### Feature 4: Audio Loudness Normalization
**Priority:** HIGH  
**Difficulty:** Low  
**Status:** Ready to implement

**Purpose:** Normalize audio levels to consistent volume across tracks

**FFmpeg Commands:**

**Basic Normalization:**
```bash
ffmpeg -i input.wav -filter:a loudnorm -c:v copy output.wav
```

**Advanced (EBU R128 Standard):**
```bash
ffmpeg -i input.wav -af "loudnorm=I=-14:LRA=11:tp=-1.5" output.wav
```

**Parameters:**
- `I`: Integrated loudness target (LUFS) - default -23
- `LRA`: Loudness Range (dB) - default 7
- `tp`: True Peak limit (dBFS) - default -2

**For Video:**
```bash
ffmpeg -i input.mp4 -filter:a "loudnorm=I=-14:LRA=11:tp=-1.5" -c:v copy output.mp4
```

**Better Approaches:**
- Two-pass analysis for better accuracy: `loudnorm=print_format=json` (first pass), then apply normalization (second pass)
- For WhatsApp compliance: Use `I=-16:LRA=11:tp=-1.5`

---

### Feature 5: Volume/Amplitude Control
**Priority:** MEDIUM  
**Difficulty:** Low  
**Status:** Ready to implement

**Purpose:** Increase or decrease audio volume

**FFmpeg Commands:**

**Using dB (Decibels):**
```bash
ffmpeg -i input.mp3 -af "volume=5dB" output.mp3
```

**Using Multiplier:**
```bash
ffmpeg -i input.mp3 -af "volume=2" output.mp3  # Double
ffmpeg -i input.mp3 -af "volume=0.5" output.mp3  # Half
```

**For Video with Volume Amplification:**
```bash
ffmpeg -i input.mp4 -af "volume=5dB" -c:v copy output.mp4
```

**With Audio Limiter (Prevent Clipping):**
```bash
ffmpeg -i input.mp4 -af "volume=5dB,alimiter=limit=0.95" -c:v copy output.mp4
```

**Conversion:**
- 1x volume = 0dB
- 2x volume ≈ 6dB
- 3x volume ≈ 9.5dB

---

### Feature 6: Audio Trimming/Seeking
**Priority:** MEDIUM  
**Difficulty:** Low  
**Status:** Ready to implement

**Purpose:** Remove first N seconds from audio (useful for removing intros, silence, or intro music)

**Basic FFmpeg Command:**
```bash
ffmpeg -y -ss SECONDS -i input.mp3 -acodec copy output.mp3
```

**Real Examples from Project:**
```bash
ffmpeg -y -ss 3.5 -i "slowed_Babu Samjho Ishare-karaoke-session.mp3" \
        -acodec copy "Babu Samjho Ishare-karaoke-session_slowed.mp3"
```

**More Trimming Examples:**
```bash
# Remove first 10 seconds
ffmpeg -y -ss 10.0 -i "audio.wav" -acodec copy "audio_trimmed.wav"

# Remove first 3.5 seconds from MP3
ffmpeg -y -ss 3.5 -i "audio.mp3" -acodec copy "audio_trimmed.mp3"

# Remove first 1 minute and 30 seconds (HH:MM:SS format)
ffmpeg -y -ss 00:01:30 -i "audio.mp3" -acodec copy "audio_trimmed.mp3"
```

**Parameters:**
- `-ss`: Seek/start position (format: HH:MM:SS or decimal seconds)
  - `3.5` = 3.5 seconds
  - `00:01:30` = 1 minute 30 seconds
- `-y`: Overwrite output file without asking
- `-acodec copy`: Fast trimming without re-encoding (no quality loss)

**Use Cases:**
- Remove intro music before singing starts
- Trim silence from beginning
- Remove countdown or introduction

**Processing Speed:** ~1-2 seconds for entire file (extremely fast because no re-encoding)

---

### Feature 7: Audio Format Conversion
**Priority:** MEDIUM  
**Difficulty:** Low  
**Status:** Ready to implement

**Purpose:** Convert between MP3, WAV, DAT formats

**WAV to MP3:**
```bash
ffmpeg -i input.wav -q:a 0 output.mp3
```

**MP3 to WAV:**
```bash
ffmpeg -i input.mp3 output.wav
```

**DAT to MP3:**
```bash
ffmpeg -i input.dat -vn -ar 44100 -ac 2 -b:a 192k output.mp3
```

**DAT to WAV:**
```bash
ffmpeg -i input.dat -vn -ar 44100 -ac 2 output.wav
```

**Parameters:**
- `-vn`: No video stream
- `-ar 44100`: Sample rate (44.1 kHz = CD quality)
- `-ac 2`: Audio channels (stereo)
- `-b:a 192k`: Audio bitrate
- `-q:a 0`: Highest quality

**Better Approaches:**
- For lossless preservation: Always use WAV as intermediate format
- For distribution: MP3 with `-q:a 0` or `-b:a 320k`

---

### Feature 8: Mono Conversion
**Priority:** LOW  
**Difficulty:** Low  
**Status:** Ready to implement

**Purpose:** Convert stereo to mono (for analysis or simpler processing)

**FFmpeg Command:**
```bash
ffmpeg -i input.wav -ac 1 output_mono.wav
```

**Parameters:**
- `-ac 1`: Set audio channels to 1 (mono)

---

## Video Processing Features

### Feature 9: Video Speed Adjustment (Independent from Audio)
**Priority:** MEDIUM  
**Difficulty:** Medium  
**Status:** Ready to implement

**Purpose:** Speed up/slow down video without affecting audio

**FFmpeg Command:**
```bash
ffmpeg -i input.mp4 -filter_complex "[0:v]setpts=FACTOR*PTS[v];[0:a]atempo=1.0[a]" -map "[v]" -map "[a]" output.mp4
```

**Examples:**
```bash
# Slow down video to 0.5x (keep audio at 1x)
ffmpeg -i input.mp4 -filter_complex "[0:v]setpts=2.0*PTS[v];[0:a]atempo=1.0[a]" -map "[v]" -map "[a]" output.mp4

# Speed up video to 1.5x (keep audio at 1x)
ffmpeg -i input.mp4 -filter_complex "[0:v]setpts=0.667*PTS[v];[0:a]atempo=1.0[a]" -map "[v]" -map "[a]" output.mp4
```

**Parameter Formula:**
- Video speed factor = 1 / tempo_factor
- To slow 1.125x tempo → video setpts = 1/1.125 = 0.8889

---

### Feature 10: Subtitle Burning/Embedding
**Priority:** LOW  
**Difficulty:** Low  
**Status:** Ready to implement

**Purpose:** Permanently embed SRT subtitle files into video

**FFmpeg Command:**
```bash
ffmpeg -i input.mp4 -vf subtitles=transliterated_lyrics.srt -c:a copy output.mp4
```

**Requirements:**
- SRT subtitle file must exist in accessible path
- FFmpeg compiled with libass support (standard)

---

### Feature 11: Vertical to Horizontal Video Conversion
**Priority:** LOW  
**Difficulty:** Medium  
**Status:** Ready to implement

**Purpose:** Convert phone-recorded vertical videos to standard 16:9 format

**FFmpeg Command:**
```bash
ffmpeg -i vertical_input.mp4 \
  -vf "crop=in_w:in_h*0.3:0:in_h*0.2,scale=1920*1.1:1080*1.1:force_original_aspect_ratio=increase,crop=1920:1080" \
  -c:a copy horizontal_output.mp4
```

**Better Approaches:**

**Option A: Center Crop with Blur Background**
```bash
ffmpeg -i vertical.mp4 -vf "[0:v]scale=1080:-1,pad=1920:1080:(1920-1080)/2:(1080-ih)/2:black[v]" -map "[v]" -c:a copy output.mp4
```

**Option B: Smart Scaling (Original Aspect Preserved)**
```bash
ffmpeg -i vertical.mp4 -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(1920-iw)/2:(1080-ih)/2" -c:a copy output.mp4
```

---

## Audio-Video Synchronization

### Feature 12: Duration Matching & Speed Synchronization
**Priority:** HIGH  
**Difficulty:** Medium  
**Status:** Ready to implement

**Purpose:** Match video and audio speeds to ensure perfect synchronization

**3-Step Process:**

**Step 1: Get Duration of Both Files**
```bash
ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "file1.mp4"
ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "file2.mp4"
```

**Step 2: Calculate Speed Ratio**
```
Speed ratio = Duration_A / Duration_B

Real Examples:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Example 1: Meet Na Mila Re Mann Ka
- Video file: 244.622222 seconds (faster)
- DAT file:   295.291396 seconds (slower)
- Ratio: 244.622222 / 295.291396 = 0.829 (need to slow DAT)

Example 2: Babu Samjho Ishare
- Org file:     290.017234 seconds (faster)
- Karaoke file: 298.972792 seconds (slower)
- Ratio: 290.017234 / 298.972792 = 0.9700 (need to slow karaoke file)

Example 3: Meet Na Mila Re Mann Ka Karaoke
- Source karaoke: 295.288163 seconds
- Target video:   244.622222 seconds
- Ratio: 244.622222 / 295.288163 = 0.829 (slow down by 17%)
```

**Step 3: Adjust Speed with FFmpeg**
```bash
# Real example: Slow down Babu Samjho Ishare karaoke to match original
ffmpeg -i "Babu Samjho Ishare-karaoke-session.mp4" \
  -filter_complex "[0:v]setpts=1/0.9700*PTS[v];[0:a]atempo=0.9700[a]" \
  -map "[v]" -map "[a]" "Babu Samjho Ishare-karaoke-session_slowed.mp4"

# Alternative: Speed up the slower one instead
ffmpeg -i input1.mp4 \
  -filter_complex "[0:v]setpts=0.8333*PTS[v];[0:a]atempo=1.2[a]" \
  -map "[v]" -map "[a]" output1_faster.mp4
```

**Verification:**
```bash
# Confirm final durations match
ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "Babu Samjho Ishare-karaoke-session_slowed.mp4"
```

---

### Feature 13: Multi-Audio Track Mixing
**Priority:** MEDIUM  
**Difficulty:** Medium  
**Status:** Ready to implement

**Purpose:** Mix multiple audio tracks with duration control

**FFmpeg Command:**
```bash
ffmpeg -i video.mp4 -i vocals.wav \
  -filter_complex "[0:a][1:a]amix=inputs=2:duration=shortest[a]" \
  -map 0:v -map "[a]" -c:v copy -c:a aac output.mp4
```

**Parameters:**
- `inputs=2`: Number of audio tracks to mix
- `duration=shortest`: Match duration to shortest input
- `duration=longest`: Match duration to longest input
- `duration=first`: Match duration to first input

**For 3+ Audio Tracks:**
```bash
ffmpeg -i video.mp4 -i vocals.wav -i background.wav \
  -filter_complex "[0:a][1:a][2:a]amix=inputs=3:duration=first[a]" \
  -map 0:v -map "[a]" -c:v copy output.mp4
```

---

### Feature 14: Karaoke Video Creation (Video + Different Audio)
**Priority:** HIGH  
**Difficulty:** Low  
**Status:** Ready to implement

**Purpose:** Replace original video's audio with different audio track (e.g., instrumental version)

**Basic Command (Fast - No Re-encoding):**
```bash
ffmpeg -i video.mp4 -i instrumental_audio.mp3 \
  -c:v copy -map 0:v:0 -map 1:a:0 output.mp4
```

**Real Example from Project:**
```bash
ffmpeg -i "Vishwanathanu thandeyadare_down2.mp4" \
        -i "Vishwanathanu tandeyaadare_down2-karaoke2.mp3" \
        -c:v copy -map 0:v:0 -map 1:a:0 "Vishwanathanu tandeyaadare_down2-karaoke.mp4"
```

**Another Example:**
```bash
ffmpeg -i "Dekha Na Haye Re Socha Na Haye Re-org.mp4" \
        -i "Dekha Na Haye Re Socha Na Haye Re-org-other.mp3" \
        -c:v copy -map 0:v:0 -map 1:a:0 "Dekha Na Haye Re Socha Na Haye Re-karaoke.mp4"
```

**Parameters:**
- `-c:v copy`: Copy video codec (fast, no re-encoding) ← IMPORTANT for speed
- `-map 0:v:0`: Use first video stream from first input (video file)
- `-map 1:a:0`: Use first audio stream from second input (audio file)

**Processing Speed:** ~5-10 minutes for a 2-hour video (very fast because no re-encoding)

**Use Case:**
- Replace original vocals with karaoke instrumental version
- Combine video from one source with audio from another
- Create custom versions without re-encoding video

**Real-World Examples:**
```bash
# Replace original video audio with karaoke audio
ffmpeg -i "Vishwanathanu thandeyadare_down2.mp4" \
  -i "Vishwanathanu tandeyaadare_down2-karaoke2.mp3" \
  -c:v copy -map 0:v:0 -map 1:a:0 "Vishwanathanu tandeyaadare_down2-karaoke.mp4"

# Use instrumental track with original video
ffmpeg -i "Dekha Na Haye Re Socha Na Haye Re-org.mp4" \
  -i "Dekha Na Haye Re Socha Na Haye Re-org-other.mp3" \
  -c:v copy -map 0:v:0 -map 1:a:0 "Dekha Na Haye Re Socha Na Haye Re-karaoke.mp4"
```

---

## File Management & Conversion

### Feature 15: Audio Extraction from Video
**Priority:** HIGH  
**Difficulty:** Low  
**Status:** Ready to implement

**Purpose:** Extract audio from video files to WAV/MP3 format

**FFmpeg Commands:**

**Extract to WAV (High Quality):**
```bash
ffmpeg -i video.mp4 -q:a 0 -map a output_audio.wav
```

**Extract to MP3:**
```bash
ffmpeg -i video.mp4 -q:a 0 -map a output_audio.mp3
```

**Parameters:**
- `-q:a 0`: Highest audio quality
- `-map a`: Extract only audio streams
- `-ar 44100`: Set sample rate to 44.1 kHz (optional)

---

### Feature 16: File Concatenation/Merging
**Priority:** MEDIUM  
**Difficulty:** Low  
**Status:** Ready to implement

**Purpose:** Combine multiple video/audio files into one (for medleys)

**Step 1: Create Playlist File (parts.txt)**
```
file 'song1.mp4'
file 'song2.mp4'
file 'song3.mp4'
```

**Step 2: Merge with FFmpeg**
```bash
ffmpeg -f concat -safe 0 -i parts.txt -c copy output.mp4
```

**Parameters:**
- `-f concat`: Use concat demuxer
- `-safe 0`: Allow absolute paths
- `-c copy`: Copy codecs (fast, no re-encoding)

**Better Approaches:**
- Pre-ensure all files have identical codec parameters
- Use `-safe 1` with relative paths for security

---

### Feature 17: Background Image Overlay
**Priority:** LOW  
**Difficulty:** Medium  
**Status:** Ready to implement

**Purpose:** Add background images with configurable transparency/positioning

**Basic Overlay with Transparency:**
```bash
ffmpeg -i video.mp4 -i background.jpg \
  -filter_complex "[1:v]scale=-1:150,format=rgba,colorchannelmixer=aa=0.7[bg];[0:v][bg]overlay=W-w:(H-h)/2" \
  -c:a copy output.mp4
```

**Parameters:**
- `scale=-1:150`: Scale height to 150px, maintain aspect ratio
- `format=rgba`: Convert to RGBA (for transparency)
- `colorchannelmixer=aa=0.7`: 70% opacity (0.0-1.0)
- `overlay=W-w:(H-h)/2`: Position right-center

**Alternative Positions:**
```
overlay=0:0           # Top-left corner
overlay=W-w:0         # Top-right corner
overlay=0:H-h         # Bottom-left corner
overlay=W-w:H-h       # Bottom-right corner
overlay=(W-w)/2:(H-h)/2  # Center
```

---

### Feature 18: Platform Codec Optimization (WhatsApp)
**Priority:** MEDIUM  
**Difficulty:** Low  
**Status:** Ready to implement

**Purpose:** Convert video codecs for specific platforms

**WhatsApp Optimization:**
```bash
ffmpeg -i input.mp4 \
  -r 30 -ar 48000 \
  -c:v libx264 -preset fast -crf 23 \
  -c:a aac -b:a 192k \
  output.mp4
```

**Parameters:**
- `-r 30`: Frame rate 30 fps (WhatsApp max)
- `-ar 48000`: Audio sample rate 48 kHz
- `-c:v libx264`: Video codec H.264
- `-preset fast`: Encoding speed (ultrafast, superfast, fast, medium, slow, slower)
- `-crf 23`: Quality (0-51, lower is better, 23 is default)
- `-c:a aac`: Audio codec
- `-b:a 192k`: Audio bitrate

---

## File Format Conversion

### Feature 19: DAT File Conversion
**Priority:** MEDIUM  
**Difficulty:** Low  
**Status:** Ready to implement

**Purpose:** Convert .dat files (common in karaoke machines, WhatsApp backups) to standard formats

**Step 1: Detect Codec First (Optional but Recommended)**
```bash
ffprobe input.dat
```
Look for output like:
- `Audio: opus` → Rename to .opus first
- `Audio: aac` → Rename to .aac first
- `Audio: amr-nb` → Rename to .amr first
- `Video: h264` → Video file, rename to .mp4

**Audio DAT to MP3:**
```bash
ffmpeg -i input.dat -acodec libmp3lame -b:a 192k output.mp3
```

**Audio DAT to WAV:**
```bash
ffmpeg -i input.dat -vn -ar 44100 -ac 2 output.wav
```

**Video DAT to MP4 (Fast - No Re-encoding):**
```bash
ffmpeg -i input.dat -c:v copy -c:a copy output.mp4
```

**Video DAT to MP4 (Full Re-encode if needed):**
```bash
ffmpeg -i input.dat -c:v libx264 -c:a aac output.mp4
```

**Parameters:**
- `-vn`: No video stream (audio only)
- `-ar 44100`: Sample rate 44.1 kHz (CD quality)
- `-ac 2`: Audio channels (2 = stereo)
- `-b:a 192k`: Audio bitrate (for MP3)
- `-acodec libmp3lame`: MP3 encoder (better quality than default)
- `-c:v copy`: Copy video codec without re-encoding (fast)
- `-c:a copy`: Copy audio codec without re-encoding (fast)

**Batch Convert ALL .dat Files in a Folder (Windows):**

Create file: `convert_dat.bat`
```batch
for %%a in (*.dat) do ffmpeg -i "%%a" -acodec libmp3lame -b:a 192k "%%~na.mp3"
```
Run it → converts all .dat to .mp3

**Real World Example (Batch Video Conversion):**
```batch
for %%a in (*.dat) do ffmpeg -i "%%a" -c:v copy -c:a copy "%%~na.mp4"
```

**Note:** Most WhatsApp `.dat` files are actually H.264 + AAC video, so video conversion method works best

---

## Analysis & Detection

### Feature 20: Audio Duration Analysis
**Priority:** MEDIUM  
**Difficulty:** Low  
**Status:** Ready to implement

**Purpose:** Get duration of audio/video files for synchronization calculations

**FFprobe Command:**
```bash
ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "input.mp4"
```

**Output:** Single number representing duration in seconds (e.g., 245.123456)

**Python Integration:**
```python
import subprocess

def get_duration(file_path):
    result = subprocess.run([
        'ffprobe', '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        file_path
    ], capture_output=True, text=True)
    return float(result.stdout.strip())
```

---

### Feature 21: BPM/Tempo Detection (Foundation)
**Priority:** LOW  
**Difficulty:** High  
**Status:** Research needed

**Purpose:** Detect BPM of songs for automatic tempo recommendations

**Preparation (Convert for Analysis):**
```bash
ffmpeg -i input.mp3 -ac 1 -ar 44100 analysis_audio.wav
```

**Better Approaches:**
- Use Python librosa library: `librosa.beat.tempo()`
- Use Essentia library (more accurate)
- Consider using external BPM detection service for heavy lifting

---

## Advanced Features

### Feature 22: Vocal Separation
**Priority:** LOW  
**Difficulty:** Very High  
**Status:** External tool required

**Purpose:** Extract vocals from mixed tracks

**Recommended Tools:**
1. **VoiceSeparator (Python)**: `voice-separator` package
2. **Spleeter (Spotify)**: Best quality, requires TensorFlow
3. **UVR (Ultimate Vocal Remover)**: GUI-based, high quality

**Python Integration Example:**
```python
from voice_separator.separator import Separator

separator = Separator("model_vocals_dereverb.pkl")
separator.separate(audio_file_path, output_dir)
```

---

### Feature 23: Audio Limiter (Prevent Clipping)
**Priority:** MEDIUM  
**Difficulty:** Low  
**Status:** Ready to implement

**Purpose:** Prevent audio distortion when amplifying

**FFmpeg Command:**
```bash
ffmpeg -i input.mp4 -af "volume=5dB,alimiter=limit=0.95" -c:v copy output.mp4
```

**Limiter Parameters:**
- `limit=0.95`: Threshold at 95% of max (prevents clipping at 100%)
- `attack=20`: Attack time in milliseconds
- `release=200`: Release time in milliseconds
- `hold=100`: Hold time in milliseconds

---

## Implementation Priorities

### Phase 1: Core Functionality (Essential for MVP)
**Timeline:** 1-2 weeks

```
Priority 1 (Complete First):
1. Pitch/Key Adjustment (Feature 1)
2. Tempo/Speed Adjustment (Feature 2)
3. Audio Extraction (Feature 15)
4. Karaoke Video Creation (Feature 14)

Priority 2 (Week 1):
5. Combined Pitch-Tempo (Feature 3)
6. Loudness Normalization (Feature 4)
7. Duration Analysis (Feature 20)
8. Speed Synchronization (Feature 12)

Priority 3 (Week 1-2):
9. Volume Control (Feature 5)
10. Format Conversion (Feature 7)
11. DAT Conversion (Feature 19)
12. File Merging (Feature 16)
```

### Phase 2: Enhancement Features (1-2 months)
```
- Audio Trimming (Feature 6)
- Video Speed Adjustment (Feature 9)
- Multi-Audio Mixing (Feature 13)
- Platform Optimization (Feature 18)
- Audio Limiter (Feature 23)
```

### Phase 3: Advanced Features (3+ months)
```
- Subtitle Burning (Feature 10)
- Vertical to Horizontal (Feature 11)
- Background Overlay (Feature 17)
- BPM Detection (Feature 21)
- Vocal Separation (Feature 22)
```

---

## Technology Stack Recommendations

### Python Libraries
- **ffmpeg-python**: Wrapper for ffmpeg commands
- **ffprobe-python**: Analysis tool wrapper
- **pydub**: High-level audio manipulation
- **numpy/scipy**: Signal processing

### External Tools
- **ffmpeg**: Core multimedia framework
- **ffprobe**: Media analysis
- **librosa**: Audio analysis (BPM, features)
- **Spleeter/VoiceSeparator**: Vocal separation

### Installation Commands
```bash
pip install ffmpeg-python ffprobe-python pydub librosa
pip install spleeter  # or voice-separator
```

**Better Approaches & Optimizations

### Quality vs Speed Trade-offs
| Feature | Basic Method | Better Method | Trade-off |
|---------|--------------|---------------|-----------|
| Pitch Shift | asetrate + atempo | rubberband + atempo | Quality vs speed |
| Tempo | atempo alone | librubberband tempo | Quality vs accuracy |
| Normalization | loudnorm | Two-pass loudnorm | Speed vs precision |
| Speed Match | Manual calc | ffprobe + verify | Accuracy vs automation |
| DAT Conversion | Basic ffmpeg | With codec detection | Reliability |

### Real-World Examples from Project

**Pitch Shifting Example (Srikanth's voice, -2 semitones):**
```bash
ffmpeg -i extracted_audio.wav -filter:a "asetrate=44100*0.89,atempo=1.125" output_audio.wav
```

**Speed Matching Example (Real Durations):**
```
"Babu Samjho Ishare-org.mp4" → 290.017234 seconds
"Babu Samjho Ishare-karaoke-session.mp4" → 298.972792 seconds
Ratio = 290.017234 / 298.972792 = 0.9700

ffmpeg -i "Babu Samjho Ishare-karaoke-session.mp4" \
  -filter_complex "[0:v]setpts=1/0.97*PTS[v];[0:a]atempo=0.97[a]" \
  -map "[v]" -map "[a]" "Babu Samjho Ishare-karaoke-session_slowed.mp4"
```

**Karaoke Video Creation (Real Example):**
```bash
ffmpeg -i "Vishwanathanu thandeyadare_down2.mp4" \
        -i "Vishwanathanu tandeyaadare_down2-karaoke2.mp3" \
        -c:v copy -map 0:v:0 -map 1:a:0 "Vishwanathanu tandeyaadare_down2-karaoke.mp4"
```

**Combined Pitch + Tempo (Professional Method):**
```bash
ffmpeg -i "Baadi Hoda Balli Inda-org.mp4" \
  -filter_complex "[0:a]rubberband=pitch=0.943874,atempo=0.97[a];[0:v]setpts=PTS/0.97[v]" \
  -map "[v]" -map "[a]" "Baadi Hoda Balli Inda.mp4"
```

**Batch DAT Conversion (Windows):**
Create file: `convert_dat.bat`
```batch
for %%a in (*.dat) do ffmpeg -i "%%a" -acodec libmp3lame -b:a 192k "%%~na.mp3"
```

### Real User Semitone Chart
```
-1 semitone:    asetrate=44100*0.94387,  atempo=1.05946
-2 semitones:   asetrate=44100*0.89,     atempo=1.125    [Srikanth]
-2.5 semitones: asetrate=44100*0.8715,   atempo=1.15     [Anita]
-2.7 semitones: asetrate=44100*0.8464,   atempo=1.181    [Surendra]
-3 semitones:   asetrate=44100*0.8342,   atempo=1.2      [Anita]
-4 semitones:   asetrate=44100*0.7937,   atempo=1.26
```

---

## Better Approaches & Optimizations

### Quality vs Speed Trade-offs
| Feature | Basic Method | Better Method | Trade-off |
|---------|--------------|---------------|-----------|
| Pitch Shift | asetrate + atempo | librubberband | Quality vs speed |
| Tempo | atempo | librubberband | Quality vs accuracy |
| Normalization | loudnorm | Two-pass loudnorm | Speed vs precision |
| Speed Match | Single ffmpeg | Pre-calculate → verify | Accuracy |

### Performance Optimization
1. **GPU Acceleration:** Use `-hwaccel cuda` for NVIDIA GPUs
2. **Batch Processing:** Queue multiple operations
3. **Codec Selection:** Use libx264 (faster) vs libx265 (better compression)
4. **Threading:** FFmpeg auto-detects CPU cores; can force with `-threads N`

### Error Handling
- Validate input files before processing
- Implement timeout mechanisms for long operations
- Provide progress feedback to users
- Log all ffmpeg operations for debugging

---

## Next Steps

1. ✅ Documentation prepared (THIS FILE)
2. ⏳ **Next:** Create wrapper functions for each feature in Python
3. ⏳ Integrate into UI (dropdowns, sliders, buttons)
4. ⏳ Testing with various file formats
5. ⏳ Performance optimization

---

**Document Version:** 1.0  
**Last Updated:** 2026-06-20  
**Status:** Ready for Implementation

---

## ADDENDUM: Real-World Workflows & Examples

### Workflow 1: Create Karaoke Video from YouTube Video + Audio
**Goal:** Download video from YouTube, replace audio with karaoke track, export

**Step-by-Step Commands:**
```bash
# 1. Download YouTube video
yt-dlp --format "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]" "https://youtu.be/URL_HERE"

# 2. Extract original audio (if needed for reference)
ffmpeg -i "video.mp4" -q:a 0 -map a "extracted_audio.wav"

# 3. Replace audio with karaoke version
ffmpeg -i "video.mp4" -i "karaoke_audio.mp3" \
  -c:v copy -map 0:v:0 -map 1:a:0 "video_karaoke.mp4"
```

### Workflow 2: Match Video & Karaoke Audio Speeds
**Goal:** Video plays too fast/slow compared to karaoke audio - fix it

**Step-by-Step:**
```bash
# 1. Get both file durations
ffprobe -v error -show_entries format=duration \
  -of default=noprint_wrappers=1:nokey=1 "video.mp4"
ffprobe -v error -show_entries format=duration \
  -of default=noprint_wrappers=1:nokey=1 "karaoke.mp3"

# 2. Calculate ratio (e.g., 290 seconds / 299 seconds = 0.97)

# 3. Adjust video to match karaoke speed
ffmpeg -i "video.mp4" -filter_complex "[0:v]setpts=1/0.97*PTS[v];[0:a]atempo=0.97[a]" \
  -map "[v]" -map "[a]" "video_matched.mp4"

# 4. Verify final duration matches
ffprobe -v error -show_entries format=duration \
  -of default=noprint_wrappers=1:nokey=1 "video_matched.mp4"
```

### Workflow 3: Transpose Song for Different Singer
**Goal:** Lower vocal pitch by 2 semitones for male singer

**Simple Method (asetrate):**
```bash
ffmpeg -i "original_vocal.wav" \
  -filter:a "asetrate=44100*0.89,atempo=1.125" \
  "transposed_-2st.wav"
```

**Professional Method (Rubberband - Better Quality):**
```bash
ffmpeg -i "original_vocal.mp4" \
  -filter_complex "[0:a]rubberband=pitch=0.89[a]" \
  -map 0:v -map "[a]" "transposed_-2st.mp4"
```

### Workflow 4: Convert WhatsApp .dat Files to MP4
**Goal:** Batch convert all downloaded WhatsApp videos

**Create convert_videos.bat:**
```batch
@echo off
for %%a in (*.dat) do (
  echo Converting %%a...
  ffmpeg -i "%%a" -c:v copy -c:a copy "%%~na.mp4"
)
echo All files converted!
pause
```

**Run it in the folder with .dat files**

### Workflow 5: Normalize Loudness Across Multiple Tracks
**Goal:** All karaoke tracks play at same volume level

**One-Pass (Simple):**
```bash
ffmpeg -i "track1.mp3" -filter:a loudnorm -c:v copy "track1_normalized.mp3"
ffmpeg -i "track2.mp3" -filter:a loudnorm -c:v copy "track2_normalized.mp3"
```

**Two-Pass (Professional - Better Accuracy):**
```bash
# First pass: analyze
ffmpeg -i "track.mp3" -af loudnorm=print_format=json -f null - > analysis.txt

# Second pass: apply with exact parameters
ffmpeg -i "track.mp3" -af "loudnorm=I=-14:LRA=11:tp=-1.5" "track_normalized.mp3"
```

### Workflow 6: Trim Opening Silence & Mix with Background Music
**Goal:** Remove intro silence and mix voice with background

**Step 1: Trim**
```bash
ffmpeg -y -ss 3.5 -i "vocal.mp3" -acodec copy "vocal_trimmed.mp3"
```

**Step 2: Mix**
```bash
ffmpeg -i "vocal_trimmed.mp3" -i "background.wav" \
  -filter_complex "[0:a][1:a]amix=inputs=2:duration=first[a]" \
  -map "[a]" -c:a aac "vocal_with_background.mp3"
```

### Workflow 7: Create Karaoke Video with Subtitles
**Goal:** Embed transliterated lyrics into karaoke video

**Prerequisites:** Create transliterated_lyrics.srt file

**Command:**
```bash
ffmpeg -i "karaoke_video.mp4" \
  -vf subtitles=transliterated_lyrics.srt \
  -c:a copy "karaoke_with_lyrics.mp4"
```

**SRT File Format Example:**
```
1
00:00:00,000 --> 00:00:05,000
Naanu yaaru yaava uru...

2
00:00:05,000 --> 00:00:10,000
Kannada geetada...
```

### Processing Time References
```
Feature                          | File Size | Time
---------------------------------|-----------|----------
Audio extraction (WAV)           | 4.5 MB    | 30 seconds
Speed matching (no re-encode)    | 700 MB    | 5-10 minutes
Pitch shift (asetrate)           | 4.5 MB    | 1-2 minutes
Pitch shift (rubberband)         | 4.5 MB    | 5-10 minutes
Video codec copy (karaoke mix)   | 700 MB    | 5-10 minutes
Loudness normalize               | 4.5 MB    | 2-3 minutes
Subtitle burn-in                 | 700 MB    | 15-30 minutes
DAT batch conversion (10 files)  | 50 MB avg | 1-2 minutes per file
```

---

**Document Version:** 1.1  
**Last Updated:** 2026-06-20 (Added Real-World Workflows)  
**Status:** Complete with Practical Examples
