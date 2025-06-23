"""
Configuration management for Clonechat.
"""
import os
import subprocess
from typing import Optional
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

from .logging_config import (
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
    
    # Zimatise pipeline configuration
    file_size_limit_mb: int = 1000
    mode: str = "zip"
    video_extensions: str = "mp4,avi,webm,ts,vob,mov,mkv,wmv,3gp,flv,ogv,ogg,rrc,gifv,mng,qt,yuv,rm,asf,amv,m4p,m4v,mpg,mp2,mpeg,mpe,mpv,svi,3g2,mxf,roq,nsv,f4v,f4p,f4a,f4b"
    reencode_plan: str = "single"
    duration_limit: str = "02:00:00.00"
    activate_transition: str = "false"
    start_index: int = 1
    hashtag_index: str = "F"
    descriptions_auto_adapt: str = "true"
    silent_mode: str = "true"
    path_summary_top: str = "summary_top.txt"
    path_summary_bot: str = "summary_bot.txt"
    document_hashtag: str = "Materiais"
    document_title: str = "Materiais"
    register_invite_link: str = "1"
    
    # Channel description configuration
    channel_title_prefix: str = "Academy"
    channel_size_label: str = "Tamanho"
    channel_duration_label: str = "Duração"
    channel_invite_label: str = "Convite"
    
    # Additional Zimatise configurations
    max_path: int = 260
    create_new_channel: str = "1"
    chat_id: str = "-100111111111"
    moc_chat_id: str = "-10022222222"
    autodel_video_temp: str = "1"
    channel_adms: str = ""
    time_limit: str = "99"
    send_moc: str = "0"
    move_to_uploaded: str = "1"


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
    
    # Zimatise pipeline configuration
    file_size_limit_mb = int(os.getenv('FILE_SIZE_LIMIT_MB', '1000'))
    mode = os.getenv('MODE', 'zip')
    video_extensions = os.getenv('VIDEO_EXTENSIONS', 'mp4,avi,webm,ts,vob,mov,mkv,wmv,3gp,flv,ogv,ogg,rrc,gifv,mng,qt,yuv,rm,asf,amv,m4p,m4v,mpg,mp2,mpeg,mpe,mpv,svi,3g2,mxf,roq,nsv,f4v,f4p,f4a,f4b')
    reencode_plan = os.getenv('REENCODE_PLAN', 'single')
    duration_limit = os.getenv('DURATION_LIMIT', '02:00:00.00')
    activate_transition = os.getenv('ACTIVATE_TRANSITION', 'false')
    start_index = int(os.getenv('START_INDEX', '1'))
    hashtag_index = os.getenv('HASHTAG_INDEX', 'F')
    descriptions_auto_adapt = os.getenv('DESCRIPTIONS_AUTO_ADAPT', 'true')
    silent_mode = os.getenv('SILENT_MODE', 'true')
    path_summary_top = os.getenv('PATH_SUMMARY_TOP', 'summary_top.txt')
    path_summary_bot = os.getenv('PATH_SUMMARY_BOT', 'summary_bot.txt')
    document_hashtag = os.getenv('DOCUMENT_HASHTAG', 'Materiais')
    document_title = os.getenv('DOCUMENT_TITLE', 'Materiais')
    register_invite_link = os.getenv('REGISTER_INVITE_LINK', '1')
    
    # Additional Zimatise configurations
    max_path = int(os.getenv('MAX_PATH', '260'))
    create_new_channel = os.getenv('CREATE_NEW_CHANNEL', '1')
    chat_id = os.getenv('CHAT_ID', '-100111111111')
    moc_chat_id = os.getenv('MOC_CHAT_ID', '-10022222222')
    autodel_video_temp = os.getenv('AUTODEL_VIDEO_TEMP', '1')
    channel_adms = os.getenv('CHANNEL_ADMS', '')
    time_limit = os.getenv('TIME_LIMIT', '99')
    send_moc = os.getenv('SEND_MOC', '0')
    move_to_uploaded = os.getenv('MOVE_TO_UPLOADED', '1')
    
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
        cloner_download_path=cloner_download_path,
        file_size_limit_mb=file_size_limit_mb,
        mode=mode,
        video_extensions=video_extensions,
        reencode_plan=reencode_plan,
        duration_limit=duration_limit,
        activate_transition=activate_transition,
        start_index=start_index,
        hashtag_index=hashtag_index,
        descriptions_auto_adapt=descriptions_auto_adapt,
        silent_mode=silent_mode,
        path_summary_top=path_summary_top,
        path_summary_bot=path_summary_bot,
        document_hashtag=document_hashtag,
        document_title=document_title,
        register_invite_link=register_invite_link,
        max_path=max_path,
        create_new_channel=create_new_channel,
        chat_id=chat_id,
        moc_chat_id=moc_chat_id,
        autodel_video_temp=autodel_video_temp,
        channel_adms=channel_adms,
        time_limit=time_limit,
        send_moc=send_moc,
        move_to_uploaded=move_to_uploaded,
        channel_title_prefix=os.getenv('CHANNEL_TITLE_PREFIX', 'Academy'),
        channel_size_label=os.getenv('CHANNEL_SIZE_LABEL', 'Tamanho'),
        channel_duration_label=os.getenv('CHANNEL_DURATION_LABEL', 'Duração'),
        channel_invite_label=os.getenv('CHANNEL_INVITE_LABEL', 'Convite')
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