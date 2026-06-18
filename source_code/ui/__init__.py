"""UI components package - modularized user interface components"""

from source_code.ui.main_layout import create_main_layout
from source_code.ui.sidebar import create_sidebar
from source_code.ui.playback_bar import create_playback_bar
from source_code.ui.download_page import create_download_page
from source_code.ui.pitch_page import create_pitch_page
from source_code.ui.extra_page import create_extra_page

__all__ = [
    "create_main_layout",
    "create_sidebar",
    "create_playback_bar",
    "create_download_page",
    "create_pitch_page",
    "create_extra_page"
]
