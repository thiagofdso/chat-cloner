"""
CLI interface for Clonechat using Typer.
"""
import typer
from typing import Optional
import logging
from pathlib import Path
from pyrogram import Client

from config import load_config, Config
from database import init_db, get_task, create_task, update_strategy, update_progress
from engine import ClonerEngine

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = typer.Typer(
    name="clonechat",
    help="Clonechat - Ferramenta para clonar chats do Telegram",
    add_completion=False
)


def read_chat_ids_from_file(file_path: str) -> list[int]:
    """
    Read chat IDs from a text file.
    
    Args:
        file_path: Path to the text file containing chat IDs.
        
    Returns:
        List of chat IDs as integers.
        
    Raises:
        FileNotFoundError: If the file doesn't exist.
        ValueError: If the file contains invalid chat IDs.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")
    
    chat_ids = []
    with open(path, 'r', encoding='utf-8') as file:
        for line_num, line in enumerate(file, 1):
            line = line.strip()
            if not line or line.startswith('#'):  # Skip empty lines and comments
                continue
            
            try:
                chat_id = int(line)
                chat_ids.append(chat_id)
            except ValueError:
                raise ValueError(f"ID inválido na linha {line_num}: '{line}'")
    
    if not chat_ids:
        raise ValueError(f"Nenhum ID válido encontrado no arquivo: {file_path}")
    
    logger.info(f"Lidos {len(chat_ids)} IDs do arquivo: {file_path}")
    return chat_ids


def process_single_chat(engine: ClonerEngine, chat_id: int, restart: bool) -> bool:
    """
    Process a single chat synchronization.
    
    Args:
        engine: ClonerEngine instance.
        chat_id: Chat ID to process.
        restart: Whether to restart the sync.
        
    Returns:
        True if successful, False otherwise.
    """
    try:
        logger.info(f"Processando chat {chat_id}")
        engine.sync_chat(chat_id, restart=restart)
        logger.info(f"Chat {chat_id} processado com sucesso")
        return True
    except Exception as e:
        logger.error(f"Erro ao processar chat {chat_id}: {e}")
        return False


@app.command()
def sync(
    origin: Optional[int] = typer.Argument(
        None,
        help="ID do chat de origem (não usado com --batch)"
    ),
    batch: bool = typer.Option(
        False,
        "--batch",
        "-b",
        help="Processar múltiplos chats a partir de um arquivo"
    ),
    source: Optional[str] = typer.Option(
        None,
        "--source",
        "-s",
        help="Caminho para o arquivo com lista de IDs (obrigatório com --batch)"
    ),
    restart: bool = typer.Option(
        False,
        "--restart",
        "-r",
        help="Forçar nova clonagem do zero (apaga dados anteriores)"
    )
):
    """
    Sincroniza um chat de origem para um canal de destino.
    
    O sistema verifica automaticamente se já existe uma tarefa de clonagem
    para este chat e resume de onde parou. Use --restart para forçar
    uma nova clonagem do zero.
    
    Modos de uso:
    - Individual: python main.py sync 123456789
    - Batch: python main.py sync --batch --source chats.txt
    """
    try:
        # Validar argumentos
        if batch:
            if not source:
                raise typer.BadParameter("--source é obrigatório quando --batch é usado")
            if origin is not None:
                raise typer.BadParameter("--origin não deve ser usado com --batch")
        else:
            if origin is None:
                raise typer.BadParameter("--origin é obrigatório quando --batch não é usado")
            if source:
                raise typer.BadParameter("--source só deve ser usado com --batch")
        
        # Carregar configurações
        config = load_config()
        logger.info("Configurações carregadas com sucesso")
        
        # Inicializar cliente Pyrogram
        client = Client(
            "clonechat_user",
            api_id=config.telegram_api_id,
            api_hash=config.telegram_api_hash
        )
        
        # Inicializar banco de dados
        init_db()
        logger.info("Banco de dados inicializado")
        
        # Inicializar motor de clonagem
        engine = ClonerEngine(config, client)
        logger.info("Motor de clonagem inicializado")
        
        if batch:
            # Processar múltiplos chats
            logger.info(f"Iniciando processamento em lote do arquivo: {source}")
            chat_ids = read_chat_ids_from_file(source)  # type: ignore
            
            successful = 0
            failed = 0
            
            for chat_id in chat_ids:
                if process_single_chat(engine, chat_id, restart):
                    successful += 1
                else:
                    failed += 1
            
            logger.info(f"Processamento em lote concluído: {successful} sucessos, {failed} falhas")
            
            if failed > 0:
                raise typer.Exit(1)
        else:
            # Processar chat individual
            logger.info(f"Iniciando sincronização do chat {origin}")
            
            if restart:
                logger.info("Modo restart ativado - iniciando nova clonagem")
            else:
                logger.info("Verificando tarefa existente no banco de dados")
            
            engine.sync_chat(origin, restart=restart)  # type: ignore
            logger.info("Sincronização concluída com sucesso!")
        
    except Exception as e:
        logger.error(f"Erro durante a sincronização: {e}")
        raise typer.Exit(1)


@app.command()
def version():
    """Exibe a versão do Clonechat."""
    typer.echo("Clonechat v2.0.0")


if __name__ == "__main__":
    app() 