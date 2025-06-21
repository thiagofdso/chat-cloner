"""
Configuration management for Clonechat.
"""
import os
import subprocess
from typing import Optional
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

from logging_config import (
    get_logger,
    log_configuration,
    log_operation_start,
    log_operation_success,
    log_operation_error
)

logger = get_logger(__name__)


@dataclass
class Config:
    """Configuration class for Clonechat."""
    telegram_api_id: str
    telegram_api_hash: str
    cloner_delay_seconds: int
    cloner_download_path: str


def load_config() -> Config:
    """
    Load configuration from environment variables.
    
    Returns:
        Config: Configuration object with loaded values.
        
    Raises:
        ValueError: If required environment variables are missing.
    """
    log_operation_start(logger, "load_config")
    
    # Load .env file if it exists
    load_dotenv()
    logger.debug("📄 .env file loaded (if exists)")
    
    # Get required environment variables
    telegram_api_id = os.getenv('TELEGRAM_API_ID')
    telegram_api_hash = os.getenv('TELEGRAM_API_HASH')
    
    # Get optional environment variables with defaults
    cloner_delay_seconds = int(os.getenv('CLONER_DELAY_SECONDS', '2'))
    cloner_download_path = os.getenv('CLONER_DOWNLOAD_PATH', './data/downloads/')
    
    # Validate required variables
    if not telegram_api_id:
        log_operation_error(logger, "load_config", ValueError("TELEGRAM_API_ID is required"), missing_var="TELEGRAM_API_ID")
        raise ValueError("TELEGRAM_API_ID is required. Please set it in your .env file.")
    
    if not telegram_api_hash:
        log_operation_error(logger, "load_config", ValueError("TELEGRAM_API_HASH is required"), missing_var="TELEGRAM_API_HASH")
        raise ValueError("TELEGRAM_API_HASH is required. Please set it in your .env file.")
    
    # Validate delay seconds
    if cloner_delay_seconds < 0:
        log_operation_error(logger, "load_config", ValueError("Invalid delay seconds"), cloner_delay_seconds=cloner_delay_seconds)
        raise ValueError("CLONER_DELAY_SECONDS must be a positive integer.")
    
    # Ensure download path exists
    download_path = Path(cloner_download_path)
    download_path.mkdir(parents=True, exist_ok=True)
    logger.debug(f"📁 Download path ensured: {download_path}")
    
    # Log configuration details (without sensitive data)
    log_configuration(
        logger,
        telegram_api_id=f"{telegram_api_id[:4]}...{telegram_api_id[-4:]}" if len(telegram_api_id) > 8 else "***",
        telegram_api_hash=f"{telegram_api_hash[:4]}...{telegram_api_hash[-4:]}" if len(telegram_api_hash) > 8 else "***",
        cloner_delay_seconds=cloner_delay_seconds,
        cloner_download_path=cloner_download_path
    )
    
    config = Config(
        telegram_api_id=telegram_api_id,
        telegram_api_hash=telegram_api_hash,
        cloner_delay_seconds=cloner_delay_seconds,
        cloner_download_path=cloner_download_path
    )
    
    log_operation_success(logger, "load_config")
    return config


def validate_ffmpeg() -> bool:
    """
    Validate if FFmpeg is installed and available in PATH.
    
    Returns:
        bool: True if FFmpeg is available, False otherwise.
    """
    log_operation_start(logger, "validate_ffmpeg")
    
    try:
        result = subprocess.run(
            ['ffmpeg', '-version'], 
            capture_output=True, 
            text=True, 
            timeout=10
        )
        
        if result.returncode == 0:
            # Extract version from output
            version_line = result.stdout.split('\n')[0] if result.stdout else "Unknown version"
            logger.info(f"✅ FFmpeg validation successful: {version_line}")
            log_operation_success(logger, "validate_ffmpeg", ffmpeg_available=True)
            return True
        else:
            log_operation_error(logger, "validate_ffmpeg", subprocess.CalledProcessError(result.returncode, 'ffmpeg'), stderr=result.stderr)
            logger.error(f"❌ FFmpeg validation failed: {result.stderr}")
            return False
            
    except FileNotFoundError:
        log_operation_error(logger, "validate_ffmpeg", FileNotFoundError("FFmpeg not found"), error_type="FileNotFoundError")
        logger.error("❌ FFmpeg not found in PATH")
        return False
        
    except subprocess.TimeoutExpired:
        log_operation_error(logger, "validate_ffmpeg", subprocess.TimeoutExpired('ffmpeg', 10), error_type="TimeoutExpired")
        logger.error("⏰ FFmpeg validation timed out")
        return False
        
    except Exception as e:
        log_operation_error(logger, "validate_ffmpeg", e, error_type=type(e).__name__)
        logger.error(f"❌ Unexpected error during FFmpeg validation: {str(e)}")
        return False


def check_environment() -> dict[str, bool]:
    """
    Check the environment for all required dependencies and configurations.
    
    Returns:
        dict: Dictionary with check results for each component.
    """
    log_operation_start(logger, "check_environment")
    
    results = {}
    
    # Check FFmpeg
    results['ffmpeg'] = validate_ffmpeg()
    
    # Check .env file
    env_file = Path('.env')
    results['env_file'] = env_file.exists()
    if not results['env_file']:
        logger.warning("⚠️ .env file not found. Using system environment variables.")
    
    # Check data directory
    data_dir = Path('data')
    results['data_directory'] = data_dir.exists()
    if not results['data_directory']:
        logger.info("📁 Creating data directory...")
        data_dir.mkdir(exist_ok=True)
        results['data_directory'] = True
    
    # Check downloads directory
    downloads_dir = Path('data/downloads')
    results['downloads_directory'] = downloads_dir.exists()
    if not results['downloads_directory']:
        logger.info("📁 Creating downloads directory...")
        downloads_dir.mkdir(parents=True, exist_ok=True)
        results['downloads_directory'] = True
    
    # Log results
    all_passed = all(results.values())
    if all_passed:
        logger.info("✅ Environment check passed")
        log_operation_success(logger, "check_environment", **results)
    else:
        failed_checks = [k for k, v in results.items() if not v]
        logger.warning(f"⚠️ Environment check failed for: {', '.join(failed_checks)}")
        log_operation_error(logger, "check_environment", ValueError("Environment check failed"), **results)
    
    return results 