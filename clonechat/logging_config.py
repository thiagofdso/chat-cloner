"""
Advanced logging configuration for Clonechat.

This module provides centralized logging configuration with custom formatting,
file and console output, and different log levels for different components.
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for console output."""
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
        'RESET': '\033[0m'      # Reset
    }
    
    def format(self, record):
        # Add color to the level name
        if record.levelname in self.COLORS:
            record.levelname = f"{self.COLORS[record.levelname]}{record.levelname}{self.COLORS['RESET']}"
        
        return super().format(record)


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[Path] = None,
    enable_console: bool = True,
    enable_file: bool = True
) -> None:
    """
    Setup advanced logging configuration.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_file: Path to log file. If None, uses 'data/app.log'.
        enable_console: Whether to enable console output.
        enable_file: Whether to enable file output.
    """
    # Convert string level to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Clear any existing handlers
    root_logger.handlers.clear()
    
    # Create formatters
    console_formatter = ColoredFormatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(numeric_level)
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
    
    # File handler
    if enable_file:
        if log_file is None:
            # Ensure data directory exists
            data_dir = Path("data")
            data_dir.mkdir(exist_ok=True)
            log_file = data_dir / "app.log"
        
        # Ensure log file directory exists
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Use RotatingFileHandler for log rotation
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
    
    # Set specific loggers to appropriate levels
    logging.getLogger('pyrogram').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('asyncio').setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name.
    
    Args:
        name: Logger name (usually __name__).
        
    Returns:
        Configured logger instance.
    """
    return logging.getLogger(name)


# Convenience functions for different log levels
def log_operation_start(logger: logging.Logger, operation: str, **kwargs) -> None:
    """Log the start of an operation with context."""
    context = ", ".join([f"{k}={v}" for k, v in kwargs.items()])
    logger.info(f"🚀 Starting {operation} - {context}")


def log_operation_success(logger: logging.Logger, operation: str, **kwargs) -> None:
    """Log the successful completion of an operation."""
    context = ", ".join([f"{k}={v}" for k, v in kwargs.items()])
    logger.info(f"✅ Completed {operation} - {context}")


def log_operation_error(logger: logging.Logger, operation: str, error: Exception, **kwargs) -> None:
    """Log an operation error with context."""
    context = ", ".join([f"{k}={v}" for k, v in kwargs.items()])
    logger.error(f"❌ Error in {operation} - {context} - {error}")


def log_progress(logger: logging.Logger, current: int, total: int, operation: str = "Processing") -> None:
    """Log progress information."""
    percentage = (current / total) * 100 if total > 0 else 0
    logger.info(f"📊 {operation} progress: {current}/{total} ({percentage:.1f}%)")


def log_flood_wait(logger: logging.Logger, wait_time: int) -> None:
    """Log FloodWait information."""
    logger.warning(f"⏳ FloodWait detected: waiting {wait_time} seconds")


def log_retry_attempt(logger: logging.Logger, attempt: int, max_attempts: int, error: Exception) -> None:
    """Log retry attempt information."""
    logger.warning(f"🔄 Retry attempt {attempt}/{max_attempts} failed: {error}")


def log_file_operation(logger: logging.Logger, operation: str, file_path: Path, **kwargs) -> None:
    """Log file operation information."""
    context = ", ".join([f"{k}={v}" for k, v in kwargs.items()])
    logger.debug(f"📁 {operation} file: {file_path.name} - {context}")


def log_media_operation(logger: logging.Logger, operation: str, message_id: int, media_type: str) -> None:
    """Log media operation information."""
    logger.debug(f"🎵 {operation} media: message_id={message_id}, type={media_type}")


def log_strategy_detection(logger: logging.Logger, strategy: str, chat_id: int) -> None:
    """Log strategy detection information."""
    logger.info(f"🎯 Strategy detected: {strategy} for chat {chat_id}")


def log_channel_creation(logger: logging.Logger, channel_id: int, channel_title: str) -> None:
    """Log channel creation information."""
    logger.info(f"📢 Created channel: {channel_title} (ID: {channel_id})")


def log_database_operation(logger: logging.Logger, operation: str, **kwargs) -> None:
    """Log database operation information."""
    context = ", ".join([f"{k}={v}" for k, v in kwargs.items()])
    logger.debug(f"💾 Database {operation}: {context}")


def log_configuration(logger: logging.Logger, **kwargs) -> None:
    """Log configuration information."""
    config_items = ", ".join([f"{k}={v}" for k, v in kwargs.items()])
    logger.info(f"⚙️ Configuration loaded: {config_items}")


def log_ffmpeg_operation(logger: logging.Logger, operation: str, input_file: Path, output_file: Optional[Path] = None) -> None:
    """Log FFmpeg operation information."""
    if output_file:
        logger.info(f"🎬 FFmpeg {operation}: {input_file.name} -> {output_file.name}")
    else:
        logger.info(f"🎬 FFmpeg {operation}: {input_file.name}")


def log_cleanup_operation(logger: logging.Logger, file_path: Path) -> None:
    """Log cleanup operation information."""
    logger.debug(f"🧹 Cleaned up temporary file: {file_path.name}") 