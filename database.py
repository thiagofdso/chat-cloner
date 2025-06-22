"""
Database layer for Clonechat.
"""
import sqlite3
from typing import Optional, Dict, Any
from pathlib import Path

from logging_config import (
    get_logger, 
    log_database_operation, 
    log_operation_error,
    log_operation_start,
    log_operation_success
)

logger = get_logger(__name__)


def create_connection() -> sqlite3.Connection:
    """
    Create a connection to the SQLite database.
    
    Returns:
        sqlite3.Connection: Database connection.
    """
    db_path = Path("data/clonechat.db")
    db_path.parent.mkdir(exist_ok=True)
    
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row  # Enable column access by name
    return conn


def init_db() -> None:
    """
    Initialize the database with required tables.
    """
    log_operation_start(logger, "init_db")
    
    conn = create_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS SyncTasks (
                origin_chat_id INTEGER PRIMARY KEY,
                origin_chat_title TEXT,
                destination_chat_id INTEGER,
                cloning_strategy TEXT DEFAULT 'unknown',
                last_synced_message_id INTEGER DEFAULT 0
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS DownloadTasks (
                origin_chat_id INTEGER PRIMARY KEY,
                origin_chat_title TEXT,
                last_downloaded_message_id INTEGER DEFAULT 0,
                total_videos INTEGER DEFAULT 0,
                downloaded_videos INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        log_database_operation(logger, "init_db", table="SyncTasks, DownloadTasks")
        log_operation_success(logger, "init_db")
        
    except sqlite3.Error as e:
        log_operation_error(logger, "init_db", e)
        raise
    finally:
        conn.close()


def get_task(origin_id: int) -> Optional[Dict[str, Any]]:
    """
    Get a sync task by origin chat ID.
    
    Args:
        origin_id: The origin chat ID.
        
    Returns:
        Optional[Dict[str, Any]]: Task data if found, None otherwise.
    """
    log_database_operation(logger, "get_task", origin_chat_id=origin_id)
    
    conn = create_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "SELECT * FROM SyncTasks WHERE origin_chat_id = ?",
            (origin_id,)
        )
        
        row = cursor.fetchone()
        if row:
            task_data = dict(row)
            log_database_operation(logger, "get_task_success", origin_chat_id=origin_id, task_found=True)
            return task_data
        
        log_database_operation(logger, "get_task_not_found", origin_chat_id=origin_id)
        return None
        
    except sqlite3.Error as e:
        log_operation_error(logger, "get_task", e, origin_chat_id=origin_id)
        raise
    finally:
        conn.close()


def create_task(origin_id: int, origin_title: str, dest_id: int) -> None:
    """
    Create a new sync task.
    
    Args:
        origin_id: The origin chat ID.
        origin_title: The origin chat title.
        dest_id: The destination chat ID.
    """
    log_operation_start(logger, "create_task", origin_chat_id=origin_id, origin_title=origin_title, dest_chat_id=dest_id)
    
    conn = create_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO SyncTasks (origin_chat_id, origin_chat_title, destination_chat_id)
            VALUES (?, ?, ?)
        """, (origin_id, origin_title, dest_id))
        
        conn.commit()
        log_database_operation(logger, "create_task_success", origin_chat_id=origin_id, dest_chat_id=dest_id)
        log_operation_success(logger, "create_task", origin_chat_id=origin_id, dest_chat_id=dest_id)
        
    except sqlite3.IntegrityError:
        log_operation_error(logger, "create_task", sqlite3.IntegrityError("Task already exists"), origin_chat_id=origin_id)
        logger.warning(f"⚠️ Task already exists for origin_chat_id={origin_id}")
        raise
    except sqlite3.Error as e:
        log_operation_error(logger, "create_task", e, origin_chat_id=origin_id, dest_chat_id=dest_id)
        raise
    finally:
        conn.close()


def update_strategy(origin_id: int, strategy: str) -> None:
    """
    Update the cloning strategy for a task.
    
    Args:
        origin_id: The origin chat ID.
        strategy: The cloning strategy ('forward' or 'download_upload').
    """
    log_operation_start(logger, "update_strategy", origin_chat_id=origin_id, strategy=strategy)
    
    conn = create_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            UPDATE SyncTasks 
            SET cloning_strategy = ?
            WHERE origin_chat_id = ?
        """, (strategy, origin_id))
        
        if cursor.rowcount == 0:
            log_operation_error(logger, "update_strategy", ValueError("No task found"), origin_chat_id=origin_id)
            logger.warning(f"⚠️ No task found for origin_chat_id={origin_id}")
            return
            
        conn.commit()
        log_database_operation(logger, "update_strategy_success", origin_chat_id=origin_id, strategy=strategy)
        log_operation_success(logger, "update_strategy", origin_chat_id=origin_id, strategy=strategy)
        
    except sqlite3.Error as e:
        log_operation_error(logger, "update_strategy", e, origin_chat_id=origin_id, strategy=strategy)
        raise
    finally:
        conn.close()


