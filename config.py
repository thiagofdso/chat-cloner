"""
Configuration management for Clonechat.
"""
import os
import subprocess
import logging
from typing import Optional
from dataclasses import dataclass
from dotenv import load_dotenv


@dataclass
class Config:
    """Configuration class for Clonechat."""
    telegram_api_id: str
    telegram_api_hash: str
    cloner_delay_seconds: int
    cloner_download_path: str


def setup_logging() -> None:
    """
    Setup basic logging configuration.
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('data/app.log')
        ]
    )


def load_config() -> Config:
    """
    Load configuration from environment variables.
    
    Returns:
        Config: Configuration object with loaded values.
        
    Raises:
        ValueError: If required environment variables are missing.
    """
    # Load .env file if it exists
    load_dotenv()
    
    # Get required environment variables
    telegram_api_id = os.getenv('TELEGRAM_API_ID')
    telegram_api_hash = os.getenv('TELEGRAM_API_HASH')
    
    # Get optional environment variables with defaults
    cloner_delay_seconds = int(os.getenv('CLONER_DELAY_SECONDS', '2'))
    cloner_download_path = os.getenv('CLONER_DOWNLOAD_PATH', './data/downloads/')
    
    # Validate required variables
    if not telegram_api_id:
        raise ValueError("TELEGRAM_API_ID is required. Please set it in your .env file.")
    
    if not telegram_api_hash:
        raise ValueError("TELEGRAM_API_HASH is required. Please set it in your .env file.")
    
    # Validate delay seconds
    if cloner_delay_seconds < 0:
        raise ValueError("CLONER_DELAY_SECONDS must be a positive integer.")
    
    # Ensure download path exists
    os.makedirs(cloner_download_path, exist_ok=True)
    
    logging.info("Configuration loaded successfully")
    
    return Config(
        telegram_api_id=telegram_api_id,
        telegram_api_hash=telegram_api_hash,
        cloner_delay_seconds=cloner_delay_seconds,
        cloner_download_path=cloner_download_path
    )


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