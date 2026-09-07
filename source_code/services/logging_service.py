"""
Centralized logging service for Karaoke Studio Pro.

Provides:
- Multiple log levels (DEBUG, INFO, WARNING, ERROR)
- Automatic log rotation (prevents logs from growing too large)
- Session tracking (when app starts/stops)
- Easy log access for users to report issues
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler


class LoggingService:
    """Centralized logging service for the application."""

    # Log file locations
    DEBUG_LOG = "app_debug.log"  # All debug messages (high volume)
    ERROR_LOG = "app_errors.log"  # Errors and exceptions only
    
    # Log rotation settings
    MAX_BYTES = 5 * 1024 * 1024  # 5 MB per file
    BACKUP_COUNT = 5  # Keep 5 rotated backup files (total ~25 MB)
    
    def __init__(self, log_dir: Path):
        """
        Initialize logging service.
        
        Args:
            log_dir: Path to directory where logs will be stored (e.g., config/)
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # Debug logger (all messages)
        self.debug_logger = self._create_logger(
            "karaoke_debug",
            self.log_dir / self.DEBUG_LOG,
            logging.DEBUG
        )
        
        # Error logger (errors only)
        self.error_logger = self._create_logger(
            "karaoke_errors",
            self.log_dir / self.ERROR_LOG,
            logging.ERROR
        )
        
        # Session started
        self.info("=" * 70)
        self.info("APPLICATION STARTED")
        self.info("=" * 70)

    def _create_logger(self, name: str, log_file: Path, level: int) -> logging.Logger:
        """
        Create a logger with rotating file handler.
        
        Args:
            name: Logger name
            log_file: Path to log file
            level: Logging level (DEBUG, INFO, WARNING, ERROR)
            
        Returns:
            Configured logger instance
        """
        logger = logging.getLogger(name)
        logger.setLevel(level)
        logger.propagate = False
        
        # Remove existing handlers to avoid duplicates
        logger.handlers.clear()
        
        # Rotating file handler (auto-rotates when file exceeds MAX_BYTES)
        handler = RotatingFileHandler(
            log_file,
            maxBytes=self.MAX_BYTES,
            backupCount=self.BACKUP_COUNT,
            encoding="utf-8"
        )
        
        # Format: TIMESTAMP | LEVEL | MESSAGE
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger

    def debug(self, message: str):
        """Log debug message (development/troubleshooting)."""
        try:
            print(message)  # Also print to console
        except Exception:
            pass
        
        try:
            self.debug_logger.debug(message)
        except Exception:
            pass

    def info(self, message: str):
        """Log info message (user-relevant events)."""
        try:
            print(message)  # Also print to console
        except Exception:
            pass
        
        try:
            self.debug_logger.info(message)
        except Exception:
            pass

    def warning(self, message: str):
        """Log warning message (something unexpected but not critical)."""
        try:
            print(f"⚠️  {message}")  # Print with warning indicator
        except Exception:
            pass
        
        try:
            self.debug_logger.warning(message)
        except Exception:
            pass

    def error(self, message: str):
        """Log error message (something went wrong)."""
        try:
            print(f"❌ {message}")  # Print with error indicator
        except Exception:
            pass
        
        try:
            self.debug_logger.error(message)
            self.error_logger.error(message)
        except Exception:
            pass

    def exception(self, context: str, exc: Exception):
        """
        Log exception with full traceback.
        
        Args:
            context: Where the exception occurred (e.g., "load_video")
            exc: The exception object
        """
        import traceback
        tb_text = traceback.format_exc()
        
        error_msg = f"[{context}] EXCEPTION: {exc}"
        
        try:
            print(f"❌ {error_msg}")
            print(tb_text)
        except Exception:
            pass
        
        try:
            self.debug_logger.error(error_msg)
            self.debug_logger.error(tb_text)
            self.error_logger.error(error_msg)
            self.error_logger.error(tb_text)
        except Exception:
            pass

    def get_debug_log_path(self) -> Path:
        """Get path to debug log file."""
        return self.log_dir / self.DEBUG_LOG

    def get_error_log_path(self) -> Path:
        """Get path to error log file."""
        return self.log_dir / self.ERROR_LOG

    def get_logs_dir(self) -> Path:
        """Get path to logs directory (for user access)."""
        return self.log_dir

    def shutdown(self):
        """Log shutdown and close handlers."""
        self.info("=" * 70)
        self.info("APPLICATION SHUTDOWN")
        self.info("=" * 70)
        
        # Close all handlers
        for logger in [self.debug_logger, self.error_logger]:
            for handler in logger.handlers[:]:
                handler.close()
                logger.removeHandler(handler)
