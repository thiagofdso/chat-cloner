"""
Cloning engine for Clonechat.
"""
import logging
import time
from typing import Dict, Any, Optional
from pyrogram import Client
from pyrogram.errors import ChatForwardsRestricted, FloodWait, ChannelInvalid, PeerIdInvalid

from config import Config
from database import init_db, get_task, create_task, update_strategy, update_progress


class ClonerEngine:
    """
    Main cloning engine that handles automatic strategy detection and chat synchronization.
    """
    
    def __init__(self, config: Config, client: Client):
        """
        Initialize the ClonerEngine.
        
        Args:
            config: Configuration object with Telegram credentials and settings.
            client: Pyrogram client instance.
        """
        self.config = config
        self.client = client
        self.logger = logging.getLogger(__name__)
        
        # Initialize database
        init_db()
        
    def get_or_create_sync_task(self, origin_chat_id: int) -> Dict[str, Any]:
        """
        Get existing sync task or create a new one with destination channel.
        
        Args:
            origin_chat_id: The origin chat ID.
            
        Returns:
            Dict containing task information.
        """
        # Check if task already exists
        existing_task = get_task(origin_chat_id)
        if existing_task:
            self.logger.info(f"Found existing task for origin_chat_id={origin_chat_id}")
            return existing_task
        
        # Get origin chat information
        try:
            origin_chat = self.client.get_chat(origin_chat_id)
            origin_title = origin_chat.title
        except (ChannelInvalid, PeerIdInvalid) as e:
            raise ValueError(f"Cannot access origin chat {origin_chat_id}: {e}")
        
        # Create destination channel
        dest_chat_id = self.create_destination_channel(origin_title)
        
        # Create task in database
        create_task(origin_chat_id, origin_title, dest_chat_id)
        
        # Determine strategy
        strategy = self.determine_strategy(origin_chat_id)
        update_strategy(origin_chat_id, strategy)
        
        # Get updated task
        task = get_task(origin_chat_id)
        if not task:
            raise RuntimeError("Failed to create task in database")
            
        self.logger.info(f"Created new task: origin={origin_chat_id}, dest={dest_chat_id}, strategy={strategy}")
        
        return task
    
    def determine_strategy(self, origin_chat_id: int) -> str:
        """
        Determine the best cloning strategy by testing forward restrictions.
        
        Args:
            origin_chat_id: The origin chat ID.
            
        Returns:
            Strategy string: 'forward' or 'download_upload'.
        """
        self.logger.info(f"Determining strategy for chat {origin_chat_id}")
        
        try:
            # Try to get a recent message to test forwarding
            messages = self.client.get_chat_history(origin_chat_id, limit=1)
            test_message = next(messages, None)
            
            if not test_message:
                self.logger.warning("No messages found to test strategy, defaulting to download_upload")
                return "download_upload"
            
            # Try to forward the message to ourselves to test restrictions
            try:
                self.client.forward_messages(
                    chat_id="me",
                    from_chat_id=origin_chat_id,
                    message_ids=test_message.id
                )
                self.logger.info("Forward strategy available")
                return "forward"
                
            except ChatForwardsRestricted:
                self.logger.info("Forward restricted, using download_upload strategy")
                return "download_upload"
                
            except Exception as e:
                self.logger.warning(f"Error testing forward strategy: {e}, defaulting to download_upload")
                return "download_upload"
                
        except Exception as e:
            self.logger.error(f"Error determining strategy: {e}, defaulting to download_upload")
            return "download_upload"
    
    def create_destination_channel(self, origin_title: str) -> int:
        """
        Create a destination channel with [CLONE] prefix.
        
        Args:
            origin_title: The title of the origin channel.
            
        Returns:
            The ID of the created destination channel.
        """
        dest_title = f"[CLONE] {origin_title}"
        
        try:
            # Create the channel
            dest_chat = self.client.create_channel(
                title=dest_title,
                description=f"Cloned from {origin_title}"
            )
            
            dest_chat_id = dest_chat.id
            self.logger.info(f"Created destination channel: {dest_title} (ID: {dest_chat_id})")
            
            return dest_chat_id
            
        except Exception as e:
            self.logger.error(f"Error creating destination channel: {e}")
            raise
    
    def sync_chat(self, origin_chat_id: int) -> None:
        """
        Main synchronization loop for a chat.
        
        Args:
            origin_chat_id: The origin chat ID to sync.
        """
        # Get or create sync task
        task = self.get_or_create_sync_task(origin_chat_id)
        
        origin_chat_id = task['origin_chat_id']
        dest_chat_id = task['destination_chat_id']
        strategy = task['cloning_strategy']
        last_synced_id = task['last_synced_message_id']
        
        self.logger.info(f"Starting sync: origin={origin_chat_id}, dest={dest_chat_id}, strategy={strategy}")
        
        try:
            # Get the last message ID to determine sync range
            messages = self.client.get_chat_history(origin_chat_id, limit=1)
            last_message = next(messages, None)
            
            if not last_message:
                self.logger.warning("No messages found in origin chat")
                return
            
            last_message_id = last_message.id
            self.logger.info(f"Sync range: {last_synced_id + 1} to {last_message_id}")
            
            # Main sync loop
            for message_id in range(last_synced_id + 1, last_message_id + 1):
                try:
                    # Get the message
                    message = self.client.get_messages(origin_chat_id, message_id)
                    
                    if not message or message.empty:
                        self.logger.debug(f"Skipping empty message {message_id}")
                        continue
                    
                    # Process message based on strategy
                    if strategy == "forward":
                        self._forward_message(message, dest_chat_id)
                    else:  # download_upload
                        self._download_upload_message(message, dest_chat_id)
                    
                    # Update progress
                    update_progress(origin_chat_id, message_id)
                    
                    # Log progress
                    if message_id % 10 == 0:  # Log every 10 messages
                        self.logger.info(f"Progress: {message_id}/{last_message_id}")
                    
                    # Delay between messages
                    time.sleep(self.config.cloner_delay_seconds)
                    
                except FloodWait as e:
                    self.logger.warning(f"FloodWait: waiting {e.value} seconds")
                    time.sleep(e.value)
                    continue
                    
                except Exception as e:
                    self.logger.error(f"Error processing message {message_id}: {e}")
                    continue
            
            self.logger.info(f"Sync completed for chat {origin_chat_id}")
            
        except Exception as e:
            self.logger.error(f"Error in sync_chat: {e}")
            raise
    
    def _forward_message(self, message, dest_chat_id: int) -> None:
        """
        Forward a message using the forward strategy.
        
        Args:
            message: The message to forward.
            dest_chat_id: Destination chat ID.
        """
        try:
            self.client.forward_messages(
                chat_id=dest_chat_id,
                from_chat_id=message.chat.id,
                message_ids=message.id
            )
        except Exception as e:
            self.logger.error(f"Error forwarding message: {e}")
            raise
    
    def _download_upload_message(self, message, dest_chat_id: int) -> None:
        """
        Download and upload a message using the download_upload strategy.
        
        Args:
            message: The message to process.
            dest_chat_id: Destination chat ID.
        """
        # This will be implemented in the processor.py module
        # For now, just log that we would process it
        self.logger.debug(f"Would download/upload message {message.id} (to be implemented in processor.py)")
        pass 