"""Controller-layer boundaries for the app shell.

This package keeps the window entry-point thin while preserving the existing
public methods and compatibility wrappers for older call sites.
"""

from source_code.controllers.playback_controller import PlaybackController
from source_code.controllers.media_controller import MediaController
from source_code.controllers.processing_controller import ProcessingController
from source_code.controllers.navigation_controller import NavigationController

__all__ = [
    "PlaybackController",
    "MediaController",
    "ProcessingController",
    "NavigationController",
]
