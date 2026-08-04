from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class AppState:
    """Centralized runtime state for the karaoke application window.

    This intentionally keeps the existing window-level attribute names available
    through a single state container so the UI/controller logic can be migrated
    incrementally without changing behavior.
    """

    video_path: str = ""
    audio_tools_file_path: str = ""
    active_tasks: Dict[str, Any] = field(default_factory=dict)
    is_video_fullscreen: bool = False
    download_splash: Any = None
    export_splash: Any = None
    _download_ui_busy: bool = False
    _download_from_audio_tools: bool = False
    _vocal_offline_dialog_shown: bool = False

    auto_reduce_active: bool = False
    _player_was_active: bool = False
    _pending_seek_ratio: Optional[float] = None

    merge_input_a_path: str = ""
    merge_input_b_path: str = ""
    _last_merge_cmd_text: str = ""

    _current_is_audio_only: bool = False
    _current_export_media_kind: str = "unknown"
    _smoothed_pitch_hz: Optional[float] = None
    _last_pitch_confidence: float = 0.0
    _realtime_pitch_apply_timer: Any = None
    _tonic_note_counts: Dict[int, int] = field(default_factory=dict)
    _tonic_frames_collected: int = 0
    _tonic_locked: bool = False
    _tonic_note_class: Optional[int] = None

    extra_tools_is_expanded: bool = False
    history_is_expanded: bool = False

    _live_amplify_factor: float = 1.0
    _pre_amplify_base_volume: Optional[int] = None
    _live_amplify_step: int = 0
    _live_amp_preview_active: bool = False
    _last_non_amplify_convert_export_tab_index: int = 0
