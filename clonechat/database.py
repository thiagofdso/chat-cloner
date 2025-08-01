"""
Database layer for Clonechat.
"""
import sqlite3
from typing import Optional, Dict, Any
from pathlib import Path

from .logging_config import (
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
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS PublishTasks (
                source_folder_path TEXT PRIMARY KEY,
                project_name TEXT NOT NULL,
                destination_chat_id INTEGER,
                current_step TEXT,
                status TEXT DEFAULT 'pending',
                -- Flags para cada etapa do pipeline Zimatise (baseado no zimatise_monitor.py)
                is_started BOOLEAN DEFAULT 0,
                is_zipped BOOLEAN DEFAULT 0,
                is_reported BOOLEAN DEFAULT 0,
                is_reencode_auth BOOLEAN DEFAULT 0,
                is_reencoded BOOLEAN DEFAULT 0,
                is_joined BOOLEAN DEFAULT 0,
                is_timestamped BOOLEAN DEFAULT 0,
                is_upload_auth BOOLEAN DEFAULT 0,
                is_published BOOLEAN DEFAULT 0,
                -- Rastreamento de upload
                last_uploaded_file TEXT,
                -- Timestamps
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        log_database_operation(logger, "init_db", table="SyncTasks, DownloadTasks, PublishTasks")
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


def create_publish_task(source_folder: str, project_name: str) -> dict:
    """
    Create a new publish task.
    
    Args:
        source_folder: The absolute path to the source folder.
        project_name: The name of the project (derived from folder name).
        
    Returns:
        dict: The created task data.
        
    Raises:
        sqlite3.IntegrityError: If a task already exists for this source folder.
    """
    log_operation_start(logger, "create_publish_task", source_folder=source_folder, project_name=project_name)
    
    conn = create_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO PublishTasks (source_folder_path, project_name)
            VALUES (?, ?)
        """, (source_folder, project_name))
        
        conn.commit()
        
        # Get the created task data
        cursor.execute("""
            SELECT * FROM PublishTasks WHERE source_folder_path = ?
        """, (source_folder,))
        
        row = cursor.fetchone()
        task_data = dict(row) if row else {}
        
        log_database_operation(logger, "create_publish_task_success", source_folder=source_folder, project_name=project_name)
        log_operation_success(logger, "create_publish_task", source_folder=source_folder, project_name=project_name)
        
        return task_data
        
    except sqlite3.IntegrityError:
        log_operation_error(logger, "create_publish_task", sqlite3.IntegrityError("Task already exists"), source_folder=source_folder)
        logger.warning(f"⚠️ Publish task already exists for source_folder={source_folder}")
        raise
    except sqlite3.Error as e:
        log_operation_error(logger, "create_publish_task", e, source_folder=source_folder, project_name=project_name)
        raise
    finally:
        conn.close()


def get_publish_task(source_folder: str) -> Optional[Dict[str, Any]]:
    """
    Get a publish task by source folder path.
    
    Args:
        source_folder: The absolute path to the source folder.
        
    Returns:
        Optional[Dict[str, Any]]: Publish task data if found, None otherwise.
    """
    log_database_operation(logger, "get_publish_task", source_folder=source_folder)
    
    conn = create_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT * FROM PublishTasks WHERE source_folder_path = ?
        """, (source_folder,))
        
        row = cursor.fetchone()
        if row:
            task_data = dict(row)
            log_database_operation(logger, "get_publish_task_success", source_folder=source_folder, task_found=True)
            return task_data
        
        log_database_operation(logger, "get_publish_task_not_found", source_folder=source_folder)
        return None
        
    except sqlite3.Error as e:
        log_operation_error(logger, "get_publish_task", e, source_folder=source_folder)
        raise
    finally:
        conn.close()


def get_or_create_publish_task(source_folder: str, project_name: str) -> Dict[str, Any]:
    """
    Get an existing publish task or create a new one if it doesn't exist.
    
    Args:
        source_folder: The absolute path to the source folder.
        project_name: The name of the project.
        
    Returns:
        Dict[str, Any]: The existing or newly created task data.
    """
    task = get_publish_task(source_folder)
    if task:
        logger.info(f"Found existing publish task for {source_folder}")
        return task
    
    logger.info(f"No existing task found. Creating a new one for {source_folder}")
    return create_publish_task(source_folder, project_name)


def update_publish_task_step(source_folder: str, step_flag: str, status: bool) -> None:
    """
    Update a specific step flag for a publish task.
    
    Args:
        source_folder: The absolute path to the source folder.
        step_flag: The step flag to update (e.g., 'is_zipped', 'is_reported').
        status: The new status (True/False).
    """
    log_operation_start(logger, "update_publish_task_step", source_folder=source_folder, step_flag=step_flag, status=status)
    
    conn = create_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(f"""
            UPDATE PublishTasks 
            SET {step_flag} = ?, updated_at = CURRENT_TIMESTAMP
            WHERE source_folder_path = ?
        """, (1 if status else 0, source_folder))
        
        if cursor.rowcount == 0:
            log_operation_error(logger, "update_publish_task_step", ValueError("No task found"), source_folder=source_folder)
            logger.warning(f"⚠️ No publish task found for source_folder={source_folder}")
            return
            
        conn.commit()
        log_database_operation(logger, "update_publish_task_step_success", source_folder=source_folder, step_flag=step_flag, status=status)
        log_operation_success(logger, "update_publish_task_step", source_folder=source_folder, step_flag=step_flag, status=status)
        
    except sqlite3.Error as e:
        log_operation_error(logger, "update_publish_task_step", e, source_folder=source_folder, step_flag=step_flag, status=status)
        raise
    finally:
        conn.close()


def update_publish_task_progress(source_folder: str, current_step: str, last_file: Optional[str] = None) -> None:
    """
    Update the current step and optionally the last uploaded file for a publish task.
    
    Args:
        source_folder: The absolute path to the source folder.
        current_step: The name of the current step being executed.
        last_file: The last file that was processed (optional).
    """
    log_operation_start(logger, "update_publish_task_progress", source_folder=source_folder, current_step=current_step, last_file=last_file)
    
    conn = create_connection()
    cursor = conn.cursor()
    
    try:
        if last_file:
            cursor.execute("""
                UPDATE PublishTasks 
                SET current_step = ?, last_uploaded_file = ?, updated_at = CURRENT_TIMESTAMP
                WHERE source_folder_path = ?
            """, (current_step, last_file, source_folder))
        else:
            cursor.execute("""
                UPDATE PublishTasks 
                SET current_step = ?, updated_at = CURRENT_TIMESTAMP
                WHERE source_folder_path = ?
            """, (current_step, source_folder))
        
        if cursor.rowcount == 0:
            log_operation_error(logger, "update_publish_task_progress", ValueError("No task found"), source_folder=source_folder)
            logger.warning(f"⚠️ No publish task found for source_folder={source_folder}")
            return
            
        conn.commit()
        log_database_operation(logger, "update_publish_task_progress_success", source_folder=source_folder, current_step=current_step, last_file=last_file or "")
        log_operation_success(logger, "update_publish_task_progress", source_folder=source_folder, current_step=current_step, last_file=last_file or "")
        
    except sqlite3.Error as e:
        log_operation_error(logger, "update_publish_task_progress", e, source_folder=source_folder, current_step=current_step, last_file=last_file or "")
        raise
    finally:
        conn.close()


def set_publish_destination_chat(source_folder: str, chat_id: int) -> None:
    """
    Set the destination chat ID for a publish task.
    
    Args:
        source_folder: The absolute path to the source folder.
        chat_id: The destination chat ID in Telegram.
    """
    log_operation_start(logger, "set_publish_destination_chat", source_folder=source_folder, chat_id=chat_id)
    
    conn = create_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            UPDATE PublishTasks 
            SET destination_chat_id = ?, updated_at = CURRENT_TIMESTAMP
            WHERE source_folder_path = ?
        """, (chat_id, source_folder))
        
        if cursor.rowcount == 0:
            log_operation_error(logger, "set_publish_destination_chat", ValueError("No task found"), source_folder=source_folder)
            logger.warning(f"⚠️ No publish task found for source_folder={source_folder}")
            return
            
        conn.commit()
        log_database_operation(logger, "set_publish_destination_chat_success", source_folder=source_folder, chat_id=chat_id)
        log_operation_success(logger, "set_publish_destination_chat", source_folder=source_folder, chat_id=chat_id)
        
    except sqlite3.Error as e:
        log_operation_error(logger, "set_publish_destination_chat", e, source_folder=source_folder, chat_id=chat_id)
        raise
    finally:
        conn.close()


def delete_publish_task(source_folder: str) -> None:
    """
    Delete a publish task (for restart functionality).
    
    Args:
        source_folder: The absolute path to the source folder.
    """
    log_operation_start(logger, "delete_publish_task", source_folder=source_folder)
    
    conn = create_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            DELETE FROM PublishTasks WHERE source_folder_path = ?
        """, (source_folder,))
        
        if cursor.rowcount == 0:
            log_operation_error(logger, "delete_publish_task", ValueError("No task found"), source_folder=source_folder)
            logger.warning(f"⚠️ No publish task found for source_folder={source_folder}")
            return
            
        conn.commit()
        log_database_operation(logger, "delete_publish_task_success", source_folder=source_folder)
        log_operation_success(logger, "delete_publish_task", source_folder=source_folder)
        
    except sqlite3.Error as e:
        log_operation_error(logger, "delete_publish_task", e, source_folder=source_folder)
        raise
    finally:
        conn.close() 