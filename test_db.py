#!/usr/bin/env python3
"""
Simple test script for database operations.
"""
import logging
from database import init_db, create_task, get_task, update_strategy, update_progress

# Setup logging
logging.basicConfig(level=logging.INFO)

def test_database():
    """Test database operations."""
    print("Testing database operations...")
    
    # Initialize database
    init_db()
    print("✓ Database initialized")
    
    # Test creating a task
    try:
        create_task(99999, "Test Channel", 88888)
        print("✓ Task created")
    except Exception as e:
        print(f"⚠ Task creation: {e}")
    
    # Test getting a task
    try:
        task = get_task(99999)
        if task:
            print(f"✓ Task found: {task['origin_chat_title']}")
        else:
            print("✗ Task not found")
    except Exception as e:
        print(f"⚠ Task retrieval: {e}")
    
    # Test updating strategy
    try:
        update_strategy(99999, "forward")
        print("✓ Strategy updated")
    except Exception as e:
        print(f"⚠ Strategy update: {e}")
    
    # Test updating progress
    try:
        update_progress(99999, 100)
        print("✓ Progress updated")
    except Exception as e:
        print(f"⚠ Progress update: {e}")
    
    print("Database test completed!")

if __name__ == "__main__":
    test_database() 