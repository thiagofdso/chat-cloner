"""
Cloning engine for Clonechat.
"""
import asyncio
import logging
import time
from pathlib import Path
from typing import Dict, Any, Optional
from pyrogram import Client, enums
from pyrogram.errors import ChatForwardsRestricted, FloodWait, ChannelInvalid, PeerIdInvalid

from .config import Config
from .database import init_db, get_task, create_task, update_strategy, update_progress
from .processor import forward_message, download_process_upload, pin_corresponding_messages
from .logging_config import (
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


async def publish_channel_link(client: Client, origin_title: str, dest_chat_id: int, publish_chat_id: int, topic_id: Optional[int] = None) -> None:
    """
    Publish the cloned channel link to a group or channel.
    
    Args:
        client: The Pyrogram client.
        origin_title: The title of the origin channel.
        dest_chat_id: The destination channel ID.
        publish_chat_id: The chat ID where to publish the link.
        topic_id: The topic ID (for groups with topics).
    """
    try:
        logger.info(f"📢 Publishing channel link for: {origin_title} (ID: {dest_chat_id})")
        
        # Generate the invite link using Pyrogram
        try:
            invite_link = await client.export_chat_invite_link(dest_chat_id)
            logger.info(f"🔗 Generated invite link: {invite_link}")
        except Exception as e:
            logger.warning(f"⚠️ Could not generate invite link, using direct link: {e}")
            # Fallback to direct link if invite link generation fails
            invite_link = f"https://t.me/c/{str(dest_chat_id)[4:]}/1"
            logger.info(f"🔗 Using fallback direct link: {invite_link}")
        
        # Create the message text
        message_text = f"{origin_title}\n{invite_link}"
        
        # Prepare message parameters
        message_params = {
            "chat_id": publish_chat_id,
            "text": message_text
        }
        
        # Add topic_id if provided
        if topic_id:
            message_params["reply_to_message_id"] = topic_id
            logger.info(f"📝 Publishing to topic ID: {topic_id}")
        
        # Send the message
        await client.send_message(**message_params)
        
        logger.info(f"✅ Channel link published successfully: {origin_title} -> {invite_link}")
        
    except Exception as e:
        logger.error(f"❌ Failed to publish channel link: {e}")
        logger.error(f"❌ Error details: origin_title='{origin_title}', dest_chat_id={dest_chat_id}, publish_chat_id={publish_chat_id}")
        raise


async def save_channel_link(client: Client, origin_title: str, dest_chat_id: int) -> None:
    """
    Save the cloned channel link to links_canais.txt.
    
    Args:
        client: The Pyrogram client.
        origin_title: The title of the origin channel.
        dest_chat_id: The destination channel ID.
    """
    try:
        logger.info(f"📝 Starting to save channel link for: {origin_title} (ID: {dest_chat_id})")
        
        # Generate the invite link using Pyrogram
        try:
            invite_link = await client.export_chat_invite_link(dest_chat_id)
            logger.info(f"🔗 Generated invite link: {invite_link}")
        except Exception as e:
            logger.warning(f"⚠️ Could not generate invite link, using direct link: {e}")
            # Fallback to direct link if invite link generation fails
            invite_link = f"https://t.me/c/{str(dest_chat_id)[4:]}/1"
            logger.info(f"🔗 Using fallback direct link: {invite_link}")
        
        # Create the links file if it doesn't exist
        links_file = Path("links_canais.txt")
        logger.info(f"📄 Writing to file: {links_file.absolute()}")
        
        # Write the channel info
        with open(links_file, 'a', encoding='utf-8') as f:
            f.write(f"{origin_title}\n")
            f.write(f"{invite_link}\n")
            f.write("-" * 50 + "\n")  # Separator
        
        logger.info(f"✅ Channel link saved successfully: {origin_title} -> {invite_link}")
        
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
    
    def __init__(self, config: Config, client: Client, force_download: bool = False, leave_origin: bool = False, dest_chat_id: Optional[int] = None, publish_chat_id: Optional[int] = None, topic_id: Optional[int] = None):
        """
        Initialize the ClonerEngine.
        
        Args:
            config: Configuration object with Telegram credentials and settings.
            client: Pyrogram client instance.
            force_download: If True, force download_upload strategy for audio extraction.
            leave_origin: If True, leave the origin channel after cloning.
            dest_chat_id: Destination channel ID (if None, creates a new channel).
            publish_chat_id: Chat ID where to publish cloned channel links.
            topic_id: Topic ID for publishing in groups with topics.
        """
        self.config = config
        self.client = client
        self.force_download = force_download
        self.leave_origin = leave_origin
        self.dest_chat_id = dest_chat_id
        self.publish_chat_id = publish_chat_id
        self.topic_id = topic_id
        self.logger = get_logger(__name__)
        
        # Message ID mapping for pinned messages functionality
        self.message_mapping: dict[int, int] = {}
        
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
        
        if leave_origin:
            logger.info("👋 Leave origin mode enabled - will leave origin channel after cloning")
        
        if dest_chat_id:
            logger.info(f"🎯 Using existing destination channel: {dest_chat_id}")
        else:
            logger.info("🆕 Will create new destination channel")
        
        if publish_chat_id:
            logger.info(f"📢 Will publish links to chat: {publish_chat_id}")
            if topic_id:
                logger.info(f"📝 Will publish to topic: {topic_id}")
        else:
            logger.info("📄 Links will be saved to file only")
        
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
        
        # Create destination channel or use existing one
        if self.dest_chat_id:
            # Use existing destination channel
            dest_chat_id = self.dest_chat_id
            logger.info(f"🎯 Using existing destination channel: {dest_chat_id}")
            
            # Verify the destination channel exists and we have access
            try:
                dest_chat = await self.client.get_chat(dest_chat_id)
                logger.info(f"✅ Destination channel verified: {dest_chat.title} (ID: {dest_chat_id})")
            except (ChannelInvalid, PeerIdInvalid) as e:
                log_operation_error(logger, "get_or_create_sync_task", e, dest_chat_id=dest_chat_id)
                raise ValueError(f"Cannot access destination chat {dest_chat_id}: {e}")
        else:
            # Create new destination channel
            dest_chat_id = await self.create_destination_channel(origin_title, origin_chat_id)
        
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
    
    async def create_destination_channel(self, origin_title: str, origin_chat_id: int) -> int:
        """
        Create a destination channel with the same title and description as origin.
        
        Args:
            origin_title: The title of the origin channel.
            origin_chat_id: The origin chat ID to get description from.
            
        Returns:
            The ID of the created destination channel.
        """
        log_operation_start(logger, "create_destination_channel", origin_title=origin_title, origin_chat_id=origin_chat_id)
        
        dest_title = origin_title
        
        try:
            # Get origin channel info to copy description
            origin_chat = await self.client.get_chat(origin_chat_id)
            origin_description = origin_chat.description or ""
            
            logger.info(f"📝 Copying description from origin channel: {origin_description[:100]}...")
            
            # Create the channel with copied description
            dest_chat = await self.client.create_channel(
                title=dest_title,
                description=origin_description
            )
            
            dest_chat_id = dest_chat.id
            log_channel_creation(logger, dest_chat_id, dest_title)
            log_operation_success(logger, "create_destination_channel", channel_id=dest_chat_id, channel_title=dest_title, description_copied=True)
            
            return dest_chat_id
            
        except Exception as e:
            log_operation_error(logger, "create_destination_channel", e, origin_title=origin_title, origin_chat_id=origin_chat_id)
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
        logger.info(f"📌 Pinned messages functionality: ENABLED (will pin corresponding messages after clone)")
        logger.info(f"📝 Channel description copying: ENABLED (will copy description from origin channel)")
        
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
                        
                    # Skip service messages that have no content to process
                    if not message.text and not message.caption and not message.media:
                        logger.debug(f"⏭️ Skipping service message {message_id}")
                        # Service messages are considered "processed"
                        update_progress(origin_chat_id, message_id)
                        processed_count += 1
                        continue
                    
                    # Process message based on strategy using processor functions
                    sent_message_id = None
                    if strategy == "forward":
                        sent_message_id = await self._forward_message(message, dest_chat_id)
                    else:  # download_upload
                        sent_message_id = await self._download_upload_message(message, dest_chat_id, download_path)
                    
                    # Track message mapping for pinned messages functionality
                    if sent_message_id and sent_message_id > 0:
                        self.message_mapping[message_id] = sent_message_id
                        logger.debug(f"📝 Mapped message {message_id} -> {sent_message_id}")
                    
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
        Perform post-cloning actions: save channel link, publish link, pin corresponding messages, and optionally leave origin channel.
        
        Args:
            origin_chat_id: The origin chat ID.
            origin_title: The title of the origin channel.
            dest_chat_id: The destination channel ID.
        """
        try:
            log_operation_start(logger, "post_cloning_actions", origin_chat_id=origin_chat_id, dest_chat_id=dest_chat_id)
            
            # Save channel link to file
            await save_channel_link(self.client, origin_title, dest_chat_id)
            
            # Publish channel link if publish_chat_id is specified
            if self.publish_chat_id:
                await publish_channel_link(self.client, origin_title, dest_chat_id, self.publish_chat_id, self.topic_id)
            
            # Pin corresponding messages if we have a message mapping
            if self.message_mapping:
                logger.info(f"📌 Starting to pin corresponding messages (mapping: {len(self.message_mapping)} messages)")
                await pin_corresponding_messages(
                    client=self.client,
                    origin_chat_id=origin_chat_id,
                    dest_chat_id=dest_chat_id,
                    message_mapping=self.message_mapping
                )
            else:
                logger.info("📌 No message mapping available, skipping pinned messages")
            
            # Leave the origin channel only if leave_origin is enabled
            if self.leave_origin:
                await leave_origin_channel(self.client, origin_chat_id, origin_title)
            else:
                logger.info(f"👋 Staying in origin channel: {origin_title} (leave_origin=False)")
            
            logger.info(f"🎉 Post-cloning actions completed for {origin_title}")
            log_operation_success(logger, "post_cloning_actions", origin_chat_id=origin_chat_id, dest_chat_id=dest_chat_id)
            
        except Exception as e:
            log_operation_error(logger, "post_cloning_actions", e, origin_chat_id=origin_chat_id, dest_chat_id=dest_chat_id)
            logger.warning(f"⚠️ Some post-cloning actions failed: {e}")
    
    async def _forward_message(self, message, dest_chat_id: int) -> int:
        """
        Forward a message using the forward strategy from processor.
        
        Args:
            message: The message to forward.
            dest_chat_id: Destination chat ID.
            
        Returns:
            The ID of the sent message.
        """
        try:
            # Forward the message and get the sent message ID
            sent_message_id = await forward_message(
                client=self.client,
                message=message,
                destination_chat=dest_chat_id,
                delay_seconds=self.config.cloner_delay_seconds
            )
            
            return sent_message_id
            
        except Exception as e:
            log_operation_error(logger, "_forward_message", e, message_id=message.id, dest_chat_id=dest_chat_id)
            raise
    
    async def _download_upload_message(self, message, dest_chat_id: int, download_path: Path) -> int:
        """
        Download and upload a message using the download_upload strategy from processor.
        
        Args:
            message: The message to process.
            dest_chat_id: Destination chat ID.
            download_path: The specific directory to download files to for this task.
            
        Returns:
            The ID of the sent message.
        """
        try:
            sent_message_id = await download_process_upload(
                client=self.client,
                message=message,
                destination_chat=dest_chat_id,
                download_path=download_path,
                delay_seconds=self.config.cloner_delay_seconds
            )
            
            return sent_message_id
            
        except Exception as e:
            log_operation_error(logger, "_download_upload_message", e, message_id=message.id, dest_chat_id=dest_chat_id)
            raise 