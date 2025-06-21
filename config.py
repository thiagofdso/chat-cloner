"""
Configuration management for Clonechat.
"""
import subprocess
import logging
from typing import Optional


def validate_ffmpeg() -> bool:
    """
    Validate if FFmpeg is installed and available in PATH.
    
    Returns:
        bool: True if FFmpeg is available, False otherwise.
    """
    try:
        result = subprocess.run(
            ['ffmpeg', '-version'], 
            capture_output=True, 
            text=True, 
            timeout=10
        )
        if result.returncode == 0:
            logging.info("FFmpeg validation successful")
            return True
        else:
            logging.error("FFmpeg validation failed: %s", result.stderr)
            return False
    except FileNotFoundError:
        logging.error("FFmpeg not found in PATH")
        return False
    except subprocess.TimeoutExpired:
        logging.error("FFmpeg validation timed out")
        return False
    except Exception as e:
        logging.error("Unexpected error during FFmpeg validation: %s", str(e))
        return False 