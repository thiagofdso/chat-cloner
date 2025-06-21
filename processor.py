"""
Message processing for Clonechat.

This module contains the core message processing logic for cloning Telegram messages.
It provides two main strategies: forward (direct forwarding) and download_upload
(download, process, upload, delete cycle).
"""

import asyncio
import os
import subprocess
from pathlib import Path
from typing import Any, Callable, Optional, Union

from pyrogram import Client
from pyrogram.errors import ChatForwardsRestricted, FloodWait
from pyrogram.types import Message

from logging_config import (
    get_logger, 
    log_operation_start, 
    log_operation_success, 
    log_operation_error,
    log_media_operation,
    log_file_operation,
    log_ffmpeg_operation,
    log_cleanup_operation
)
from retry_utils import retry_telegram_operation, retry_file_operation

logger = get_logger(__name__)


def get_caption(message: Message) -> Optional[str]:
    """Extract caption from a message.
    
    Args:
        message: The Telegram message object.
        
    Returns:
        The message caption in markdown format, or None if no caption exists.
    """
    if message.caption:
        return message.caption.markdown
    return None


def get_sender(message: Message) -> Callable:
    """Determine the appropriate forward function based on message type.
    
    Args:
        message: The Telegram message object.
        
    Returns:
        The appropriate forward function for the message type.
        
    Raises:
        Exception: If message type is not recognized.
    """
    if message.photo:
        return forward_photo
    if message.text:
        return forward_text
    if message.document:
        return forward_document
    if message.sticker:
        return forward_sticker
    if message.animation:
        return forward_animation
    if message.audio:
        return forward_audio
    if message.voice:
        return forward_voice
    if message.video:
        return forward_video
    if message.video_note:
        return forward_video_note
    if message.poll:
        return forward_poll
    
    logger.error(f"Unrecognized message type: {message}")
    raise Exception(f"Unrecognized message type: {type(message)}")


@retry_telegram_operation(max_retries=3, base_delay=2.0)
async def forward_photo(client: Client, message: Message, destination_chat: int) -> None:
    """Forward a photo message.
    
    Args:
        client: The Pyrogram client.
        message: The message containing the photo.
        destination_chat: The destination chat ID.
    """
    log_media_operation(logger, "Forwarding", message.id, "photo")
    caption = get_caption(message)
    photo_id = message.photo.file_id
    
    await client.send_photo(
        chat_id=destination_chat,
        photo=photo_id,
        caption=caption,
    )


@retry_telegram_operation(max_retries=3, base_delay=2.0)
async def forward_text(client: Client, message: Message, destination_chat: int) -> None:
    """Forward a text message.
    
    Args:
        client: The Pyrogram client.
        message: The message containing the text.
        destination_chat: The destination chat ID.
    """
    log_media_operation(logger, "Forwarding", message.id, "text")
    text = message.text.markdown
    
    await client.send_message(
        chat_id=destination_chat,
        text=text,
        disable_notification=True,
        disable_web_page_preview=True,
    )


@retry_telegram_operation(max_retries=3, base_delay=2.0)
async def forward_sticker(client: Client, message: Message, destination_chat: int) -> None:
    """Forward a sticker message.
    
    Args:
        client: The Pyrogram client.
        message: The message containing the sticker.
        destination_chat: The destination chat ID.
    """
    log_media_operation(logger, "Forwarding", message.id, "sticker")
    sticker_id = message.sticker.file_id
    
    await client.send_sticker(
        chat_id=destination_chat, 
        sticker=sticker_id
    )


@retry_telegram_operation(max_retries=3, base_delay=2.0)
async def forward_document(client: Client, message: Message, destination_chat: int) -> None:
    """Forward a document message.
    
    Args:
        client: The Pyrogram client.
        message: The message containing the document.
        destination_chat: The destination chat ID.
    """
    log_media_operation(logger, "Forwarding", message.id, "document")
    caption = get_caption(message)
    document_id = message.document.file_id
    
    await client.send_document(
        chat_id=destination_chat,
        document=document_id,
        disable_notification=True,
        caption=caption,
    )


