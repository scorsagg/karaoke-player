"""Factories for the loading/progress splash screens used by every long-running action."""

import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPixmap

LOADING_SPLASH_WIDTH = 600
LOADING_SPLASH_HEIGHT = 300
FALLBACK_SPLASH_COLOR = "#1e1e1e"


def create_loading_pixmap(width=LOADING_SPLASH_WIDTH, height=LOADING_SPLASH_HEIGHT):
    """Return the bundled Loading.png scaled to splash size, or a flat placeholder."""
    from source_code.main import get_resource_path

    loading_path = get_resource_path("Loading.png")
    if os.path.exists(loading_path):
        return QPixmap(loading_path).scaled(width, height, Qt.KeepAspectRatio, Qt.SmoothTransformation)

    pixmap = QPixmap(width, height)
    pixmap.fill(QColor(FALLBACK_SPLASH_COLOR))
    return pixmap


def create_loading_splash(show_cancel_button=False):
    """Return an unshown splash screen displaying the loading artwork."""
    from source_code.main import ModernSplashScreen

    return ModernSplashScreen(create_loading_pixmap(), show_cancel_button=show_cancel_button)


def show_cancellable_splash(on_cancel, progress=None, message=None):
    """Show a splash whose STOP button triggers `on_cancel`."""
    splash = create_loading_splash(show_cancel_button=True)
    splash.cancel_btn.clicked.connect(on_cancel)
    splash.show()
    if progress is not None:
        splash.set_progress(progress, message or "")
    return splash


def show_task_splash(app, task_key, progress=None, message=None):
    """Show the export splash for an async task, cancelling that task on STOP."""
    app.export_splash = show_cancellable_splash(
        lambda: app.kill_allocated_task(task_key), progress, message
    )
    return app.export_splash


def show_download_splash(app, progress=2, message="Initializing download..."):
    """Show the download splash, stopping the active download on STOP."""
    app.download_splash = show_cancellable_splash(
        app.download_service.stop_download, progress, message
    )
    return app.download_splash


def close_splash(app, attribute="export_splash"):
    """Close and clear a splash stored on the app, if one is present."""
    splash = getattr(app, attribute, None)
    if splash is not None:
        splash.close()
        setattr(app, attribute, None)