def update_progress(origin_id: int, last_message_id: int) -> None:
    """
    Update the last synced message ID for a task.
    
    Args:
        origin_id: The origin chat ID.
        last_message_id: The ID of the last synced message.
    """
    log_database_operation(logger, "update_progress", origin_chat_id=origin_id, last_message_id=last_message_id)
    
    conn = create_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            UPDATE SyncTasks 
            SET last_synced_message_id = ?
            WHERE origin_chat_id = ?
        """, (last_message_id, origin_id))
        
        if cursor.rowcount == 0:
            log_operation_error(logger, "update_progress", ValueError("No task found"), origin_chat_id=origin_id)
            logger.warning(f"⚠️ No task found for origin_chat_id={origin_id}")
            return
            
        conn.commit()
        log_database_operation(logger, "update_progress_success", origin_chat_id=origin_id, last_message_id=last_message_id)
        
    except sqlite3.Error as e:
        log_operation_error(logger, "update_progress", e, origin_chat_id=origin_id, last_message_id=last_message_id)
        raise
    finally:
        conn.close()


def get_download_task(origin_id: int) -> Optional[Dict[str, Any]]:
    """
    Get a download task by origin chat ID.
    
    Args:
        origin_id: The origin chat ID.
        
    Returns:
        Optional[Dict[str, Any]]: Download task data if found, None otherwise.
    """
    log_database_operation(logger, "get_download_task", origin_chat_id=origin_id)
    
    conn = create_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "SELECT * FROM DownloadTasks WHERE origin_chat_id = ?",
            (origin_id,)
        )
        
        row = cursor.fetchone()
        if row:
            task_data = dict(row)
            log_database_operation(logger, "get_download_task_success", origin_chat_id=origin_id, task_found=True)
            return task_data
        
        log_database_operation(logger, "get_download_task_not_found", origin_chat_id=origin_id)
        return None
        
    except sqlite3.Error as e:
        log_operation_error(logger, "get_download_task", e, origin_chat_id=origin_id)
        raise
    finally:
        conn.close()


def create_download_task(origin_id: int, origin_title: str, total_videos: int = 0) -> None:
    """
    Create a new download task.
    
    Args:
        origin_id: The origin chat ID.
        origin_title: The origin chat title.
        total_videos: Total number of videos to download.
    """
    log_operation_start(logger, "create_download_task", origin_chat_id=origin_id, origin_title=origin_title, total_videos=total_videos)
    
    conn = create_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO DownloadTasks (origin_chat_id, origin_chat_title, total_videos)
            VALUES (?, ?, ?)
        """, (origin_id, origin_title, total_videos))
        
        conn.commit()
        log_database_operation(logger, "create_download_task_success", origin_chat_id=origin_id, total_videos=total_videos)
        log_operation_success(logger, "create_download_task", origin_chat_id=origin_id, total_videos=total_videos)
        
    except sqlite3.IntegrityError:
        log_operation_error(logger, "create_download_task", sqlite3.IntegrityError("Task already exists"), origin_chat_id=origin_id)
        logger.warning(f"⚠️ Download task already exists for origin_chat_id={origin_id}")
        raise
    except sqlite3.Error as e:
        log_operation_error(logger, "create_download_task", e, origin_chat_id=origin_id, total_videos=total_videos)
        raise
    finally:
        conn.close()


def update_download_progress(origin_id: int, last_message_id: int, downloaded_count: int) -> None:
    """
    Update the download progress for a task.
    
    Args:
        origin_id: The origin chat ID.
        last_message_id: The ID of the last downloaded message.
        downloaded_count: Number of videos downloaded so far.
    """
    log_database_operation(logger, "update_download_progress", origin_chat_id=origin_id, last_message_id=last_message_id, downloaded_count=downloaded_count)
    
    conn = create_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            UPDATE DownloadTasks 
            SET last_downloaded_message_id = ?, downloaded_videos = ?, updated_at = CURRENT_TIMESTAMP
            WHERE origin_chat_id = ?
        """, (last_message_id, downloaded_count, origin_id))
        
        if cursor.rowcount == 0:
            log_operation_error(logger, "update_download_progress", ValueError("No task found"), origin_chat_id=origin_id)
            logger.warning(f"⚠️ No download task found for origin_chat_id={origin_id}")
            return
            
        conn.commit()
        log_database_operation(logger, "update_download_progress_success", origin_chat_id=origin_id, last_message_id=last_message_id, downloaded_count=downloaded_count)
        
    except sqlite3.Error as e:
        log_operation_error(logger, "update_download_progress", e, origin_chat_id=origin_id, last_message_id=last_message_id, downloaded_count=downloaded_count)
        raise
    finally:
        conn.close()


def delete_download_task(origin_id: int) -> None:
    """
    Delete a download task.
    
    Args:
        origin_id: The origin chat ID.
    """
    log_operation_start(logger, "delete_download_task", origin_chat_id=origin_id)
    
    conn = create_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "DELETE FROM DownloadTasks WHERE origin_chat_id = ?",
            (origin_id,)
        )
        
        if cursor.rowcount == 0:
            log_operation_error(logger, "delete_download_task", ValueError("No task found"), origin_chat_id=origin_id)
            logger.warning(f"⚠️ No download task found for origin_chat_id={origin_id}")
            return
            
        conn.commit()
        log_database_operation(logger, "delete_download_task_success", origin_chat_id=origin_id)
        log_operation_success(logger, "delete_download_task", origin_chat_id=origin_id)
        
    except sqlite3.Error as e:
        log_operation_error(logger, "delete_download_task", e, origin_chat_id=origin_id)
        raise
    finally:
        conn.close() 