@retry_telegram_operation(max_retries=3, base_delay=2.0)
async def forward_animation(client: Client, message: Message, destination_chat: int) -> None:
    """Forward an animation message.
    
    Args:
        client: The Pyrogram client.
        message: The message containing the animation.
        destination_chat: The destination chat ID.
    """
    log_media_operation(logger, "Forwarding", message.id, "animation")
    caption = get_caption(message)
    animation_id = message.animation.file_id
    
    await client.send_animation(
        chat_id=destination_chat,
        animation=animation_id,
        disable_notification=True,
        caption=caption,
    )


@retry_telegram_operation(max_retries=3, base_delay=2.0)
async def forward_audio(client: Client, message: Message, destination_chat: int) -> None:
    """Forward an audio message.
    
    Args:
        client: The Pyrogram client.
        message: The message containing the audio.
        destination_chat: The destination chat ID.
    """
    log_media_operation(logger, "Forwarding", message.id, "audio")
    caption = get_caption(message)
    audio_id = message.audio.file_id
    
    await client.send_audio(
        chat_id=destination_chat,
        audio=audio_id,
        disable_notification=True,
        caption=caption,
    )


@retry_telegram_operation(max_retries=3, base_delay=2.0)
async def forward_voice(client: Client, message: Message, destination_chat: int) -> None:
    """Forward a voice message.
    
    Args:
        client: The Pyrogram client.
        message: The message containing the voice.
        destination_chat: The destination chat ID.
    """
    log_media_operation(logger, "Forwarding", message.id, "voice")
    caption = get_caption(message)
    voice_id = message.voice.file_id
    
    await client.send_voice(
        chat_id=destination_chat,
        voice=voice_id,
        disable_notification=True,
        caption=caption,
    )


@retry_telegram_operation(max_retries=3, base_delay=2.0)
async def forward_video_note(client: Client, message: Message, destination_chat: int) -> None:
    """Forward a video note message.
    
    Args:
        client: The Pyrogram client.
        message: The message containing the video note.
        destination_chat: The destination chat ID.
    """
    log_media_operation(logger, "Forwarding", message.id, "video_note")
    video_note_id = message.video_note.file_id
    
    await client.send_video_note(
        chat_id=destination_chat,
        video_note=video_note_id,
        disable_notification=True,
    )


@retry_telegram_operation(max_retries=3, base_delay=2.0)
async def forward_video(client: Client, message: Message, destination_chat: int) -> None:
    """Forward a video message.
    
    Args:
        client: The Pyrogram client.
        message: The message containing the video.
        destination_chat: The destination chat ID.
    """
    log_media_operation(logger, "Forwarding", message.id, "video")
    caption = get_caption(message)
    video_id = message.video.file_id
    
    await client.send_video(
        chat_id=destination_chat,
        video=video_id,
        disable_notification=True,
        caption=caption,
    )


@retry_telegram_operation(max_retries=3, base_delay=2.0)
async def forward_poll(client: Client, message: Message, destination_chat: int) -> None:
    """Forward a poll message.
    
    Args:
        client: The Pyrogram client.
        message: The message containing the poll.
        destination_chat: The destination chat ID.
    """
    log_media_operation(logger, "Forwarding", message.id, "poll")
    if message.poll.type != "regular":
        return
    
    await client.send_poll(
        chat_id=destination_chat,
        question=message.poll.question,
        options=[option.text for option in message.poll.options],
        is_anonymous=message.poll.is_anonymous,
        allows_multiple_answers=message.poll.allows_multiple_answers,
        disable_notification=True,
    )


async def forward_message(
    client: Client, 
    message: Message, 
    destination_chat: int, 
    delay_seconds: float = 2.0
) -> None:
    """Forward a message using the direct forward strategy.
    
    This function determines the message type and forwards it directly
    to the destination chat using the appropriate method.
    
    Args:
        client: The Pyrogram client.
        message: The message to forward.
        destination_chat: The destination chat ID.
        delay_seconds: Delay in seconds between operations to avoid FloodWait.
    """
    try:
        log_operation_start(logger, "forward_message", message_id=message.id, destination_chat=destination_chat)
        
        # Get the appropriate forward function based on message type
        forward_func = get_sender(message)
        
        # Forward the message
        await forward_func(client, message, destination_chat)
        
        log_operation_success(logger, "forward_message", message_id=message.id, destination_chat=destination_chat)
        
        # Apply delay to avoid FloodWait
        if delay_seconds > 0:
            await asyncio.sleep(delay_seconds)
            
    except ChatForwardsRestricted:
        log_operation_error(logger, "forward_message", ChatForwardsRestricted("Forwarding is not allowed"), 
                          message_id=message.id, destination_chat=destination_chat)
        raise
    except Exception as e:
        log_operation_error(logger, "forward_message", e, message_id=message.id, destination_chat=destination_chat)
        raise


