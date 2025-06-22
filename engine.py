"""
Cloning engine for Clonechat.
"""
import asyncio
import logging
import time
from pathlib import Path
from typing import Dict, Any, Optional
from pyrogram import Client
from pyrogram.errors import ChatForwardsRestricted, FloodWait, ChannelInvalid, PeerIdInvalid

from config import Config
from database import init_db, get_task, create_task, update_strategy, update_progress
from processor import forward_message, download_process_upload
from logging_config import (
    get_logger,
    log_operation_start,
    log_operation_success,
    log_operation_error,
    log_strategy_detection,
    log_channel_creation,
    log_database_operation,
    log_configuration,
    log_progress
)

logger = get_logger(__name__)


def delete_task(origin_id: int) -> None:
    """
    Delete a sync task from the database.
    
    Args:
        origin_id: The origin chat ID.
    """
    import sqlite3
    from pathlib import Path
    
    db_path = Path("data/clonechat.db")
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    try:
        cursor.execute("DELETE FROM SyncTasks WHERE origin_chat_id = ?", (origin_id,))
        conn.commit()
        log_database_operation(logger, "delete_task", origin_chat_id=origin_id)
    except sqlite3.Error as e:
        log_operation_error(logger, "delete_task", e, origin_chat_id=origin_id)
        raise
    finally:
        conn.close()


def save_channel_link(origin_title: str, dest_chat_id: int) -> None:
    """
    Save the cloned channel link to links_canais.txt.
    
    Args:
        origin_title: The title of the origin channel.
        dest_chat_id: The destination channel ID.
    """
    try:
        logger.info(f"📝 Starting to save channel link for: {origin_title} (ID: {dest_chat_id})")
        
        # Generate the channel link
        channel_link = f"https://t.me/c/{str(dest_chat_id)[4:]}/1"
        logger.info(f"🔗 Generated channel link: {channel_link}")
        
        # Create the links file if it doesn't exist
        links_file = Path("links_canais.txt")
        logger.info(f"📄 Writing to file: {links_file.absolute()}")
        
        # Write the channel info
        with open(links_file, 'a', encoding='utf-8') as f:
            f.write(f"{origin_title}\n")
            f.write(f"{channel_link}\n")
            f.write("-" * 50 + "\n")  # Separator
        
        logger.info(f"✅ Channel link saved successfully: {origin_title} -> {channel_link}")
        
    except Exception as e:
        logger.error(f"❌ Failed to save channel link: {e}")
        logger.error(f"❌ Error details: origin_title='{origin_title}', dest_chat_id={dest_chat_id}")
        raise


async def leave_origin_channel(client: Client, origin_chat_id: int, origin_title: str) -> None:
    """
    Leave the origin channel after cloning is complete.
    
    Args:
        client: The Pyrogram client.
        origin_chat_id: The origin chat ID.
        origin_title: The title of the origin channel.
    """
    try:
        log_operation_start(logger, "leave_origin_channel", origin_chat_id=origin_chat_id, origin_title=origin_title)
        
        # Leave the channel
        await client.leave_chat(origin_chat_id)
        
        logger.info(f"👋 Left origin channel: {origin_title} (ID: {origin_chat_id})")
        log_operation_success(logger, "leave_origin_channel", origin_chat_id=origin_chat_id, origin_title=origin_title)
        
    except Exception as e:
        log_operation_error(logger, "leave_origin_channel", e, origin_chat_id=origin_chat_id, origin_title=origin_title)
        logger.warning(f"⚠️ Failed to leave origin channel {origin_title}: {e}")


