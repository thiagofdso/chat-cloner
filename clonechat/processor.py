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

from .logging_config import (
    get_logger, 
    log_operation_start, 
    log_operation_success, 
    log_operation_error,
    log_media_operation,
    log_file_operation,
    log_ffmpeg_operation,
    log_cleanup_operation
)
from .retry_utils import retry_telegram_operation, retry_file_operation

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
async def forward_photo(client: Client, message: Message, destination_chat: int) -> int:
    """Forward a photo message.
    
    Args:
        client: The Pyrogram client.
        message: The message containing the photo.
        destination_chat: The destination chat ID.
        
    Returns:
        The ID of the sent message.
    """
    log_media_operation(logger, "Forwarding", message.id, "photo")
    caption = get_caption(message)
    photo_id = message.photo.file_id
    
    sent_message = await client.send_photo(
        chat_id=destination_chat,
        photo=photo_id,
        caption=caption,
    )
    
    return sent_message.id


@retry_telegram_operation(max_retries=3, base_delay=2.0)
async def forward_text(client: Client, message: Message, destination_chat: int) -> int:
    """Forward a text message.
    
    Args:
        client: The Pyrogram client.
        message: The message containing the text.
        destination_chat: The destination chat ID.
        
    Returns:
        The ID of the sent message.
    """
    log_media_operation(logger, "Forwarding", message.id, "text")
    text = message.text.markdown
    
    sent_message = await client.send_message(
        chat_id=destination_chat,
        text=text,
        disable_notification=True,
        disable_web_page_preview=True,
    )
    
    return sent_message.id


@retry_telegram_operation(max_retries=3, base_delay=2.0)
async def forward_sticker(client: Client, message: Message, destination_chat: int) -> int:
    """Forward a sticker message.
    
    Args:
        client: The Pyrogram client.
        message: The message containing the sticker.
        destination_chat: The destination chat ID.
        
    Returns:
        The ID of the sent message.
    """
    log_media_operation(logger, "Forwarding", message.id, "sticker")
    sticker_id = message.sticker.file_id
    
    sent_message = await client.send_sticker(
        chat_id=destination_chat, 
        sticker=sticker_id
    )
    
    return sent_message.id


@retry_telegram_operation(max_retries=3, base_delay=2.0)
async def forward_document(client: Client, message: Message, destination_chat: int) -> int:
    """Forward a document message.
    
    Args:
        client: The Pyrogram client.
        message: The message containing the document.
        destination_chat: The destination chat ID.
        
    Returns:
        The ID of the sent message.
    """
    log_media_operation(logger, "Forwarding", message.id, "document")
    caption = get_caption(message)
    document_id = message.document.file_id
    
    sent_message = await client.send_document(
        chat_id=destination_chat,
        document=document_id,
        disable_notification=True,
        caption=caption,
    )
    
    return sent_message.id


@retry_telegram_operation(max_retries=3, base_delay=2.0)
async def forward_animation(client: Client, message: Message, destination_chat: int) -> int:
    """Forward an animation message.
    
    Args:
        client: The Pyrogram client.
        message: The message containing the animation.
        destination_chat: The destination chat ID.
        
    Returns:
        The ID of the sent message.
    """
    log_media_operation(logger, "Forwarding", message.id, "animation")
    caption = get_caption(message)
    animation_id = message.animation.file_id
    
    sent_message = await client.send_animation(
        chat_id=destination_chat,
        animation=animation_id,
        disable_notification=True,
        caption=caption,
    )
    
    return sent_message.id


@retry_telegram_operation(max_retries=3, base_delay=2.0)
async def forward_audio(client: Client, message: Message, destination_chat: int) -> int:
    """Forward an audio message.
    
    Args:
        client: The Pyrogram client.
        message: The message containing the audio.
        destination_chat: The destination chat ID.
        
    Returns:
        The ID of the sent message.
    """
    log_media_operation(logger, "Forwarding", message.id, "audio")
    caption = get_caption(message)
    audio_id = message.audio.file_id
    
    sent_message = await client.send_audio(
        chat_id=destination_chat,
        audio=audio_id,
        disable_notification=True,
        caption=caption,
    )
    
    return sent_message.id


