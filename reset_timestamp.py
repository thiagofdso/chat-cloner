#!/usr/bin/env python3
"""
Script para resetar apenas o status de timestamp.
Isso força a reexecução da etapa de timestamp com as novas configurações.
"""

import sys
from pathlib import Path

# Adicionar o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent))

from clonechat.database import init_db, update_publish_task_step


def reset_timestamp_status():
    """Reseta apenas o status de timestamp para uma pasta específica."""
    
    # Pasta de teste
    test_folder = r"C:\4_anos_mel"
    
    print(f"🔄 Resetando status de timestamp para: {test_folder}")
    
    # Inicializar banco
    init_db()
    
    # Resetar apenas o status de timestamp
    update_publish_task_step(test_folder, 'is_timestamped', False)
    
    print("✅ Status de timestamp resetado!")
    print("📝 Agora você pode executar o pipeline novamente e a etapa de timestamp será reexecutada")
    print("💡 Execute: poetry run python main.py publish -f \"C:\\4_anos_mel\"")


if __name__ == "__main__":
    reset_timestamp_status() 