class ClonerEngine:
    """
    Main cloning engine that handles automatic strategy detection and chat synchronization.
    """
    
    def __init__(self, config: Config, client: Client, force_download: bool = False):
        """
        Initialize the ClonerEngine.
        
        Args:
            config: Configuration object with Telegram credentials and settings.
            client: Pyrogram client instance.
            force_download: If True, force download_upload strategy for audio extraction.
        """
        self.config = config
        self.client = client
        self.force_download = force_download
        self.logger = get_logger(__name__)
        
        # Log configuration
        log_configuration(
            logger,
            telegram_api_id=config.telegram_api_id,
            cloner_delay_seconds=config.cloner_delay_seconds,
            cloner_download_path=config.cloner_download_path
        )
        
        # Initialize database
        init_db()
        log_database_operation(logger, "init_db")
        
        # Ensure download directory exists
        self.download_path = Path(config.cloner_download_path)
        self.download_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"📁 Download directory ready: {self.download_path}")
        
        if force_download:
            logger.info("🔧 Force download mode enabled - will use download_upload strategy for audio extraction")
        
    async def get_or_create_sync_task(self, origin_chat_id: int, restart: bool = False) -> Dict[str, Any]:
        """
        Get existing sync task or create a new one with destination channel.
        
        Args:
            origin_chat_id: The origin chat ID.
            restart: If True, delete existing task and create new one.
            
        Returns:
            Dict containing task information.
        """
        log_operation_start(logger, "get_or_create_sync_task", origin_chat_id=origin_chat_id, restart=restart)
        
        # Check if task already exists
        existing_task = get_task(origin_chat_id)
        
        if restart and existing_task:
            logger.info(f"🔄 Restart mode: deleting existing task for origin_chat_id={origin_chat_id}")
            delete_task(origin_chat_id)
            existing_task = None
        
        if existing_task:
            logger.info(f"📋 Found existing task for origin_chat_id={origin_chat_id}")
            log_operation_success(logger, "get_or_create_sync_task", origin_chat_id=origin_chat_id, task_exists=True)
            return existing_task
        
        # Get origin chat information
        try:
            logger.info(f"Obtendo dados do canal de origem(ID: {origin_chat_id})")
            origin_chat = await self.client.get_chat(origin_chat_id)
            origin_title = origin_chat.title
            logger.info(f"📢 Origin chat: {origin_title} (ID: {origin_chat_id})")
        except (ChannelInvalid, PeerIdInvalid) as e:
            log_operation_error(logger, "get_or_create_sync_task", e, origin_chat_id=origin_chat_id)
            raise ValueError(f"Cannot access origin chat {origin_chat_id}: {e}")
        
        # Create destination channel
        dest_chat_id = await self.create_destination_channel(origin_title)
        
        # Create task in database
        create_task(origin_chat_id, origin_title, dest_chat_id)
        log_database_operation(logger, "create_task", origin_chat_id=origin_chat_id, dest_chat_id=dest_chat_id)
        
        # Determine strategy
        strategy = await self.determine_strategy(origin_chat_id)
        update_strategy(origin_chat_id, strategy)
        log_database_operation(logger, "update_strategy", origin_chat_id=origin_chat_id, strategy=strategy)
        
        # Get updated task
        task = get_task(origin_chat_id)
        if not task:
            log_operation_error(logger, "get_or_create_sync_task", RuntimeError("Failed to create task"), origin_chat_id=origin_chat_id)
            raise RuntimeError("Failed to create task in database")
        
        log_operation_success(logger, "get_or_create_sync_task", origin_chat_id=origin_chat_id, dest_chat_id=dest_chat_id, strategy=strategy)
        return task
    
    async def determine_strategy(self, origin_chat_id: int) -> str:
        """
        Determine the best cloning strategy by testing forward restrictions.
        
        Args:
            origin_chat_id: The origin chat ID.
            
        Returns:
            Strategy string: 'forward' or 'download_upload'.
        """
        log_operation_start(logger, "determine_strategy", origin_chat_id=origin_chat_id)
        
        # If force_download is enabled, always use download_upload strategy
        if self.force_download:
            logger.info("🔧 Force download mode: using download_upload strategy")
            log_strategy_detection(logger, "download_upload", origin_chat_id)
            return "download_upload"
        
        try:
            # Try to get a recent message to test forwarding
            test_message = None
            async for message in self.client.get_chat_history(origin_chat_id, limit=1):
                test_message = message
            
            if not test_message:
                logger.warning("⚠️ No messages found to test strategy, defaulting to download_upload")
                log_strategy_detection(logger, "download_upload", origin_chat_id)
                return "download_upload"
            
            # Try to forward the message to ourselves to test restrictions
            try:
                await self.client.forward_messages(
                    chat_id="me",
                    from_chat_id=origin_chat_id,
                    message_ids=test_message.id
                )
                logger.info("✅ Forward strategy available")
                log_strategy_detection(logger, "forward", origin_chat_id)
                return "forward"
                
            except ChatForwardsRestricted:
                logger.info("🚫 Forward restricted, using download_upload strategy")
                log_strategy_detection(logger, "download_upload", origin_chat_id)
                return "download_upload"
                
            except Exception as e:
                logger.warning(f"⚠️ Error testing forward strategy: {e}, defaulting to download_upload")
                log_strategy_detection(logger, "download_upload", origin_chat_id)
                return "download_upload"
                
        except Exception as e:
            logger.error(f"❌ Error determining strategy: {e}, defaulting to download_upload")
            log_strategy_detection(logger, "download_upload", origin_chat_id)
            return "download_upload"
    
    async def create_destination_channel(self, origin_title: str) -> int:
        """
        Create a destination channel with [CLONE] prefix.
        
        Args:
            origin_title: The title of the origin channel.
            
        Returns:
            The ID of the created destination channel.
        """
        log_operation_start(logger, "create_destination_channel", origin_title=origin_title)
        
        dest_title = origin_title
        
        try:
            # Create the channel
            dest_chat = await self.client.create_channel(
                title=dest_title,
                description=f"Cloned from {origin_title}"
            )
            
            dest_chat_id = dest_chat.id
            log_channel_creation(logger, dest_chat_id, dest_title)
            log_operation_success(logger, "create_destination_channel", channel_id=dest_chat_id, channel_title=dest_title)
            
            return dest_chat_id
            
        except Exception as e:
            log_operation_error(logger, "create_destination_channel", e, origin_title=origin_title)
            raise
    
    async def sync_chat(self, origin_chat_id: int, restart: bool = False) -> None:
        """
        Main synchronization loop for a chat.
        
        Args:
            origin_chat_id: The origin chat ID to sync.
            restart: If True, restart from the beginning (delete existing task).
        """
        log_operation_start(logger, "sync_chat", origin_chat_id=origin_chat_id, restart=restart)
        
        # Get or create sync task
        task = await self.get_or_create_sync_task(origin_chat_id, restart=restart)
        
        origin_chat_id = task['origin_chat_id']
        dest_chat_id = task['destination_chat_id']
        origin_title = task['origin_chat_title']
        strategy = task['cloning_strategy']
        last_synced_id = task['last_synced_message_id']
        
        # Criar pasta de download específica para esta tarefa
        safe_title = "".join(c for c in origin_title if c.isalnum() or c in (' ', '_')).rstrip()
        download_path = self.download_path / f"{origin_chat_id} - {safe_title}"
        download_path.mkdir(parents=True, exist_ok=True)

        logger.info(f"🚀 Starting sync: origin={origin_chat_id}, dest={dest_chat_id}, strategy={strategy}")
        
        try:
            # Get the last message ID to determine sync range
            last_message = None
            async for message in self.client.get_chat_history(origin_chat_id, limit=1):
                last_message = message
            
            if not last_message:
                logger.warning("⚠️ No messages found in origin chat")
                # Still perform post-cloning actions even if no messages
                await self._post_cloning_actions(origin_chat_id, origin_title, dest_chat_id)
                return
            
            last_message_id = last_message.id
            logger.info(f"📊 Sync range: {last_synced_id + 1} to {last_message_id}")
            
            # Calculate total messages to process
            total_messages = last_message_id - last_synced_id
            if total_messages <= 0:
                logger.info("✅ No new messages to sync")
                # Still perform post-cloning actions even if no new messages
                await self._post_cloning_actions(origin_chat_id, origin_title, dest_chat_id)
                return
            
            # Main sync loop
            processed_count = 0
            for message_id in range(last_synced_id + 1, last_message_id + 1):
                try:
                    # Get the message
                    message = await self.client.get_messages(origin_chat_id, message_id)
                    
                    if not message or message.empty:
                        logger.debug(f"⏭️ Skipping empty message {message_id}")
                        continue
                    
                    # Process message based on strategy using processor functions
                    if strategy == "forward":
                        await self._forward_message(message, dest_chat_id)
                    else:  # download_upload
                        await self._download_upload_message(message, dest_chat_id, download_path)
                    
                    # Update progress only if processing was successful
                    update_progress(origin_chat_id, message_id)
                    processed_count += 1
                    
                    # Log progress
                    if processed_count % 10 == 0:  # Log every 10 messages
                        log_progress(logger, processed_count, total_messages, "Message processing")
                    
                    # Delay between messages
                    await asyncio.sleep(self.config.cloner_delay_seconds)
                    
                except FloodWait as e:
                    logger.warning(f"⏳ FloodWait: waiting {e.value} seconds")
                    await asyncio.sleep(e.value)
                    # Don't increment processed_count for FloodWait, retry the same message
                    continue
                    
                except Exception as e:
                    log_operation_error(logger, "sync_chat_message", e, message_id=message_id, origin_chat_id=origin_chat_id)
                    logger.error(f"❌ Failed to process message {message_id}, skipping to next message")
                    # Don't increment processed_count for failed messages
                    continue
            
            log_operation_success(logger, "sync_chat", origin_chat_id=origin_chat_id, processed_messages=processed_count, total_messages=total_messages)
            logger.info(f"✅ Sync completed for chat {origin_chat_id}: {processed_count}/{total_messages} messages processed")
            
            # Post-cloning actions
            await self._post_cloning_actions(origin_chat_id, origin_title, dest_chat_id)
            
        except Exception as e:
            log_operation_error(logger, "sync_chat", e, origin_chat_id=origin_chat_id)
            raise
    
    async def _post_cloning_actions(self, origin_chat_id: int, origin_title: str, dest_chat_id: int) -> None:
        """
        Perform post-cloning actions: save channel link and leave origin channel.
        
        Args:
            origin_chat_id: The origin chat ID.
            origin_title: The title of the origin channel.
            dest_chat_id: The destination channel ID.
        """
        try:
            log_operation_start(logger, "post_cloning_actions", origin_chat_id=origin_chat_id, dest_chat_id=dest_chat_id)
            
            # Save channel link to file
            save_channel_link(origin_title, dest_chat_id)
            
            # Leave the origin channel
            await leave_origin_channel(self.client, origin_chat_id, origin_title)
            
            logger.info(f"🎉 Post-cloning actions completed for {origin_title}")
            log_operation_success(logger, "post_cloning_actions", origin_chat_id=origin_chat_id, dest_chat_id=dest_chat_id)
            
        except Exception as e:
            log_operation_error(logger, "post_cloning_actions", e, origin_chat_id=origin_chat_id, dest_chat_id=dest_chat_id)
            logger.warning(f"⚠️ Some post-cloning actions failed: {e}")
    
    async def _forward_message(self, message, dest_chat_id: int) -> None:
        """
        Forward a message using the forward strategy from processor.
        
        Args:
            message: The message to forward.
            dest_chat_id: Destination chat ID.
        """
        try:
            await forward_message(
                client=self.client,
                message=message,
                destination_chat=dest_chat_id,
                delay_seconds=self.config.cloner_delay_seconds
            )
        except Exception as e:
            log_operation_error(logger, "_forward_message", e, message_id=message.id, dest_chat_id=dest_chat_id)
            raise
    
    async def _download_upload_message(self, message, dest_chat_id: int, download_path: Path) -> None:
        """
        Download and upload a message using the download_upload strategy from processor.
        
        Args:
            message: The message to process.
            dest_chat_id: Destination chat ID.
            download_path: The specific directory to download files to for this task.
        """
        try:
            await download_process_upload(
                client=self.client,
                message=message,
                destination_chat=dest_chat_id,
                download_path=download_path,
                delay_seconds=self.config.cloner_delay_seconds
            )
        except Exception as e:
            log_operation_error(logger, "_download_upload_message", e, message_id=message.id, dest_chat_id=dest_chat_id)
            raise 