"""
CLI interface for Clonechat using Typer.
"""
import asyncio
import typer
from typing import Optional
from pathlib import Path
from pyrogram import Client
import toml
import sqlite3

from config import load_config, Config

from database import init_db, get_task, create_task, update_strategy, update_progress, get_download_task, delete_download_task, create_download_task, update_download_progress
from engine import ClonerEngine
from logging_config import setup_logging, get_logger, log_operation_start, log_operation_success, log_operation_error

# Setup logging
setup_logging(log_level="INFO", enable_console=True, enable_file=True)
logger = get_logger(__name__)

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
    
    logger.info(f"📄 Lidos {len(chat_ids)} IDs do arquivo: {file_path}")
    return chat_ids


async def process_single_chat(engine: ClonerEngine, chat_id: int, restart: bool) -> bool:
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
        log_operation_start(logger, "process_single_chat", chat_id=chat_id, restart=restart)
        await engine.sync_chat(chat_id, restart=restart)
        log_operation_success(logger, "process_single_chat", chat_id=chat_id)
        return True
    except Exception as e:
        log_operation_error(logger, "process_single_chat", e, chat_id=chat_id)
        return False


async def resolve_chat_id(client: Client, chat_identifier: str) -> int:
    """
    Resolve a chat identifier (ID, username, or link) to a numeric ID.
    
    Args:
        client: Pyrogram client instance.
        chat_identifier: Chat ID, username, or link.
        
    Returns:
        Numeric chat ID.
    """
    try:
        # If it's already a numeric ID (including negative), return it
        if chat_identifier.replace('-', '').isdigit():
            return int(chat_identifier)
        
        # Otherwise, resolve it using Pyrogram
        chat = await client.get_chat(chat_identifier)
        return chat.id
    except Exception as e:
        raise ValueError(f"Cannot resolve chat identifier '{chat_identifier}': {e}")


async def run_sync_async(
    origin: Optional[str],
    batch: bool,
    source: Optional[str],
    restart: bool,
    force_download: bool = False,
    leave_origin: bool = False,
    dest: Optional[str] = None
) -> None:
    """
    Async wrapper for the sync operation.
    
    Args:
        origin: Origin chat ID, username or link.
        batch: Whether to process in batch mode.
        source: Source file for batch processing.
        restart: Whether to restart the sync.
        force_download: Whether to force download strategy for extracting audio from videos.
        leave_origin: Whether to leave the origin channel after cloning.
        dest: Destination channel ID, username or link (if None, creates a new channel).
    """
    try:
        log_operation_start(logger, "run_sync_async", origin=origin, batch=batch, restart=restart)
        
        # Carregar configurações
        config = load_config()
        logger.info("⚙️ Configurações carregadas com sucesso")
        
        # Inicializar cliente Pyrogram
        client = Client(
            "clonechat_user",
            api_id=config.telegram_api_id,
            api_hash=config.telegram_api_hash
        )
        
        # Iniciar cliente Pyrogram
        await client.start()
        me = await client.get_me()
        logger.info(f"🤖 Logged in as: {me.first_name} (ID: {me.id})")
        
        # Inicializar banco de dados
        init_db()
        logger.info("💾 Banco de dados inicializado")
        
        # Inicializar motor de clonagem
        # Resolver identificadores de chat se fornecidos
        dest_chat_id = None
        if dest:
            dest_chat_id = await resolve_chat_id(client, dest)
        
        engine = ClonerEngine(config, client, force_download=force_download, leave_origin=leave_origin, dest_chat_id=dest_chat_id)
        logger.info("🚀 Motor de clonagem inicializado")
        
        if batch:
            # Processar múltiplos chats
            logger.info(f"📦 Iniciando processamento em lote do arquivo: {source}")
            chat_ids = read_chat_ids_from_file(source)  # type: ignore
            
            successful = 0
            failed = 0
            
            for chat_id in chat_ids:
                if await process_single_chat(engine, chat_id, restart):
                    successful += 1
                else:
                    failed += 1
            
            logger.info(f"📊 Processamento em lote concluído: {successful} sucessos, {failed} falhas")
            
            if failed > 0:
                raise typer.Exit(1)
        else:
            # Processar chat individual
            if origin:
                origin_chat_id = await resolve_chat_id(client, origin)
                logger.info(f"🎯 Iniciando sincronização do chat {origin} (ID: {origin_chat_id})")
                
                if restart:
                    logger.info("🔄 Modo restart ativado - iniciando nova clonagem")
                else:
                    logger.info("📋 Verificando tarefa existente no banco de dados")
                
                await engine.sync_chat(origin_chat_id, restart=restart)
                logger.info("✅ Sincronização concluída com sucesso!")
        
        log_operation_success(logger, "run_sync_async", origin=origin, batch=batch, restart=restart)
        
    except Exception as e:
        log_operation_error(logger, "run_sync_async", e, origin=origin, batch=batch, restart=restart)
        raise typer.Exit(1)
    finally:
        # Fechar cliente Pyrogram
        if 'client' in locals():
            await client.stop()