@retry_telegram_operation(max_retries=3, base_delay=2.0)
async def forward_voice(client: Client, message: Message, destination_chat: int) -> int:
    """Forward a voice message.
    
    Args:
        client: The Pyrogram client.
        message: The message containing the voice.
        destination_chat: The destination chat ID.
        
    Returns:
        The ID of the sent message.
    """
    log_media_operation(logger, "Forwarding", message.id, "voice")
    caption = get_caption(message)
    voice_id = message.voice.file_id
    
    sent_message = await client.send_voice(
        chat_id=destination_chat,
        voice=voice_id,
        disable_notification=True,
        caption=caption,
    )
    
    return sent_message.id


@retry_telegram_operation(max_retries=3, base_delay=2.0)
async def forward_video_note(client: Client, message: Message, destination_chat: int) -> int:
    """Forward a video note message.
    
    Args:
        client: The Pyrogram client.
        message: The message containing the video note.
        destination_chat: The destination chat ID.
        
    Returns:
        The ID of the sent message.
    """
    log_media_operation(logger, "Forwarding", message.id, "video_note")
    video_note_id = message.video_note.file_id
    
    sent_message = await client.send_video_note(
        chat_id=destination_chat,
        video_note=video_note_id,
        disable_notification=True,
    )
    
    return sent_message.id


@retry_telegram_operation(max_retries=3, base_delay=2.0)
async def forward_video(client: Client, message: Message, destination_chat: int) -> int:
    """Forward a video message.
    
    Args:
        client: The Pyrogram client.
        message: The message containing the video.
        destination_chat: The destination chat ID.
        
    Returns:
        The ID of the sent message.
    """
    log_media_operation(logger, "Forwarding", message.id, "video")
    caption = get_caption(message)
    video_id = message.video.file_id
    
    sent_message = await client.send_video(
        chat_id=destination_chat,
        video=video_id,
        disable_notification=True,
        caption=caption,
    )
    
    return sent_message.id


@retry_telegram_operation(max_retries=3, base_delay=2.0)
async def forward_poll(client: Client, message: Message, destination_chat: int) -> int:
    """Forward a poll message.
    
    Args:
        client: The Pyrogram client.
        message: The message containing the poll.
        destination_chat: The destination chat ID.
        
    Returns:
        The ID of the sent message.
    """
    log_media_operation(logger, "Forwarding", message.id, "poll")
    if message.poll.type != "regular":
        raise ValueError("Only regular polls can be forwarded")
    
    sent_message = await client.send_poll(
        chat_id=destination_chat,
        question=message.poll.question,
        options=[option.text for option in message.poll.options],
        is_anonymous=message.poll.is_anonymous,
        allows_multiple_answers=message.poll.allows_multiple_answers,
        disable_notification=True,
    )
    
    return sent_message.id


