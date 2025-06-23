#!/usr/bin/env python3
"""
Test script for the publish upload functionality.
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from clonechat.config import load_config
from clonechat.database import init_db, create_publish_task, get_publish_task
from clonechat.tasks.publish_pipeline import PublishPipeline


async def test_publish_upload():
    """Test the publish upload functionality."""
    print("🧪 Testing publish upload functionality...")
    
    # Load configuration
    config = load_config()
    print(f"✅ Configuration loaded: API ID = {config.telegram_api_id}")
    
    # Initialize database
    init_db()
    print("✅ Database initialized")
    
    # Create a test publish task
    test_folder = Path("test_publish_folder")
    test_folder.mkdir(exist_ok=True)
    
    # Create some test files
    (test_folder / "test_video.mp4").write_text("fake video content")
    (test_folder / "test_document.pdf").write_text("fake document content")
    (test_folder / "summary.txt").write_text("Test summary content for upload")
    
    # Create upload plan
    upload_plan = test_folder / "upload_plan.csv"
    upload_plan.write_text("""file_output,description
test_video.mp4,Test video file
test_document.pdf,Test document file""")
    
    # Create publish task
    task_data = create_publish_task(str(test_folder.absolute()), "Test Project")
    print(f"✅ Created publish task: {task_data}")
    
    # Mark all previous steps as completed
    from clonechat.database import update_publish_task_step
    update_publish_task_step(str(test_folder.absolute()), 'is_zipped', True)
    update_publish_task_step(str(test_folder.absolute()), 'is_reported', True)
    update_publish_task_step(str(test_folder.absolute()), 'is_reencoded', True)
    update_publish_task_step(str(test_folder.absolute()), 'is_joined', True)
    update_publish_task_step(str(test_folder.absolute()), 'is_timestamped', True)
    print("✅ Marked all previous steps as completed")
    
    # Get the updated task
    task = get_publish_task(str(test_folder.absolute()))
    print(f"✅ Retrieved task: {task}")
    
    # Initialize Pyrogram client
    from pyrogram import Client
    
    client = Client(
        "clonechat_test",
        api_id=config.telegram_api_id,
        api_hash=config.telegram_api_hash
    )
    
    try:
        await client.start()
        print("✅ Pyrogram client started")
        
        # Create pipeline instance
        if task is None:
            print("❌ Failed to get task data")
            return
            
        pipeline = PublishPipeline(client, task)
        print("✅ Pipeline instance created")
        
        # Test destination channel creation
        dest_chat_id = await pipeline._ensure_destination_channel()
        print(f"✅ Destination channel created/verified: {dest_chat_id}")
        
        # Test upload plan reading
        files_to_upload = pipeline._read_upload_plan()
        print(f"✅ Upload plan read: {len(files_to_upload)} files")
        
        # Test message type detection
        video_type = pipeline._get_message_type(Path("test.mp4"))
        doc_type = pipeline._get_message_type(Path("test.pdf"))
        print(f"✅ Message type detection: video={video_type}, document={doc_type}")
        
        print("🎉 All upload functionality tests passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        await client.stop()
        print("✅ Pyrogram client stopped")
        
        # Cleanup
        import shutil
        if test_folder.exists():
            shutil.rmtree(test_folder)
            print("✅ Test folder cleaned up")


if __name__ == "__main__":
    asyncio.run(test_publish_upload()) 