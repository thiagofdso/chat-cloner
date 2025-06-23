"""
Clonechat - Ferramenta para clonar chats do Telegram e publicar pastas locais.

Este pacote contém toda a lógica principal do Clonechat, incluindo:
- Interface de linha de comando (CLI)
- Camada de acesso a dados (DAL)
- Motores de processamento (clone e publish)
- Utilitários e configurações
"""

__version__ = "2.0.0"
__author__ = "Thiago Oliveira & AI Copilot"

# Imports principais para facilitar o uso
from .cli import app
from .config import load_config, Config
from .database import init_db
from .engine import ClonerEngine
from .tasks import PublishPipeline

__all__ = [
    'app',
    'load_config', 
    'Config',
    'init_db',
    'ClonerEngine',
    'PublishPipeline'
] 