"""
CLI interface for Clonechat using Typer.
"""
import asyncio
import typer
from typing import Optional
from pathlib import Path
from pyrogram import Client, raw
from pyrogram.errors import FileReferenceExpired
import toml
import sqlite3
import re
from pyrogram.raw.functions.channels import GetFullChannel, GetForumTopics

from .config import load_config, Config

from .database import init_db, get_task, create_task, update_strategy, update_progress, get_download_task, delete_download_task, create_download_task, update_download_progress, get_publish_task, get_or_create_publish_task, delete_publish_task
from .engine import ClonerEngine
from .logging_config import setup_logging, get_logger, log_operation_start, log_operation_success, log_operation_error
from .tasks import PublishPipeline

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
    if not chat_identifier:
        raise ValueError("Chat identifier cannot be empty or None")

    try:
        # If it's already a numeric ID (including negative), return it
        if str(chat_identifier).replace('-', '').isdigit():
            return int(chat_identifier)

        # Otherwise, resolve it using Pyrogram
        chat = await client.get_chat(chat_identifier)
        return chat.id
    except Exception as e:
        raise ValueError(f"Cannot resolve chat identifier '{chat_identifier}': {e}")


async def validate_batch_chats(client: Client, chat_ids: list[int]) -> tuple[list[int], list[int]]:
    """
    Validate batch chat IDs before processing.

    Args:
        client: Pyrogram client instance.
        chat_ids: List of chat IDs to validate.

    Returns:
        Tuple of (valid_chat_ids, invalid_chat_ids).
    """
    valid_chats = []
    invalid_chats = []

    logger.info(f"🔍 Validando {len(chat_ids)} chats antes do processamento...")

    for i, chat_id in enumerate(chat_ids, 1):
        try:
            logger.info(f"🔍 Validando chat {i}/{len(chat_ids)}: {chat_id}")

            # Resolver ID do chat
            resolved_id = await resolve_chat_id(client, str(chat_id))

            # Testar acesso ao chat
            chat = await client.get_chat(resolved_id)

            logger.info(f"✅ Chat válido: {chat.title} (ID: {chat.id}, Tipo: {getattr(chat, 'type', 'unknown')})")
            valid_chats.append(chat_id)

        except Exception as e:
            logger.error(f"❌ Chat inválido {chat_id}: {e}")
            invalid_chats.append(chat_id)

    logger.info(f"📊 Validação concluída: {len(valid_chats)} válidos, {len(invalid_chats)} inválidos")

    if invalid_chats:
        logger.warning(f"⚠️ Chats inválidos que serão ignorados: {invalid_chats}")

    return valid_chats, invalid_chats