@retry_file_operation(max_retries=2, base_delay=1.0)
def extract_audio_from_video(video_file_path: str) -> tuple[str, str]:
    """Extract audio from a video file using FFmpeg.
    
    Args:
        video_file_path: Path to the video file.
        
    Returns:
        Tuple containing (audio_file_path, filename) of the extracted audio.
        
    Raises:
        subprocess.CalledProcessError: If FFmpeg fails to extract audio.
    """
    video_path = Path(video_file_path)
    video_dir = video_path.parent
    filename = video_path.stem
    audio_file_path = video_dir / f"{filename}.mp3"
    
    if not audio_file_path.exists():
        log_ffmpeg_operation(logger, "extracting audio", video_path, audio_file_path)
        
        try:
            # Command to extract audio and resample
            command = [
                'ffmpeg',
                '-i', str(video_path),
                '-vn',                          # no video
                '-acodec', 'libmp3lame',       # MP3 audio codec
                '-b:a', '192k',                # audio bitrate
                str(audio_file_path)           # output file
            ]
            
            # Execute the command
            subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            logger.info(f"✅ Audio extracted successfully: {audio_file_path.name}")
            
        except subprocess.CalledProcessError as e:
            log_operation_error(logger, "extract_audio", e, video_file=video_path.name)
            raise
    
    return str(audio_file_path), filename


@retry_file_operation(max_retries=2, base_delay=1.0)
def delete_local_media(file_path: Union[str, Path]) -> None:
    """Delete a local media file.
    
    Args:
        file_path: Path to the file to delete.
    """
    try:
        path = Path(file_path)
        if path.exists() and path.is_file():
            path.unlink()
            log_cleanup_operation(logger, path)
    except Exception as e:
        logger.warning(f"Failed to delete file {file_path}: {e}")


@retry_telegram_operation(max_retries=3, base_delay=2.0)
async def download_media(
    client: Client, 
    message: Message, 
    download_path: Path, 
    message_id: int
) -> Optional[Path]:
    """Download media from a message.
    
    Args:
        client: The Pyrogram client.
        message: The message containing the media.
        download_path: Directory to save the downloaded file.
        message_id: The message ID for naming the file.
        
    Returns:
        Path to the downloaded file, or None if download failed.
    """
    try:
        log_operation_start(logger, "download_media", message_id=message_id)
        
        # Generate filename based on message ID and original filename
        if hasattr(message, 'document') and message.document:
            original_filename = message.document.file_name or "document"
            media_type = "document"
        elif hasattr(message, 'video') and message.video:
            original_filename = "video.mp4"
            media_type = "video"
        elif hasattr(message, 'photo') and message.photo:
            original_filename = "photo.jpg"
            media_type = "photo"
        elif hasattr(message, 'audio') and message.audio:
            original_filename = message.audio.file_name or "audio.mp3"
            media_type = "audio"
        elif hasattr(message, 'voice') and message.voice:
            original_filename = "voice.ogg"
            media_type = "voice"
        else:
            original_filename = "media"
            media_type = "unknown"
        
        file_path = download_path / f"{message_id}-{original_filename}"
        log_file_operation(logger, "downloading", file_path, media_type=media_type)
        
        # Download the media
        downloaded_path = await client.download_media(
            message,
            file_name=str(file_path)
        )
        
        if downloaded_path and Path(downloaded_path).exists():
            log_operation_success(logger, "download_media", message_id=message_id, file_path=Path(downloaded_path).name)
            return Path(downloaded_path)
        else:
            log_operation_error(logger, "download_media", Exception("Download failed"), message_id=message_id)
            return None
            
    except Exception as e:
        log_operation_error(logger, "download_media", e, message_id=message_id)
        return None


