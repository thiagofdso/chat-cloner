#!/usr/bin/env python3
"""
Script de teste para as funções de banco de dados de PublishTasks.
"""
import os
import sys
from pathlib import Path

# Adicionar o diretório atual ao path para importar os módulos
sys.path.insert(0, str(Path(__file__).parent))

from database import (
    init_db, 
    create_publish_task, 
    get_publish_task, 
    update_publish_task_step,
    update_publish_task_progress,
    set_publish_destination_chat,
    delete_publish_task
)
from logging_config import setup_logging, get_logger

def test_publish_database():
    """Testa as funções de banco de dados para PublishTasks."""
    
    # Configurar logging
    setup_logging(log_level="INFO", enable_console=True, enable_file=False)
    logger = get_logger(__name__)
    
    logger.info("🧪 Iniciando testes do banco de dados PublishTasks...")
    
    try:
        # 1. Testar inicialização do banco
        logger.info("📋 1. Testando inicialização do banco de dados...")
        init_db()
        logger.info("✅ Banco de dados inicializado com sucesso")
        
        # 2. Testar criação de tarefa
        logger.info("📋 2. Testando criação de tarefa de publicação...")
        test_folder = r"C:\test\projeto_exemplo"
        test_project = "projeto_exemplo"
        
        task_data = create_publish_task(test_folder, test_project)
        logger.info(f"✅ Tarefa criada: {task_data}")
        
        # 3. Testar busca de tarefa
        logger.info("📋 3. Testando busca de tarefa...")
        found_task = get_publish_task(test_folder)
        if found_task:
            logger.info(f"✅ Tarefa encontrada: {found_task}")
        else:
            logger.error("❌ Tarefa não encontrada!")
            return False
        
        # 4. Testar atualização de etapa
        logger.info("📋 4. Testando atualização de etapa...")
        update_publish_task_step(test_folder, "is_zipped", True)
        update_publish_task_step(test_folder, "is_reported", True)
        
        # Verificar se as atualizações foram aplicadas
        updated_task = get_publish_task(test_folder)
        if updated_task:
            logger.info(f"✅ Tarefa após atualizações: is_zipped={updated_task['is_zipped']}, is_reported={updated_task['is_reported']}")
        else:
            logger.error("❌ Não foi possível recuperar a tarefa atualizada!")
            return False
        
        # 5. Testar atualização de progresso
        logger.info("📋 5. Testando atualização de progresso...")
        update_publish_task_progress(test_folder, "zipping", "arquivo1.zip")
        
        # Verificar progresso
        progress_task = get_publish_task(test_folder)
        if progress_task:
            logger.info(f"✅ Progresso atualizado: current_step={progress_task['current_step']}, last_uploaded_file={progress_task['last_uploaded_file']}")
        else:
            logger.error("❌ Não foi possível recuperar a tarefa de progresso!")
            return False
        
        # 6. Testar definição de chat de destino
        logger.info("📋 6. Testando definição de chat de destino...")
        test_chat_id = -1001234567890
        set_publish_destination_chat(test_folder, test_chat_id)
        
        # Verificar chat de destino
        dest_task = get_publish_task(test_folder)
        if dest_task:
            logger.info(f"✅ Chat de destino definido: destination_chat_id={dest_task['destination_chat_id']}")
        else:
            logger.error("❌ Não foi possível recuperar a tarefa de destino!")
            return False
        
        # 7. Testar remoção de tarefa
        logger.info("📋 7. Testando remoção de tarefa...")
        delete_publish_task(test_folder)
        
        # Verificar se foi removida
        deleted_task = get_publish_task(test_folder)
        if deleted_task is None:
            logger.info("✅ Tarefa removida com sucesso")
        else:
            logger.error("❌ Tarefa não foi removida!")
            return False
        
        logger.info("🎉 Todos os testes passaram com sucesso!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro durante os testes: {e}")
        return False

if __name__ == "__main__":
    success = test_publish_database()
    if success:
        print("\n🎉 Testes concluídos com sucesso!")
        sys.exit(0)
    else:
        print("\n❌ Alguns testes falharam!")
        sys.exit(1) 