async def forward_message(
    client: Client, 
    message: Message, 
    destination_chat: int, 
    delay_seconds: float = 2.0
) -> int:
    """Forward a message using the direct forward strategy.
    
    This function determines the message type and forwards it directly
    to the destination chat using the appropriate method.
    
    Args:
        client: The Pyrogram client.
        message: The message to forward.
        destination_chat: The destination chat ID.
        delay_seconds: Delay in seconds between operations to avoid FloodWait.
        
    Returns:
        The ID of the sent message.
    """
    try:
        log_operation_start(logger, "forward_message", message_id=message.id, destination_chat=destination_chat)
        
        # Get the appropriate forward function based on message type
        forward_func = get_sender(message)
        
        # Forward the message and get the sent message ID
        sent_message_id = await forward_func(client, message, destination_chat)
        
        log_operation_success(logger, "forward_message", message_id=message.id, destination_chat=destination_chat, sent_message_id=sent_message_id)
        
        # Apply delay to avoid FloodWait
        if delay_seconds > 0:
            await asyncio.sleep(delay_seconds)
            
        return sent_message_id
            
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
) -> int:
    """Upload media to a destination chat.
    
    Args:
        client: The Pyrogram client.
        file_path: Path to the file to upload.
        destination_chat: The destination chat ID.
        caption: Optional caption for the media.
        message_type: Type of media (video, document, photo, audio, voice).
        
    Returns:
        The ID of the sent message.
    """
    try:
        log_operation_start(logger, "upload_media", file_path=file_path.name, message_type=message_type, destination_chat=destination_chat)
        
        sent_message = None
        if message_type == "video":
            sent_message = await client.send_video(
                chat_id=destination_chat,
                video=str(file_path),
                caption=caption,
                supports_streaming=True,
            )
        elif message_type == "document":
            sent_message = await client.send_document(
                chat_id=destination_chat,
                document=str(file_path),
                caption=caption,
            )
        elif message_type == "photo":
            sent_message = await client.send_photo(
                chat_id=destination_chat,
                photo=str(file_path),
                caption=caption,
            )
        elif message_type == "audio":
            sent_message = await client.send_audio(
                chat_id=destination_chat,
                audio=str(file_path),
                caption=caption,
            )
        elif message_type == "voice":
            sent_message = await client.send_voice(
                chat_id=destination_chat,
                voice=str(file_path),
                caption=caption,
            )
        else:
            # Default to document
            sent_message = await client.send_document(
                chat_id=destination_chat,
                document=str(file_path),
                caption=caption,
            )
        
        log_operation_success(logger, "upload_media", file_path=file_path.name, message_type=message_type)
        return sent_message.id
        
    except Exception as e:
        log_operation_error(logger, "upload_media", e, file_path=file_path.name, message_type=message_type)
        raise


async def _get_message_caption(message: Message) -> str:
    """Extracts the caption from a message, returning an empty string if none exists."""
    return message.caption or ""


async def _extract_audio(message: Message, file_path: Path) -> None:
    """
    Extracts audio from a video file if the message is a video.
    The audio file is saved in the same directory with a .mp3 extension.
    """
    if not message.video:
        logger.debug(f"⏭️ Skipping audio extraction for non-video message {message.id}")
        return

    try:
        log_operation_start(logger, "extract_audio", message_id=message.id, video_file=file_path.name)
        output_path = file_path.with_suffix(".mp3")
        
        logger.info(f"🎬 Starting audio extraction: {file_path.name} -> {output_path.name}")
        
        # Use -y to overwrite existing file, -vn to disable video
        command = [
            "ffmpeg",
            "-y",
            "-i",
            str(file_path),
            "-vn",
            "-acodec",
            "libmp3lame",
            "-q:a",
            "2",
            str(output_path),
        ]
        
        logger.debug(f"🔧 FFmpeg command: {' '.join(command)}")
        
        result = subprocess.run(
            command, check=True, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW
        )
        
        if output_path.exists():
            file_size = output_path.stat().st_size
            logger.info(f"✅ Audio extracted successfully for message {message.id}: {output_path.name} ({file_size} bytes)")
            log_operation_success(logger, "extract_audio", message_id=message.id, audio_file=output_path.name, file_size=file_size)
        else:
            logger.error(f"❌ Audio file was not created: {output_path}")
            raise FileNotFoundError(f"Audio file was not created: {output_path}")

    except FileNotFoundError:
        logger.error(
            "❌ FFmpeg not found. Please install it and ensure it's in your system's PATH."
        )
        log_operation_error(logger, "extract_audio", FileNotFoundError("FFmpeg not found"), message_id=message.id)
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ FFmpeg error extracting audio for message {message.id}: {e.stderr}")
        log_operation_error(logger, "extract_audio", e, message_id=message.id, stderr=e.stderr)
    except Exception as e:
        logger.error(f"❌ Unexpected error extracting audio for message {message.id}: {e}")
        log_operation_error(logger, "extract_audio", e, message_id=message.id)


