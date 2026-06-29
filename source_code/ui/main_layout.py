"""Main application layout orchestrator - combines all UI components"""

from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QStackedWidget, QScrollArea
from PySide6.QtCore import Qt
from source_code.widgets.video_frame import VideoFrame
from source_code.ui.sidebar import create_sidebar
from source_code.ui.playback_bar import create_playback_bar
from source_code.ui.media_loader_page import create_media_loader_page
from source_code.ui.pitch_page import create_pitch_page
from source_code.ui.extra_page import create_audio_tools_page
from source_code.ui.video_tools_page import create_video_tools_page
from PySide6.QtWidgets import QLabel, QWidget
from PySide6.QtGui import QFont


def create_main_layout(settings):
    """Create the main application layout combining all UI components
    
    Args:
        settings: Settings dict for configuration
    
    Returns:
        dict: Dictionary containing all UI components and the main layout
    """
    components = {}
    
    # Create main layout
    main_h_layout = QHBoxLayout()
    main_h_layout.setContentsMargins(0, 0, 0, 0)
    main_h_layout.setSpacing(0)

    # Create sidebar
    sidebar_components = create_sidebar(None)
    components["sidebar_components"] = sidebar_components
    main_h_layout.addWidget(sidebar_components["sidebar"])

    # Create content container
    content_container = QVBoxLayout()

    # Video frame — low initial minimum so Qt calculates a small window minimum size;
    # actual minimum is set per-page in handle_navigation_change
    video_frame = VideoFrame()
    video_frame.setStyleSheet("background-color: #000;")
    video_frame.setMinimumHeight(80)
    content_container.addWidget(video_frame, 10)
    components["video_frame"] = video_frame

    # Filename label
    filename_label = QLabel("No file loaded")
    filename_label.setStyleSheet("color: #ccc; padding: 5px 15px; font-size: 12px; background-color: #1e1e1e;")
    content_container.addWidget(filename_label)
    components["filename_label"] = filename_label

    # Playback bar
    playback_components = create_playback_bar(settings)
    content_container.addWidget(playback_components["playback_widget"])
    components["playback_components"] = playback_components

    # Content pages (stacked widget)
    stack = QStackedWidget()
    
    media_loader_page_components = create_media_loader_page()
    stack.addWidget(media_loader_page_components["page"])
    components["media_loader_page_components"] = media_loader_page_components
    components["download_page_components"] = media_loader_page_components  # backward compatibility
    
    pitch_page_components = create_pitch_page()
    stack.addWidget(pitch_page_components["page"])
    components["pitch_page_components"] = pitch_page_components
    
    # Index 2: Audio Tools page (wrapped in scroll area so controls are reachable)
    audio_tools_page_components = create_audio_tools_page()
    audio_scroll = QScrollArea()
    audio_scroll.setWidget(audio_tools_page_components["page"])
    audio_scroll.setWidgetResizable(True)
    audio_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    audio_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    audio_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
    stack.addWidget(audio_scroll)
    components["audio_tools_page_components"] = audio_tools_page_components

    # Index 3: Video Tools page (wrapped in scroll area so controls are reachable)
    video_tools_page_components = create_video_tools_page()
    video_tools_scroll = QScrollArea()
    video_tools_scroll.setWidget(video_tools_page_components["page"])
    video_tools_scroll.setWidgetResizable(True)
    video_tools_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    video_tools_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    video_tools_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
    stack.addWidget(video_tools_scroll)
    components["video_tools_page_components"] = video_tools_page_components
    
    # Audio Tools components exposed directly; widen controls are inside video_tools_page_components
    extra_page_components = {**audio_tools_page_components}
    components["extra_page_components"] = extra_page_components

    components["stack"] = stack
    content_container.addWidget(stack, 1)

    main_h_layout.addLayout(content_container)

    return {
        "main_layout": main_h_layout,
        "components": components
    }