@retry_telegram_operation(max_retries=3, base_delay=2.0)
async def upload_media(
    client: Client,
    file_path: Path,
    destination_chat: int,
    caption: Optional[str] = None,
    message_type: str = "document"
) -> None:
    """Upload media to a destination chat.
    
    Args:
        client: The Pyrogram client.
        file_path: Path to the file to upload.
        destination_chat: The destination chat ID.
        caption: Optional caption for the media.
        message_type: Type of media (video, document, photo, audio, voice).
    """
    try:
        log_operation_start(logger, "upload_media", file_path=file_path.name, message_type=message_type, destination_chat=destination_chat)
        
        if message_type == "video":
            await client.send_video(
                chat_id=destination_chat,
                video=str(file_path),
                caption=caption,
                supports_streaming=True,
            )
        elif message_type == "document":
            await client.send_document(
                chat_id=destination_chat,
                document=str(file_path),
                caption=caption,
            )
        elif message_type == "photo":
            await client.send_photo(
                chat_id=destination_chat,
                photo=str(file_path),
                caption=caption,
            )
        elif message_type == "audio":
            await client.send_audio(
                chat_id=destination_chat,
                audio=str(file_path),
                caption=caption,
            )
        elif message_type == "voice":
            await client.send_voice(
                chat_id=destination_chat,
                voice=str(file_path),
                caption=caption,
            )
        else:
            # Default to document
            await client.send_document(
                chat_id=destination_chat,
                document=str(file_path),
                caption=caption,
            )
        
        log_operation_success(logger, "upload_media", file_path=file_path.name, message_type=message_type)
        
    except Exception as e:
        log_operation_error(logger, "upload_media", e, file_path=file_path.name, message_type=message_type)
        raise


async def download_process_upload(
    client: Client,
    message: Message,
    destination_chat: int,
    download_path: Path,
    delay_seconds: float = 2.0
) -> None:
    """Process a message using the download-upload strategy.
    
    This function implements the cycle: Download -> Process -> Upload -> Delete
    to minimize disk usage and ensure atomic processing of each message.
    
    Args:
        client: The Pyrogram client.
        message: The message to process.
        destination_chat: The destination chat ID.
        download_path: Directory to save temporary files.
        delay_seconds: Delay in seconds between operations to avoid FloodWait.
    """
    downloaded_files = []
    
    try:
        log_operation_start(logger, "download_process_upload", message_id=message.id, destination_chat=destination_chat)
        
        # Step 1: Download the media
        downloaded_path = await download_media(client, message, download_path, message.id)
        
        if not downloaded_path:
            logger.warning(f"Failed to download message {message.id}, skipping")
            return
        
        downloaded_files.append(downloaded_path)
        
        # Step 2: Determine message type and caption
        caption = get_caption(message)
        message_type = "document"  # default
        
        if hasattr(message, 'video') and message.video:
            message_type = "video"
        elif hasattr(message, 'photo') and message.photo:
            message_type = "photo"
        elif hasattr(message, 'audio') and message.audio:
            message_type = "audio"
        elif hasattr(message, 'voice') and message.voice:
            message_type = "voice"
        
        # Step 3: Upload the original media
        await upload_media(client, downloaded_path, destination_chat, caption, message_type)
        
        # Step 4: Extract and upload audio for videos
        if message_type == "video" and downloaded_path.suffix.lower() in ['.mp4', '.mov', '.avi']:
            try:
                audio_path, _ = extract_audio_from_video(str(downloaded_path))
                audio_file_path = Path(audio_path)
                
                if audio_file_path.exists():
                    downloaded_files.append(audio_file_path)
                    
                    # Upload the extracted audio
                    await upload_media(
                        client,
                        audio_file_path,
                        destination_chat,
                        f"{caption or ''} (Audio extraído)" if caption else "Audio extraído",
                        "audio"
                    )
                    
                    logger.info(f"✅ Successfully uploaded extracted audio for message {message.id}")
                    
            except Exception as e:
                logger.warning(f"Failed to extract/upload audio for message {message.id}: {e}")
        
        # Step 5: Apply delay to avoid FloodWait
        if delay_seconds > 0:
            await asyncio.sleep(delay_seconds)
        
        log_operation_success(logger, "download_process_upload", message_id=message.id, destination_chat=destination_chat)
        
    except Exception as e:
        log_operation_error(logger, "download_process_upload", e, message_id=message.id, destination_chat=destination_chat)
        raise
        
    finally:
        # Step 6: Clean up downloaded files
        for file_path in downloaded_files:
            if file_path and file_path.exists():
                delete_local_media(file_path) 