async def _upload_media(
    client: Client, chat_id: int, file_path: Path, caption: str
) -> int:
    """
    Uploads a media file to the specified chat, selecting the correct
    Pyrogram method based on the file type.
    
    Args:
        client: The Pyrogram client.
        chat_id: The destination chat ID.
        file_path: Path to the file to upload.
        caption: Caption for the media.
        
    Returns:
        The ID of the sent message.
    """
    log_operation_start(
        logger, "upload_media", file_path=str(file_path), chat_id=chat_id
    )
    
    try:
        sent_message = None
        if file_path.suffix.lower() in [".jpg", ".jpeg", ".png"]:
            sent_message = await client.send_photo(chat_id, photo=str(file_path), caption=caption)
        elif file_path.suffix.lower() in [".mp4", ".mkv", ".avi", ".mov"]:
            sent_message = await client.send_video(chat_id, video=str(file_path), caption=caption)
        elif file_path.suffix.lower() in [".mp3", ".ogg", ".wav", ".flac"]:
            sent_message = await client.send_audio(chat_id, audio=str(file_path), caption=caption)
        else:
            sent_message = await client.send_document(chat_id, document=str(file_path), caption=caption)
        
        logger.info(f"✅ Uploaded {file_path.name} to {chat_id}")
        return sent_message.id
    
    except Exception as e:
        log_operation_error(logger, "upload_media", e, file_path=str(file_path))
        raise # Re-raise to be handled by the main processor


@retry_telegram_operation(max_retries=3, base_delay=2.0)
async def get_pinned_messages(client: Client, chat_id: int) -> list[Message]:
    """
    Get pinned message from a chat.
    
    Args:
        client: The Pyrogram client.
        chat_id: The chat ID to get pinned message from.
        
    Returns:
        List containing the pinned message, or empty list if no pinned message.
    """
    try:
        log_operation_start(logger, "get_pinned_messages", chat_id=chat_id)
        
        # Get chat info and check for pinned message
        chat = await client.get_chat(chat_id)
        if chat.pinned_message:
            logger.info(f"📌 Found pinned message: {chat.pinned_message.id}")
            log_operation_success(logger, "get_pinned_messages", chat_id=chat_id, pinned_count=1)
            return [chat.pinned_message]
        else:
            logger.info(f"📌 No pinned message found in chat {chat_id}")
            log_operation_success(logger, "get_pinned_messages", chat_id=chat_id, pinned_count=0)
            return []
        
    except Exception as e:
        log_operation_error(logger, "get_pinned_messages", e, chat_id=chat_id)
        logger.error(f"❌ Error getting pinned message: {e}")
        return []