async def run_sync_async(
    origin: Optional[str],
    batch: bool,
    source: Optional[str],
    restart: bool,
    force_download: bool = False,
    leave_origin: bool = False,
    dest: Optional[str] = None,
    publish_to: Optional[str] = None,
    topic_id: Optional[int] = None,
    extract_audio: bool = False
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
        publish_to: ID, username or link of the group/channel to publish the links of cloned channels.
        topic_id: ID of the topic (for groups with topic enabled).
        extract_audio: Whether to extract audio from videos when using download-upload strategy.
    """
    try:
        log_operation_start(logger, "run_sync_async", origin=origin, batch=batch, restart=restart)

        # Carregar configurações
        config = load_config()
        logger.info("⚙️ Configurações carregadas com sucesso")

        # Inicializar cliente Pyrogram
        client = Client(
            config.cloner_session_name,
            api_id=config.telegram_api_id,
            api_hash=config.telegram_api_hash
        )

        # Iniciar cliente Pyrogram
        await client.start()
        me = await client.get_me()
        logger.info(f"🤖 Logged in as: {me.first_name} (ID: {me.id})")

        # Atualizar cache de chats (semelhante a list-chats)
        logger.info("🔄 Atualizando cache de chats...")
        async for _ in client.get_dialogs():
            pass
        logger.info("✅ Cache de chats atualizado.")

        # Inicializar banco de dados
        init_db()
        logger.info("💾 Banco de dados inicializado")

        # Inicializar motor de clonagem
        # Resolver identificadores de chat se fornecidos
        dest_chat_id = None
        if dest:
            dest_chat_id = await resolve_chat_id(client, dest)

        publish_chat_id = None
        if publish_to:
            publish_chat_id = await resolve_chat_id(client, publish_to)

        engine = ClonerEngine(config, client, force_download=force_download, leave_origin=leave_origin, dest_chat_id=dest_chat_id, publish_chat_id=publish_chat_id, topic_id=topic_id, extract_audio=extract_audio)
        logger.info("🚀 Motor de clonagem inicializado")

        if batch:
            # Processar múltiplos chats
            logger.info(f"📦 Iniciando processamento em lote do arquivo: {source}")
            chat_ids = read_chat_ids_from_file(source)  # type: ignore

            # Validar chats antes do processamento
            valid_chat_ids, invalid_chat_ids = await validate_batch_chats(client, chat_ids)

            if not valid_chat_ids:
                logger.error("❌ Nenhum chat válido encontrado no arquivo batch")
                raise typer.Exit(1)

            if invalid_chat_ids:
                logger.warning(f"⚠️ {len(invalid_chat_ids)} chats inválidos serão ignorados")

            logger.info(f"🚀 Iniciando processamento de {len(valid_chat_ids)} chats válidos")

            successful = 0
            failed = 0

            for chat_id in valid_chat_ids:
                if await process_single_chat(engine, chat_id, restart):
                    successful += 1
                else:
                    failed += 1

            logger.info(f"📊 Processamento em lote concluído: {successful} sucessos, {failed} falhas")

            if invalid_chat_ids:
                logger.info(f"📋 Resumo final:")
                logger.info(f"   ✅ Chats processados: {len(valid_chat_ids)}")
                logger.info(f"   ❌ Chats ignorados (inválidos): {len(invalid_chat_ids)}")
                logger.info(f"   🎯 Taxa de sucesso: {successful}/{len(valid_chat_ids)}")

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
    extract_audio: bool = typer.Option(
        False,
        "--extract-audio",
        help="Extrair áudio de vídeos na estratégia download-upload (default: False)"
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
    ),
    publish_to: Optional[str] = typer.Option(
        None,
        "--publish-to",
        "-p",
        help="ID, username ou link do grupo/canal onde publicar os links dos canais clonados"
    ),
    topic_id: Optional[int] = typer.Option(
        None,
        "--topic",
        "-t",
        help="ID do tópico (para grupos com tópicos habilitados)"
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

    Use --force-download para sempre usar a estratégia download_upload.
    Use --extract-audio para extrair o áudio dos vídeos ao usar a estratégia de download-upload.

    Use --dest para especificar um canal de destino existente em vez de criar um novo.
    Use --leave-origin para sair do canal de origem após a clonagem.
    Use --publish-to para publicar os links dos canais clonados em um grupo/canal.
    Use --topic para especificar um tópico específico (para grupos com tópicos).

    Modos de uso:
    - Individual: python main.py sync --origin 123456789
    - Com extração de áudio: python main.py sync --origin 123456789 --force-download --extract-audio
    - Para canal existente: python main.py sync --origin 123456789 --dest 987654321
    - Sair do canal origem: python main.py sync --origin 123456789 --leave-origin
    - Publicar links: python main.py sync --origin 123456789 --publish-to -1001234567890
    - Publicar em tópico: python main.py sync --origin 123456789 --publish-to -1001234567890 --topic 123
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
        asyncio.run(run_sync_async(origin, batch, source, restart, force_download, leave_origin, dest, publish_to, topic_id, extract_audio))

        log_operation_success(logger, "sync_command", origin=origin, batch=batch, restart=restart)

    except Exception as e:
        log_operation_error(logger, "sync_command", e, origin=origin, batch=batch, restart=restart)
        raise typer.Exit(1)


@app.command()
def test_resolve(
    chat_id: str = typer.Option(
        None,
        "--id",
        "-i",
        help="ID, username ou link do chat para testar"
    )
):
    """
    Testa a resolução de um identificador de chat.
    """
    if not chat_id:
        logger.error("❌ O parâmetro --id é obrigatório.")
        raise typer.Exit(1)

    async def test_resolve_chat():
        try:
            # Carregar configurações
            config = load_config()
            logger.info("⚙️ Configurações carregadas com sucesso")

            # Inicializar cliente Pyrogram
            client = Client(
                config.cloner_session_name,
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
                config.cloner_session_name,
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


@app.command(name="join-channel")
def join_channel(
    invite_url: Optional[str] = typer.Option(
        None,
        "--invite-url",
        "-i",
        help="Link de convite do canal (para canais privados)"
    ),
    public: bool = typer.Option(
        False,
        "--public",
        help="Indica se o canal é público"
    ),
    name: Optional[str] = typer.Option(
        None,
        "--name",
        "-n",
        help="Username do canal (para canais públicos, ex: @nome_do_canal)"
    )
):
    """
    Entra em um canal público ou privado.

    Por padrão, considera que o canal é privado e requer --invite-url.
    Se o canal for público, use --public e forneça o --name.

    Exemplos:
    - Privado: python main.py join-channel --invite-url https://t.me/+ABC123xyz789
    - Público: python main.py join-channel --public --name @nome_do_canal
    """
    async def run_join():
        try:
            # Validar argumentos
            if public:
                if not name:
                    logger.error("❌ O parâmetro --name é obrigatório para canais públicos.")
                    raise typer.Exit(1)
                target = name
            else:
                if not invite_url:
                    logger.error("❌ O parâmetro --invite-url é obrigatório para canais privados.")
                    logger.info("💡 Para canais públicos, use --public --name @canal")
                    raise typer.Exit(1)

                # Extrair hash do link de convite
                if "+" in invite_url:
                    target = invite_url.split("+")[-1].split("?")[0].split("/")[0]
                elif "joinchat/" in invite_url:
                    target = invite_url.split("joinchat/")[-1].split("?")[0].split("/")[0]
                else:
                    target = invite_url # Assume que já é o hash

            # Carregar configurações
            config = load_config()

            # Inicializar cliente Pyrogram
            client = Client(
                config.cloner_session_name,
                api_id=config.telegram_api_id,
                api_hash=config.telegram_api_hash
            )

            # Iniciar cliente Pyrogram
            await client.start()

            if public:
                logger.info(f"🚀 Tentando entrar no canal público: {target}")
                chat = await client.join_chat(target)
                logger.info(f"✅ Entrou com sucesso no canal: {chat.title} (ID: {chat.id})")
            else:
                logger.info(f"🚀 Tentando entrar no canal privado com hash: {target}")
                chat = await client.join_chat_invite(target)
                logger.info(f"✅ Entrou com sucesso no canal privado: {chat.title} (ID: {chat.id})")

        except Exception as e:
            logger.error(f"❌ Erro ao entrar no canal: {e}")
            raise typer.Exit(1)
        finally:
            if 'client' in locals():
                await client.stop()

    asyncio.run(run_join())


@app.command(name="leave-channel")
def leave_channel(
    chat_id: str = typer.Option(
        None,
        "--id",
        "-i",
        help="ID, username ou link do canal que deseja sair"
    )
):
    """
    Sai de um canal ou grupo.

    Exemplos:
    - Por ID: python main.py leave-channel --id -1001234567890
    - Por Username: python main.py leave-channel --id @nome_do_canal
    """
    if not chat_id:
        logger.error("❌ O parâmetro --id é obrigatório.")
        raise typer.Exit(1)

    async def run_leave():
        try:
            # Carregar configurações
            config = load_config()

            # Inicializar cliente Pyrogram
            client = Client(
                config.cloner_session_name,
                api_id=config.telegram_api_id,
                api_hash=config.telegram_api_hash
            )

            # Iniciar cliente Pyrogram
            await client.start()

            # Resolver ID do chat
            resolved_id = await resolve_chat_id(client, chat_id)

            # Obter título para o log antes de sair (se possível)
            try:
                chat = await client.get_chat(resolved_id)
                title = chat.title
            except Exception:
                title = chat_id

            logger.info(f"🚀 Saindo do canal/grupo: {title} (ID: {resolved_id})")
            await client.leave_chat(resolved_id)
            logger.info(f"✅ Saiu com sucesso do canal: {title}")

        except Exception as e:
            logger.error(f"❌ Erro ao sair do canal: {e}")
            raise typer.Exit(1)
        finally:
            if 'client' in locals():
                await client.stop()

    asyncio.run(run_leave())


@app.command(name="extract-messages")
def extract_messages(
    chat_id: str = typer.Option(
        None,
        "--id",
        "-i",
        help="ID, username ou link do canal que deseja extrair as mensagens"
    ),
    output_file: str = typer.Option(
        "mensagens.txt",
        "--output",
        "-o",
        help="Caminho do arquivo .txt onde as mensagens serão salvas"
    ),
    topic_id: Optional[int] = typer.Option(
        None,
        "--topic",
        "-t",
        help="ID do tópico (para grupos com tópicos habilitados)"
    )
):
    """
    Extrai todos os captions e mensagens de texto de um canal ou tópico.

    O resultado é salvo em um arquivo de texto.

    Exemplo:
    - Canal: python main.py extract-messages --id -1001234567890 -o extraido.txt
    - Tópico: python main.py extract-messages --id -1001234567890 --topic 42 -o topico.txt
    """
    if not chat_id:
        logger.error("❌ O parâmetro --id é obrigatório.")
        raise typer.Exit(1)

    async def run_extract():
        try:
            # Carregar configurações
            config = load_config()

            # Inicializar cliente Pyrogram
            client = Client(
                config.cloner_session_name,
                api_id=config.telegram_api_id,
                api_hash=config.telegram_api_hash
            )

            # Iniciar cliente Pyrogram
            await client.start()

            # Resolver ID do chat
            resolved_id = await resolve_chat_id(client, chat_id)

            # Obter informações do chat
            chat = await client.get_chat(resolved_id)
            topic_log = f" no tópico {topic_id}" if topic_id else ""
            logger.info(f"🚀 Iniciando extração do canal: {chat.title} (ID: {resolved_id}){topic_log}")

            messages_extracted = 0

            with open(output_file, "w", encoding="utf-8") as f:
                header = f"Extração do canal: {chat.title} (ID: {resolved_id})"
                if topic_id:
                    header += f" | Tópico: {topic_id}"
                f.write(f"{header}\n")
                f.write("-" * 50 + "\n\n")

                # Coletar histórico
                history_args = {"chat_id": resolved_id}
                if topic_id:
                    history_args["reply_to_message_id"] = topic_id

                async for message in client.get_chat_history(**history_args):
                    content = ""
                    if message.text:
                        content = message.text
                    elif message.caption:
                        content = message.caption
                    elif message.media:
                        # Opcional: indicar mídia sem legenda para manter consistência com o pedido
                        content = f"[Mídia: {message.media}]"

                    if content:
                        date_str = message.date.strftime("%Y-%m-%d %H:%M:%S")
                        f.write(f"[{date_str}] ID: {message.id}\n")
                        f.write(f"{content}\n")
                        f.write("-" * 30 + "\n\n")
                        messages_extracted += 1

                        if messages_extracted % 100 == 0:
                            logger.info(f"📊 {messages_extracted} mensagens extraídas...")

            logger.info(f"✅ Extração concluída! {messages_extracted} mensagens salvas em: {output_file}")

        except Exception as e:
            logger.error(f"❌ Erro ao extrair mensagens: {e}")
            raise typer.Exit(1)
        finally:
            if 'client' in locals():
                await client.stop()

    asyncio.run(run_extract())


@app.command()
def download(
    origin: str = typer.Option(None, "--origin", "-o", help="ID, username ou link do canal de origem"),
    limit: Optional[int] = typer.Option(None, "--limit", "-l", help="Limite de vídeos para baixar (padrão: todos)"),
    output_dir: Optional[str] = typer.Option(None, "--output", "-d", help="Diretório de saída (padrão: ./downloads/)"),
    restart: bool = typer.Option(False, "--restart", "-r", help="Forçar novo download do zero (apaga dados anteriores)"),
    delete_video: bool = typer.Option(False, "--delete-video", help="Deletar arquivo de vídeo após extrair áudio"),
    message_id: Optional[int] = typer.Option(None, "--message-id", help="ID da mensagem para continuar o download a partir deste ponto")
):
    """
    Baixa todos os vídeos de um canal e extrai os áudios.

    O sistema verifica automaticamente se já existe uma tarefa de download
    para este canal e resume de onde parou. Use --restart para forçar
    um novo download do zero.

    Por padrão, o sistema mantém tanto os vídeos originais quanto os áudios
    extraídos. Use --delete-video para economizar espaço em disco,
    removendo os arquivos de vídeo após a extração do áudio.

    Use --message-id para continuar o download a partir de uma mensagem
    específica, útil para pular conteúdo já baixado ou começar de um ponto
    específico no histórico do canal.

    Exemplos:
    - python main.py download --origin -1002859374479
    - python main.py download --origin -1002859374479 --limit 10
    - python main.py download --origin -1002859374479 --output ./meus_videos/
    - python main.py download --origin -1002859374479 --restart
    - python main.py download --origin -1002859374479 --delete-video
    - python main.py download --origin -1002859374479 --message-id 12345
    """
    if not origin:
        logger.error("❌ O parâmetro --origin é obrigatório.")
        raise typer.Exit(1)

    async def download_videos(delete_video_files: bool = delete_video, start_message_id: Optional[int] = message_id):
        max_download_attempts = 3
        retry_delay_seconds = 2

        def remove_partial_download(file_path: Path) -> None:
            for partial_path in (file_path, file_path.with_name(f"{file_path.name}.temp")):
                if partial_path.exists():
                    try:
                        partial_path.unlink()
                    except OSError as cleanup_error:
                        logger.warning(f"Nao foi possivel remover arquivo parcial: {cleanup_error}")

        async def download_video_with_retry(message, video_path: Path) -> int:
            current_message = message

            for attempt in range(1, max_download_attempts + 1):
                remove_partial_download(video_path)

                try:
                    downloaded_path = await client.download_media(
                        current_message.video,
                        file_name=str(video_path)
                    )
                except FileReferenceExpired:
                    downloaded_path = None
                    logger.warning(
                        f"Referencia do arquivo expirou na tentativa {attempt}/{max_download_attempts}. "
                        "Buscando a mensagem novamente para reiniciar o download do zero..."
                    )

                downloaded_file = Path(downloaded_path) if downloaded_path else video_path
                video_size = downloaded_file.stat().st_size if downloaded_file.exists() else 0

                if downloaded_path and video_size > 0:
                    if downloaded_file != video_path:
                        downloaded_file.replace(video_path)
                        video_size = video_path.stat().st_size
                    if attempt > 1:
                        logger.info(f"Video baixado com sucesso na tentativa {attempt}.")
                    return video_size

                remove_partial_download(video_path)

                if attempt < max_download_attempts:
                    logger.warning(
                        f"Falha ao baixar video na tentativa {attempt}/{max_download_attempts}. "
                        "Renovando referencia e repetindo download do zero..."
                    )
                    fresh_message = await client.get_messages(origin_chat_id, message.id)
                    if not fresh_message or not fresh_message.video:
                        raise RuntimeError(f"Mensagem {message.id} nao contem mais video para download.")
                    current_message = fresh_message
                    await asyncio.sleep(retry_delay_seconds)

            return 0

        try:
            # Carregar configurações
            config = load_config()
            logger.info("⚙️ Configurações carregadas com sucesso")

            # Inicializar cliente Pyrogram
            client = Client(
                config.cloner_session_name,
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

            # Determinar ponto de início baseado em prioridade: message_id > existing_task > 0
            if start_message_id is not None:
                logger.info(f"🎯 Iniciando download a partir da mensagem especificada: {start_message_id}")
                last_message_id = start_message_id
                downloaded_count = 0  # Reset contador quando especifica message_id
            elif existing_task:
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
                # Sanitize chat title for use as a directory name
                safe_title = re.sub(r'[<>:"/\\|?*]', '_', chat.title)
                safe_title = re.sub(r'\s+', ' ', safe_title).strip()
                download_path = Path(config.cloner_download_path).resolve() / f"{origin_chat_id} - {safe_title}"

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

            # Coletar todas as mensagens com vídeo primeiro para inverter a ordem
            video_messages = []
            async for message in client.get_chat_history(origin_chat_id):
                if message.video:
                    video_messages.append(message)

            # Processar na ordem cronológica (inverter a lista)
            video_messages.reverse()

            initial_download_count = downloaded_count
            remaining_messages = [msg for msg in video_messages if msg.id > last_message_id]

            if limit is not None:
                remaining_quota = max(limit - downloaded_count, 0)
                if remaining_quota == 0:
                    logger.info(f"Limite ja atingido antes de iniciar o download (limit={limit}, ja baixados={downloaded_count}).")
                    remaining_messages = []
                else:
                    remaining_messages = remaining_messages[:remaining_quota]

            session_total_videos = len(remaining_messages)
            if session_total_videos == 0:
                logger.info("Nenhum video pendente para baixar com os parametros fornecidos.")
            else:
                logger.info(f"Videos pendentes nesta execucao: {session_total_videos}")

            for message in remaining_messages:
                if limit and downloaded_count >= limit:
                    logger.info(f"Limite atingido: {limit} videos baixados")
                    break
                try:
                    # Nome do arquivo baseado no caption ou fallback para data/ID
                    if message.caption and message.caption.strip():
                        # Limpar caption para uso como nome de arquivo
                        # Remover quebras de linha e caracteres de controle
                        clean_caption = re.sub(r'[\r\n\t\f\v]+', ' ', message.caption.strip())
                        # Remover caracteres inválidos do Windows
                        safe_caption = re.sub(r'[<>:"/\\|?*]', '_', clean_caption)
                        # Remover espaços múltiplos e limitar tamanho
                        safe_caption = re.sub(r'\s+', ' ', safe_caption).strip()[:100]
                        video_filename = f"{safe_caption}_{message.id}_video.mp4"
                        audio_filename = f"{safe_caption}_{message.id}_audio.mp3"
                    else:
                        # Fallback para data e ID se não houver caption
                        date_str = message.date.strftime("%Y%m%d_%H%M%S")
                        video_filename = f"{date_str}_{message.id}_video.mp4"
                        audio_filename = f"{date_str}_{message.id}_audio.mp3"

                    video_path = download_path / video_filename
                    audio_path = download_path / audio_filename

                    session_index = (downloaded_count - initial_download_count) + 1
                    logger.info(f"Baixando video {session_index}/{session_total_videos}: {video_filename}")

                    # Baixar vídeo com retentativa e renovação de file_reference.
                    video_size = await download_video_with_retry(message, video_path)

                    if video_size == 0:
                        logger.error(
                            f"Falha ao baixar video apos {max_download_attempts} tentativas."
                        )
                        failed_count += 1
                        continue

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

                        # Remover vídeo original se delete_video_files for True
                        if delete_video_files:
                            video_path.unlink()
                            logger.info(f"🗑️ Vídeo original removido: {video_filename}")
                        else:
                            logger.info(f"💾 Vídeo original mantido: {video_filename}")

                    except subprocess.CalledProcessError as e:
                        logger.error(f"❌ Erro ao extrair áudio: {e}")
                        logger.error(f"FFmpeg stderr: {e.stderr}")
                        if audio_path.exists():
                            audio_path.unlink()
                        failed_count += 1
                        continue
                    except FileNotFoundError:
                        logger.error("❌ FFmpeg não encontrado. Instale o FFmpeg e adicione ao PATH.")
                        failed_count += 1
                        continue

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


async def run_publish_async(folder_path: str, restart: bool = False, publish_to: Optional[str] = None, topic_id: Optional[int] = None) -> None:
    """
    Async wrapper for the publish operation.

    Args:
        folder_path: Path to the folder to publish.
        restart: Whether to restart the publish task (delete existing task).
        publish_to: ID, username or link of the group/channel to publish the link of the published channel.
        topic_id: ID of the topic (for groups with topic enabled).
    """
    try:
        log_operation_start(logger, "run_publish_async", folder_path=folder_path, restart=restart)

        # Carregar configurações
        config = load_config()
        logger.info("⚙️ Configurações carregadas com sucesso")

        # Inicializar cliente Pyrogram
        client = Client(
            config.cloner_session_name,
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

        # Verificar se a pasta existe
        folder_path_obj = Path(folder_path)
        if not folder_path_obj.exists():
            raise ValueError(f"Pasta não encontrada: {folder_path}")

        if not folder_path_obj.is_dir():
            raise ValueError(f"Caminho não é uma pasta: {folder_path}")

        # Resolver caminho absoluto
        absolute_folder_path = str(folder_path_obj.resolve())
        project_name = folder_path_obj.name

        logger.info(f"📁 Pasta de origem: {absolute_folder_path}")
        logger.info(f"📋 Nome do projeto: {project_name}")

        # Handle restart logic
        if restart:
            logger.info(f"🔄 Modo restart: apagando tarefa e arquivos existentes para {absolute_folder_path}")
            delete_publish_task(absolute_folder_path)

            # Clean up generated files
            project_workspace_path = Path("data/project_workspace") / project_name
            if project_workspace_path.exists():
                logger.info(f"🗑️ Limpando arquivos gerados em: {project_workspace_path}")
                import shutil
                try:
                    shutil.rmtree(project_workspace_path)
                    logger.info("✅ Arquivos gerados removidos com sucesso")
                except Exception as e:
                    logger.warning(f"⚠️ Erro ao limpar arquivos: {e}")

        # Get or create the publish task
        task_data = get_or_create_publish_task(absolute_folder_path, project_name)
        logger.info(f"✅ Tarefa de publicação pronta: {task_data}")

        # Executar pipeline
        logger.info("🚀 Iniciando pipeline de publicação")
        pipeline = PublishPipeline(client, task_data)

        success = await pipeline.run()

        if success:
            logger.info("✅ Pipeline de publicação concluído com sucesso!")

            # Publicar link do canal publicado
            if publish_to:
                dest_chat_id = await resolve_chat_id(client, publish_to)
                logger.info(f"📤 Publicando link do canal publicado para {publish_to} (ID: {dest_chat_id})")

                # Gerar link de convite do canal publicado, se possível
                try:
                    # Supondo que o pipeline cria um canal/clonagem e salva o ID em task_data
                    # Se não houver, apenas publica o nome do projeto
                    canal_nome = project_name
                    canal_link = None
                    if hasattr(pipeline, 'dest_chat_id'):
                        canal_id = getattr(pipeline, 'dest_chat_id')
                        try:
                            canal_link = await client.export_chat_invite_link(canal_id)
                        except Exception:
                            canal_link = None
                    mensagem = f"🎉 Canal publicado: {canal_nome}"
                    if canal_link:
                        mensagem += f"\n🔗 Link: {canal_link}"
                except Exception:
                    mensagem = f"🎉 Canal publicado: {project_name}"

                send_kwargs = {"chat_id": dest_chat_id, "text": mensagem}
                if topic_id is not None:
                    # Pyrogram 2.0.106 não aceita message_thread_id no send_message.
                    # Para grupos-fórum, o ID retornado por list-topics é usado como
                    # reply_to_message_id/top message id do tópico.
                    send_kwargs["reply_to_message_id"] = topic_id
                await client.send_message(**send_kwargs)

        else:
            logger.error("❌ Pipeline de publicação falhou")
            raise typer.Exit(1)

    except Exception as e:
        logger.error(f"❌ Erro na operação de publicação: {e}")
        raise typer.Exit(1)
    finally:
        if 'client' in locals():
            await client.stop()


@app.command()
def publish(
    folder_path: str = typer.Option(..., "--folder", "-f", help="Caminho para a pasta a ser publicada"),
    restart: bool = typer.Option(False, "--restart", "-r", help="Forçar nova publicação do zero (apaga dados anteriores)"),
    publish_to: Optional[str] = typer.Option(
        None,
        "--publish-to",
        "-p",
        help="ID, username ou link do grupo/canal onde publicar o link do canal publicado"
    ),
    topic_id: Optional[int] = typer.Option(
        None,
        "--topic",
        "-t",
        help="ID do tópico (para grupos com tópicos habilitados)"
    )
):
    """
    Publica uma pasta local no Telegram usando o pipeline Zimatise.

    O sistema processa a pasta através de várias etapas:
    1. Compactação de arquivos
    2. Geração de relatórios
    3. Recodificação de vídeos
    4. Junção de arquivos
    5. Adição de timestamps
    6. Upload para Telegram

    O sistema verifica automaticamente se já existe uma tarefa de publicação
    para esta pasta e resume de onde parou. Use --restart para forçar
    uma nova publicação do zero.

    Exemplos:
    - python main.py publish --folder C:/meus_projetos/curso_python
    - python main.py publish --folder C:/meus_projetos/curso_python --restart
    - python main.py publish --folder C:/meus_projetos/curso_python --publish-to -1001234567890 --topic 123
    """
    asyncio.run(run_publish_async(folder_path, restart, publish_to, topic_id))


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


@app.command()
def list_topics(
    chat_id: str = typer.Option(
        None,
        "--id",
        "-i",
        help="ID, username ou link do grupo para listar os tópicos"
    )
):
    """
    Lista todos os tópicos de um grupo com tópicos habilitados.

    Mostra o ID e nome de cada tópico, útil para usar com a opção --topic
    do comando sync.
    """
    try:
        log_operation_start(logger, "list_topics_command", chat_id=chat_id)

        if not chat_id:
            logger.error("❌ O parâmetro --id é obrigatório.")
            logger.info("💡 Exemplo: python main.py list-topics --id -1001234567890")
            raise typer.Exit(1)

        async def list_group_topics():
            # Carregar configurações
            config = load_config()
            logger.info("⚙️ Configurações carregadas com sucesso")

            # Inicializar cliente Pyrogram
            client = Client(
                config.cloner_session_name,
                api_id=config.telegram_api_id,
                api_hash=config.telegram_api_hash
            )

            # Iniciar cliente Pyrogram
            await client.start()
            me = await client.get_me()
            logger.info(f"🤖 Logged in as: {me.first_name} (ID: {me.id})")

            # Resolver ID do chat
            resolved_chat_id = await resolve_chat_id(client, chat_id)
            logger.info(f"🎯 Chat resolvido: {chat_id} -> {resolved_chat_id}")

            try:
                # Obter peer do canal para a chamada da API Raw
                peer = await client.resolve_peer(resolved_chat_id)
                logger.info("ℹ️ Obtendo tópicos com chamada direta à API (channels.GetForumTopics)...")

                # Chamar diretamente a função da API MTProto
                result = await client.invoke(
                    GetForumTopics(
                        channel=peer,
                        offset_date=0,
                        offset_id=0,
                        offset_topic=0,
                        limit=100  # Limite máximo por chamada
                    )
                )

                # A resposta contém uma lista de tópicos
                topics = result.topics

                if not topics:
                    logger.info("📭 Nenhum tópico encontrado neste grupo.")
                    logger.info("💡 Verifique se o grupo realmente possui tópicos criados.")
                    return

                # Exibir tópicos em formato de tabela
                logger.info(f"📊 Encontrados {len(topics)} tópicos:")
                logger.info("─" * 80)
                logger.info(f"{'ID':<8} {'Nome do Tópico'}")
                logger.info("─" * 80)

                for topic in topics:
                    logger.info(f"{topic.id:<8} {topic.title}")

                logger.info("─" * 80)
                logger.info("💡 Use o ID do tópico com a opção --topic no comando sync.")

            except Exception as e:
                logger.error(f"❌ Erro ao obter tópicos: {e}")
                if "CHANNEL_FORUM_MISSING" in str(e):
                    logger.error("💡 O Telegram confirmou que este grupo não é um fórum.")
                elif "CHAT_NOT_FOUND" in str(e):
                    logger.error("💡 Verifique se o ID do grupo está correto.")
                elif "CHAT_WRITE_FORBIDDEN" in str(e):
                    logger.error("💡 Você precisa ter permissão de leitura no grupo.")
                else:
                    logger.error("💡 Verifique se o grupo existe e você tem acesso.")

            finally:
                await client.stop()

        # Executar operação assíncrona
        asyncio.run(list_group_topics())

        log_operation_success(logger, "list_topics_command", chat_id=chat_id)

    except Exception as e:
        log_operation_error(logger, "list_topics_command", e, chat_id=chat_id)
        raise typer.Exit(1)


@app.command(name="list-files")
def list_files(
    origin: str = typer.Option(None, "--origin", "-o", help="ID, username ou link do canal de origem"),
    limit: Optional[int] = typer.Option(None, "--limit", "-l", help="Limite de itens para listar (padrão: todos)")
):
    """
    Lista vídeos e arquivos de um canal com seus captions, sem baixar.
    Útil para verificar os arquivos que o comando download encontraria.
    """
    if not origin:
        logger.error("❌ O parâmetro --origin é obrigatório.")
        raise typer.Exit(1)

    async def run_list():
        try:
            config = load_config()
            client = Client(
                config.cloner_session_name,
                api_id=config.telegram_api_id,
                api_hash=config.telegram_api_hash
            )
            await client.start()

            origin_chat_id = await resolve_chat_id(client, origin)
            chat = await client.get_chat(origin_chat_id)
            logger.info(f"📢 Canal: {chat.title}")

            # Coletar mensagens
            messages = []
            logger.info("Coletando histórico do canal...")
            async for message in client.get_chat_history(origin_chat_id):
                if message.video or message.document:
                    messages.append(message)
                    if limit and len(messages) >= limit:
                        break

            # Processar na ordem cronológica (inverter a lista)
            messages.reverse()

            logger.info(f"📊 Total de vídeos/arquivos encontrados: {len(messages)}")

            for message in messages:
                if message.caption and message.caption.strip():
                    clean_caption = re.sub(r'[\r\n\t\f\v]+', ' ', message.caption.strip())
                    safe_caption = re.sub(r'[<>:"/\\|?*]', '_', clean_caption)
                    safe_caption = re.sub(r'\s+', ' ', safe_caption).strip()[:100]
                    caption_display = safe_caption
                else:
                    caption_display = "Sem caption"

                msg_type = "Vídeo" if message.video else "Arquivo"

                # Para arquivo, tentar pegar o nome original, se possível, para logar junto
                file_name = ""
                if message.document and getattr(message.document, 'file_name', None):
                    file_name = f" [{message.document.file_name}]"
                elif message.video and getattr(message.video, 'file_name', None):
                    file_name = f" [{message.video.file_name}]"

                date_str = message.date.strftime("%Y-%m-%d %H:%M:%S")

                logger.info(f"[{date_str}] ID: {message.id} | Tipo: {msg_type}{file_name} | Caption: {caption_display}")

        except Exception as e:
            logger.error(f"❌ Erro ao listar arquivos: {e}")
            raise typer.Exit(1)
        finally:
            if 'client' in locals():
                await client.stop()

    asyncio.run(run_list())


def main():
    """
    Entry point para o comando chat-clone.
    """
    app()
