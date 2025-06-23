"""
Test script for PublishPipeline implementation.
"""
import asyncio
import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

from clonechat.config import load_config
from clonechat.database import init_db, create_publish_task, get_publish_task
from clonechat.tasks import PublishPipeline
from clonechat.logging_config import setup_logging, get_logger

logger = get_logger(__name__)


async def test_publish_pipeline():
    """Test the PublishPipeline implementation."""
    try:
        logger.info("🧪 Iniciando teste do PublishPipeline")
        
        # Setup logging
        setup_logging(log_level="INFO", enable_console=True, enable_file=True)
        
        # Load config
        config = load_config()
        logger.info("⚙️ Configuração carregada")
        
        # Initialize database
        init_db()
        logger.info("💾 Banco de dados inicializado")
        
        # Create a test task
        test_folder = Path("test_folder")
        test_folder.mkdir(exist_ok=True)
        
        # Create some test files
        (test_folder / "test.txt").write_text("Test file content")
        (test_folder / "test2.txt").write_text("Another test file")
        
        logger.info(f"📁 Pasta de teste criada: {test_folder}")
        
        # Create publish task
        task_data = create_publish_task(str(test_folder.resolve()), "test_project")
        logger.info(f"📋 Tarefa criada: {task_data}")
        
        # Create a mock client (we won't actually use it for this test)
        class MockClient:
            pass
        
        mock_client = MockClient()
        
        # Create and run pipeline
        pipeline = PublishPipeline(mock_client, task_data)
        logger.info("🚀 Pipeline criado")
        
        # Run the pipeline
        success = await pipeline.run()
        
        if success:
            logger.info("✅ Pipeline executado com sucesso!")
        else:
            logger.error("❌ Pipeline falhou")
            return False
        
        # Check task status
        updated_task = get_publish_task(str(test_folder.resolve()))
        if updated_task:
            logger.info(f"📊 Status da tarefa após execução:")
            logger.info(f"   - is_zipped: {updated_task.get('is_zipped', False)}")
            logger.info(f"   - is_reported: {updated_task.get('is_reported', False)}")
            logger.info(f"   - current_step: {updated_task.get('current_step', 'N/A')}")
        else:
            logger.warning("⚠️ Tarefa não encontrada após execução")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro durante teste: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_publish_pipeline())
    if success:
        print("✅ Teste concluído com sucesso!")
    else:
        print("❌ Teste falhou!")
        sys.exit(1) 