@app.command()
def sync(
    origin: Optional[str] = typer.Option(
        None,
        "--origin",
        "-o",
        help="ID, username ou link do chat de origem (não usado com --batch)"
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
    ),
    force_download: bool = typer.Option(
        False,
        "--force-download",
        "-f",
        help="Forçar estratégia download_upload para extrair áudio de vídeos"
    ),
    leave_origin: bool = typer.Option(
        False,
        "--leave-origin",
        "-l",
        help="Sair do canal de origem após a clonagem (por padrão não sai)"
    ),
    dest: Optional[str] = typer.Option(
        None,
        "--dest",
        "-d",
        help="ID, username ou link do canal de destino (se não especificado, cria um novo canal)"
    )
):
    """
    Sincroniza um chat de origem para um canal de destino.
    
    O sistema verifica automaticamente se já existe uma tarefa de clonagem
    para este chat e resume de onde parou. Use --restart para forçar
    uma nova clonagem do zero.
    
    Estratégias de clonagem:
    - Forward: Encaminhamento direto (mais rápido, sem extração de áudio)
    - Download-Upload: Download, processamento e upload (extrai áudio de vídeos)
    
    Use --force-download para sempre usar a estratégia download_upload,
    garantindo que o áudio seja extraído de todos os vídeos.
    
    Use --dest para especificar um canal de destino existente em vez de criar um novo.
    Use --leave-origin para sair do canal de origem após a clonagem.
    
    Modos de uso:
    - Individual: python main.py sync --origin 123456789
    - Com extração de áudio: python main.py sync --origin 123456789 --force-download
    - Para canal existente: python main.py sync --origin 123456789 --dest 987654321
    - Sair do canal origem: python main.py sync --origin 123456789 --leave-origin
    - Batch: python main.py sync --batch --source chats.txt
    """
    try:
        log_operation_start(logger, "sync_command", origin=origin, batch=batch, restart=restart)
        
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
        
        # Executar operação assíncrona
        asyncio.run(run_sync_async(origin, batch, source, restart, force_download, leave_origin, dest))
        
        log_operation_success(logger, "sync_command", origin=origin, batch=batch, restart=restart)
        
    except Exception as e:
        log_operation_error(logger, "sync_command", e, origin=origin, batch=batch, restart=restart)
        raise typer.Exit(1)


@app.command()
def test_resolve(
    chat_id: str = typer.Option(..., "--id", "-i", help="ID, username ou link do chat para testar")
):
    """
    Testa a resolução de um identificador de chat.
    """
    async def test_resolve_chat():
        try:
            # Carregar configurações
            config = load_config()
            logger.info("⚙️ Configurações carregadas com sucesso")
            
            # Inicializar cliente Pyrogram
            client = Client(
                "clonechat_user",
                api_id=config.telegram_api_id,
                api_hash=config.telegram_api_hash
            )
            
            # Iniciar cliente Pyrogram
            await client.start()
            me = await client.get_me()
            logger.info(f"🤖 Logged in as: {me.first_name} (ID: {me.id})")
            
            # Testar resolução
            logger.info(f"🔍 Testando resolução de: {chat_id}")
            resolved_id = await resolve_chat_id(client, chat_id)
            logger.info(f"✅ ID resolvido: {resolved_id}")
            
            # Testar acesso
            chat = await client.get_chat(resolved_id)
            logger.info(f"✅ Acesso confirmado: {chat.title} (ID: {chat.id})")
            
        except Exception as e:
            logger.error(f"❌ Erro: {e}")
            raise typer.Exit(1)
        finally:
            if 'client' in locals():
                await client.stop()
    
    asyncio.run(test_resolve_chat())


@app.command()
def list_chats():
    """
    Lista todos os chats que o usuário tem acesso.
    """
    async def list_user_chats():
        try:
            # Carregar configurações
            config = load_config()
            logger.info("⚙️ Configurações carregadas com sucesso")
            
            # Inicializar cliente Pyrogram
            client = Client(
                "clonechat_user",
                api_id=config.telegram_api_id,
                api_hash=config.telegram_api_hash
            )
            
            # Iniciar cliente Pyrogram
            await client.start()
            me = await client.get_me()
            logger.info(f"🤖 Logged in as: {me.first_name} (ID: {me.id})")
            
            # Listar chats
            logger.info("📋 Listando chats disponíveis:")
            async for dialog in client.get_dialogs():
                chat = dialog.chat
                chat_type = getattr(chat, 'type', 'unknown')
                logger.info(f"  - {chat.title} (ID: {chat.id}, Tipo: {chat_type})")
            
        except Exception as e:
            logger.error(f"❌ Erro ao listar chats: {e}")
            raise typer.Exit(1)
        finally:
            if 'client' in locals():
                await client.stop()
    
    asyncio.run(list_user_chats())