@retry_telegram_operation(max_retries=3, base_delay=2.0)
async def pin_corresponding_messages(
    client: Client, 
    origin_chat_id: int, 
    dest_chat_id: int, 
    message_mapping: dict[int, int]
) -> None:
    """
    Pin messages in destination chat that correspond to pinned messages in origin.
    
    Args:
        client: The Pyrogram client.
        origin_chat_id: The origin chat ID.
        dest_chat_id: The destination chat ID.
        message_mapping: Mapping of origin message IDs to destination message IDs.
    """
    try:
        log_operation_start(logger, "pin_corresponding_messages", origin_chat_id=origin_chat_id, dest_chat_id=dest_chat_id)
        
        # Get pinned messages from origin
        pinned_messages = await get_pinned_messages(client, origin_chat_id)
        
        if not pinned_messages:
            logger.info("📌 No pinned messages found in origin channel")
            log_operation_success(logger, "pin_corresponding_messages", origin_chat_id=origin_chat_id, pinned_count=0)
            return
            
        pinned_count = 0
        # Pin corresponding messages in destination
        for pinned_msg in pinned_messages:
            if pinned_msg.id in message_mapping:
                dest_msg_id = message_mapping[pinned_msg.id]
                await client.pin_chat_message(dest_chat_id, dest_msg_id)
                logger.info(f"📌 Pinned message {dest_msg_id} (origin: {pinned_msg.id})")
                pinned_count += 1
            else:
                logger.warning(f"⚠️ Pinned message {pinned_msg.id} not found in mapping")
        
        logger.info(f"✅ Successfully pinned {pinned_count}/{len(pinned_messages)} messages")
        log_operation_success(logger, "pin_corresponding_messages", origin_chat_id=origin_chat_id, dest_chat_id=dest_chat_id, pinned_count=pinned_count)
                
    except Exception as e:
        log_operation_error(logger, "pin_corresponding_messages", e, origin_chat_id=origin_chat_id, dest_chat_id=dest_chat_id)
        logger.error(f"❌ Error pinning messages: {e}")


async def download_process_upload(
    client: Client,
    message: Message,
    destination_chat: int,
    download_path: Path,
    delay_seconds: int,
) -> int:
    """
    Processes a message, handling both text and media types.
    For media, downloads it, optionally extracts audio, and uploads the original media.
    For text, sends the text content.

    Args:
        client: The Pyrogram client.
        message: The message to process.
        destination_chat: The destination chat ID.
        download_path: The base directory for downloads for this task.
        delay_seconds: Delay after processing the message.
        
    Returns:
        The ID of the sent message.
    """
    log_operation_start(
        logger,
        "download_process_upload",
        message_id=message.id,
        destination_chat=destination_chat,
    )

    try:
        sent_message_id = 0  # Default value
        
        if message.text:
            # Handle text-only messages
            sent_message = await client.send_message(
                chat_id=destination_chat, text=message.text
            )
            sent_message_id = sent_message.id
            logger.info(f"✅ Sent text message {message.id} to {destination_chat}")
        
        elif message.media:
            # Handle media messages
            caption = await _get_message_caption(message)
            downloaded_path = await download_media(client, message, download_path, message.id)

            if downloaded_path:
                # Extração de áudio é um efeito colateral, não afeta o upload
                audio_path = None
                if message.video:
                    await _extract_audio(message, downloaded_path)
                    # Get the audio file path that was created
                    audio_path = downloaded_path.with_suffix(".mp3")

                sent_message_id = await _upload_media(
                    client, destination_chat, downloaded_path, caption
                )
                
                # Limpeza do arquivo baixado (apenas o arquivo original)
                if downloaded_path.exists():
                    os.remove(downloaded_path)
                    logger.info(f"🗑️ Cleaned up downloaded file: {downloaded_path}")
                
                # Preservar o arquivo de áudio extraído
                if audio_path and audio_path.exists():
                    logger.info(f"🎵 Audio file preserved: {audio_path}")

            else:
                 # Se download_media retornar None mas a mensagem for de mídia,
                 # pode ser um tipo não suportado ou um texto com formatação.
                 # Tentamos enviar o texto/caption, se houver.
                if caption:
                    sent_message = await client.send_message(chat_id=destination_chat, text=caption)
                    sent_message_id = sent_message.id
                    logger.info(f"✅ Sent caption for message {message.id} to {destination_chat}")

        return sent_message_id

    except Exception as e:
        log_operation_error(
            logger,
            "download_process_upload",
            e,
            message_id=message.id,
            destination_chat=destination_chat,
        )
        logger.error(f"❌ Failed to process message {message.id}: {e}")
        # Re-raise the exception to be handled by the caller
        raise
    finally:
        await asyncio.sleep(delay_seconds) 