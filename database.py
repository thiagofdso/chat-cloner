"""
Database layer for Clonechat.
"""
import sqlite3
import logging
from typing import Optional, Dict, Any
from pathlib import Path


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
        
        conn.commit()
        logging.info("Database initialized successfully")
        
    except sqlite3.Error as e:
        logging.error("Error initializing database: %s", e)
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
    conn = create_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "SELECT * FROM SyncTasks WHERE origin_chat_id = ?",
            (origin_id,)
        )
        
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None
        
    except sqlite3.Error as e:
        logging.error("Error getting task: %s", e)
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
    conn = create_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO SyncTasks (origin_chat_id, origin_chat_title, destination_chat_id)
            VALUES (?, ?, ?)
        """, (origin_id, origin_title, dest_id))
        
        conn.commit()
        logging.info("Task created: origin_id=%d, dest_id=%d", origin_id, dest_id)
        
    except sqlite3.IntegrityError:
        logging.warning("Task already exists for origin_id=%d", origin_id)
        raise
    except sqlite3.Error as e:
        logging.error("Error creating task: %s", e)
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
    conn = create_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            UPDATE SyncTasks 
            SET cloning_strategy = ?
            WHERE origin_chat_id = ?
        """, (strategy, origin_id))
        
        if cursor.rowcount == 0:
            logging.warning("No task found for origin_id=%d", origin_id)
            return
            
        conn.commit()
        logging.info("Strategy updated: origin_id=%d, strategy=%s", origin_id, strategy)
        
    except sqlite3.Error as e:
        logging.error("Error updating strategy: %s", e)
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
    conn = create_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            UPDATE SyncTasks 
            SET last_synced_message_id = ?
            WHERE origin_chat_id = ?
        """, (last_message_id, origin_id))
        
        if cursor.rowcount == 0:
            logging.warning("No task found for origin_id=%d", origin_id)
            return
            
        conn.commit()
        logging.info("Progress updated: origin_id=%d, last_message_id=%d", origin_id, last_message_id)
        
    except sqlite3.Error as e:
        logging.error("Error updating progress: %s", e)
        raise
    finally:
        conn.close() 