@app.command()
def download(
    origin: str = typer.Option(..., "--origin", "-o", help="ID, username ou link do canal de origem"),
    limit: Optional[int] = typer.Option(None, "--limit", "-l", help="Limite de vídeos para baixar (padrão: todos)"),
    output_dir: Optional[str] = typer.Option(None, "--output", "-d", help="Diretório de saída (padrão: ./downloads/)"),
    restart: bool = typer.Option(False, "--restart", "-r", help="Forçar novo download do zero (apaga dados anteriores)")
):
    """
    Baixa todos os vídeos de um canal e extrai os áudios.
    
    O sistema verifica automaticamente se já existe uma tarefa de download
    para este canal e resume de onde parou. Use --restart para forçar
    um novo download do zero.
    
    Exemplos:
    - python main.py download --origin -1002859374479
    - python main.py download --origin -1002859374479 --limit 10
    - python main.py download --origin -1002859374479 --output ./meus_videos/
    - python main.py download --origin -1002859374479 --restart
    """
    async def download_videos():
        try:
            # Carregar configurações
            config = load_config()
            logger.info("⚙️ Configurações carregadas com sucesso")
            
            # Inicializar cliente Pyrogram
            client = Client(
                "clonechat_user",
                api_id=config.telegram_api_id,
                api_hash=config.telegram_api_hash
            )
            
            # Iniciar cliente Pyrogram
            await client.start()
            me = await client.get_me()
            logger.info(f"🤖 Logged in as: {me.first_name} (ID: {me.id})")
            
            # Inicializar banco de dados
            init_db()
            logger.info("💾 Banco de dados inicializado")
            
            # Resolver ID do canal
            origin_chat_id = await resolve_chat_id(client, origin)
            logger.info(f"🎯 Canal de origem: {origin_chat_id}")
            
            # Obter informações do canal
            chat = await client.get_chat(origin_chat_id)
            logger.info(f"📢 Canal: {chat.title}")
            
            # Verificar tarefa existente
            existing_task = get_download_task(origin_chat_id)
            
            if restart and existing_task:
                logger.info(f"🔄 Modo restart: apagando tarefa existente para origin_chat_id={origin_chat_id}")
                delete_download_task(origin_chat_id)
                existing_task = None
            
            if existing_task:
                logger.info(f"📋 Tarefa de download existente encontrada:")
                logger.info(f"   - Última mensagem processada: {existing_task['last_downloaded_message_id']}")
                logger.info(f"   - Vídeos baixados: {existing_task['downloaded_videos']}")
                logger.info(f"   - Total de vídeos: {existing_task['total_videos']}")
                last_message_id = existing_task['last_downloaded_message_id']
                downloaded_count = existing_task['downloaded_videos']
                logger.info(f"🔄 Resumindo download a partir da mensagem {last_message_id}")
            else:
                logger.info("🆕 Iniciando nova tarefa de download")
                last_message_id = 0
                downloaded_count = 0
            
            # Configurar diretório de saída
            if output_dir:
                download_path = Path(output_dir).resolve()
            else:
                download_path = Path("./downloads/").resolve() / f"{chat.title}"
            
            download_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"📁 Diretório de saída: {download_path}")
            logger.info(f"📁 Caminho absoluto: {download_path.absolute()}")
            
            # Contar vídeos (apenas se não for restart e não há tarefa existente)
            if not existing_task or restart:
                video_count = 0
                async for message in client.get_chat_history(origin_chat_id):
                    if message.video:
                        video_count += 1
                        if limit and video_count >= limit:
                            break
                
                logger.info(f"📊 Total de vídeos encontrados: {video_count}")
                
                # Criar nova tarefa
                try:
                    create_download_task(origin_chat_id, chat.title, video_count)
                except sqlite3.IntegrityError:
                    # Se já existe, atualizar
                    pass
            else:
                video_count = existing_task['total_videos']
                logger.info(f"📊 Total de vídeos (da tarefa existente): {video_count}")
            
            # Baixar vídeos
            failed_count = 0
            processed_messages = set()
            
            async for message in client.get_chat_history(origin_chat_id):
                if message.video:
                    # Pular mensagens já processadas
                    if message.id <= last_message_id:
                        continue
                    
                    # Verificar limite
                    if limit and downloaded_count >= limit:
                        logger.info(f"✅ Limite atingido: {limit} vídeos baixados")
                        break
                    
                    try:
                        # Nome do arquivo baseado na data e ID da mensagem
                        date_str = message.date.strftime("%Y%m%d_%H%M%S")
                        video_filename = f"{date_str}_{message.id}_video.mp4"
                        audio_filename = f"{date_str}_{message.id}_audio.mp3"
                        
                        video_path = download_path / video_filename
                        audio_path = download_path / audio_filename
                        
                        logger.info(f"📥 Baixando vídeo {downloaded_count + 1}/{video_count}: {video_filename}")
                        
                        # Baixar vídeo
                        await client.download_media(
                            message.video,
                            file_name=str(video_path)
                        )
                        
                        # Extrair áudio
                        logger.info(f"🎵 Extraindo áudio: {audio_filename}")
                        try:
                            import subprocess
                            result = subprocess.run([
                                "ffmpeg", "-i", str(video_path), 
                                "-vn", "-acodec", "mp3", 
                                "-ab", "192k", str(audio_path),
                                "-y"  # Sobrescrever se existir
                            ], capture_output=True, text=True, check=True)
                            
                            logger.info(f"✅ Áudio extraído: {audio_filename}")
                            
                            # Verificar se os arquivos existem
                            if video_path.exists():
                                logger.info(f"✅ Vídeo salvo: {video_path} ({video_path.stat().st_size} bytes)")
                            else:
                                logger.warning(f"⚠️ Vídeo não encontrado: {video_path}")
                            
                            if audio_path.exists():
                                logger.info(f"✅ Áudio salvo: {audio_path} ({audio_path.stat().st_size} bytes)")
                            else:
                                logger.warning(f"⚠️ Áudio não encontrado: {audio_path}")
                            
                            # NÃO remover vídeo original - manter ambos
                            # video_path.unlink()
                            # logger.info(f"🗑️ Vídeo original removido: {video_filename}")
                            
                        except subprocess.CalledProcessError as e:
                            logger.error(f"❌ Erro ao extrair áudio: {e}")
                            logger.error(f"FFmpeg stderr: {e.stderr}")
                        except FileNotFoundError:
                            logger.error("❌ FFmpeg não encontrado. Instale o FFmpeg e adicione ao PATH.")
                        
                        downloaded_count += 1
                        processed_messages.add(message.id)
                        
                        # Atualizar progresso no banco
                        update_download_progress(origin_chat_id, message.id, downloaded_count)
                        
                        # Delay para evitar flood
                        await asyncio.sleep(1)
                        
                    except Exception as e:
                        logger.error(f"❌ Erro ao baixar vídeo {message.id}: {e}")
                        failed_count += 1
                        continue
            
            logger.info(f"🎉 Download concluído!")
            logger.info(f"✅ Vídeos baixados: {downloaded_count}")
            logger.info(f"❌ Falhas: {failed_count}")
            logger.info(f"📁 Arquivos salvos em: {download_path}")
            
            # Listar arquivos baixados
            if download_path.exists():
                files = list(download_path.glob("*"))
                if files:
                    logger.info(f"📋 Arquivos no diretório ({len(files)}):")
                    for file in files:
                        size = file.stat().st_size
                        logger.info(f"  - {file.name} ({size} bytes)")
                else:
                    logger.warning("⚠️ Nenhum arquivo encontrado no diretório")
            else:
                logger.error("❌ Diretório de saída não existe")
            
        except Exception as e:
            logger.error(f"❌ Erro no download: {e}")
            raise typer.Exit(1)
        finally:
            if 'client' in locals():
                await client.stop()
    
    asyncio.run(download_videos())


@app.command()
def init_database():
    """
    Inicializa ou atualiza o banco de dados.
    """
    try:
        logger.info("🚀 Inicializando banco de dados...")
        init_db()
        logger.info("✅ Banco de dados inicializado com sucesso!")
        logger.info("📋 Tabelas criadas:")
        logger.info("   - SyncTasks (tarefas de clonagem)")
        logger.info("   - DownloadTasks (tarefas de download)")
    except Exception as e:
        logger.error(f"❌ Erro ao inicializar banco de dados: {e}")
        raise typer.Exit(1)


@app.command()
def version():
    """Exibe a versão do Clonechat."""
    try:
        pyproject = toml.load("pyproject.toml")
        version = pyproject.get("project", {}).get("version", "desconhecida")
        typer.echo(f"Clonechat v{version}")
    except Exception:
        typer.echo("Clonechat (versão desconhecida)")


if __name__ == "__main__":
    app() 