"""
Publish Pipeline implementation for Clonechat.
Handles the processing and publishing of local folders to Telegram.
"""
import asyncio
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime
import csv
import shutil

from pyrogram import Client
import zipind
import vidtool

from ..logging_config import get_logger
from ..database import update_publish_task_step, update_publish_task_progress, set_publish_destination_chat
from ..config import load_config
from ..processor import extract_audio_from_video, delete_local_media, upload_media

logger = get_logger(__name__)


class PublishPipeline:
    """
    Pipeline for processing and publishing local folders to Telegram.
    
    This class orchestrates the complete workflow from folder processing
    to final publication, managing state through the database.
    """
    
    def __init__(self, client: Client, task_data: Dict[str, Any]):
        """
        Initialize the PublishPipeline.
        
        Args:
            client: Pyrogram client instance for Telegram operations.
            task_data: Task data from the database containing folder path and status.
        """
        self.client = client
        self.task = task_data
        self.config = load_config()
        self.source_folder = Path(task_data['source_folder_path'])
        self.project_name = task_data['project_name']
        
        # Setup project paths
        self.project_process_path = self._get_project_process_path()
        self.project_output_path = self.project_process_path / "output_videos"
        
        # Ensure output directory exists
        self.project_output_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"🚀 PublishPipeline inicializado para: {self.project_name} ({self.source_folder})")
        logger.info(f"📁 Pasta de processamento: {self.project_process_path}")
        logger.info(f"📁 Pasta de saída: {self.project_output_path}")
    
    def _get_project_process_path(self) -> Path:
        """
        Get the project processing path based on source folder.
        
        Returns:
            Path: The project processing directory.
        """
        # Create a safe folder name from the source folder
        safe_name = "".join(c for c in self.project_name if c.isalnum() or c in (' ', '_')).rstrip()
        return Path("data") / "project_workspace" / safe_name
    
    async def run(self) -> bool:
        """
        Execute the complete publish pipeline.
        
        This method orchestrates all steps of the pipeline:
        1. Zipping files
        2. Generating reports
        3. Reencoding videos
        4. Joining files
        5. Adding timestamps
        6. Uploading to Telegram
        
        Returns:
            bool: True if pipeline completed successfully, False otherwise.
        """
        logger.info(f"🎯 Iniciando pipeline de publicação para: {self.project_name}")
        
        try:
            # Step 1: Zip files
            if not self.task.get('is_zipped', False):
                logger.info("📦 Executando etapa 1: Compactação de arquivos")
                if await self._step_zip():
                    await self._update_step_status('is_zipped', True)
                else:
                    logger.error("❌ Falha na etapa de compactação")
                    return False
            else:
                logger.info("⏭️ Pulando etapa 1: Compactação já concluída")
            
            # Step 2: Generate reports
            if not self.task.get('is_reported', False):
                logger.info("📊 Executando etapa 2: Geração de relatórios")
                if await self._step_report():
                    await self._update_step_status('is_reported', True)
                else:
                    logger.error("❌ Falha na etapa de relatórios")
                    return False
            else:
                logger.info("⏭️ Pulando etapa 2: Relatórios já gerados")
            
            # Step 3: Reencode videos
            if not self.task.get('is_reencoded', False):
                logger.info("🎬 Executando etapa 3: Recodificação de vídeos")
                if await self._step_reencode():
                    await self._update_step_status('is_reencoded', True)
                else:
                    logger.error("❌ Falha na etapa de recodificação")
                    return False
            else:
                logger.info("⏭️ Pulando etapa 3: Recodificação já concluída")
            
            # Step 4: Join files
            if not self.task.get('is_joined', False):
                logger.info("🔗 Executando etapa 4: Junção de arquivos")
                if await self._step_join():
                    await self._update_step_status('is_joined', True)
                else:
                    logger.error("❌ Falha na etapa de junção")
                    return False
            else:
                logger.info("⏭️ Pulando etapa 4: Junção já concluída")
            
            # Step 5: Add timestamps
            if not self.task.get('is_timestamped', False):
                logger.info("⏰ Executando etapa 5: Adição de timestamps")
                if await self._step_timestamp():
                    await self._update_step_status('is_timestamped', True)
                else:
                    logger.error("❌ Falha na etapa de adição de timestamps")
                    return False
            else:
                logger.info("⏭️ Pulando etapa 5: Timestamps já adicionados")
            
            # Step 6: Upload files
            if not self.task.get('is_published', False):
                logger.info("📤 Executando etapa 6: Upload para Telegram")
                if await self._step_upload():
                    await self._update_step_status('is_published', True)
                else:
                    logger.error("❌ Falha na etapa de upload")
                    return False
            else:
                logger.info("⏭️ Pulando etapa 6: Upload já concluído")
            
            logger.info("✅ Todas as etapas concluídas com sucesso")
            logger.info("📋 Pipeline de processamento completo - arquivos prontos para upload")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro durante execução do pipeline: {e}")
            return False
    
    async def _step_zip(self) -> bool:
        """
        Step 1: Zip files according to size limits.
        
        This step compresses non-video files into ZIP archives based on
        size limits defined in the configuration.
        
        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            logger.info(f"📦 Iniciando compactação de arquivos em: {self.source_folder}")
            
            # Get configuration parameters
            file_size_limit_mb = int(self.config.file_size_limit_mb)
            mode = self.config.mode
            video_extensions = self.config.video_extensions.split(",")
            
            logger.info(f"⚙️ Configuração: limite={file_size_limit_mb}MB, modo={mode}")
            logger.info(f"🎬 Extensões de vídeo ignoradas: {video_extensions}")
            
            # Update progress
            await self._update_progress("zipping", "Iniciando compactação")
            
            # Run zipind
            zipind.zipind_core.run(
                path_folder=str(self.source_folder),
                mb_per_file=file_size_limit_mb,
                path_folder_output=str(self.project_output_path),
                mode=mode,
                ignore_extensions=video_extensions,
            )
            
            logger.info(f"✅ Compactação concluída com sucesso")
            logger.info(f"📁 Arquivos ZIP salvos em: {self.project_output_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro durante compactação: {e}")
            return False
    
    async def _step_report(self) -> bool:
        """
        Step 2: Generate reports using vidtool.
        
        This step creates a detailed report of video files in the project
        folder, including metadata and processing recommendations.
        
        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            logger.info(f"📊 Iniciando geração de relatório para: {self.source_folder}")
            
            # Get configuration parameters
            video_extensions = self.config.video_extensions.split(",")
            reencode_plan = self.config.reencode_plan
            
            # Define report file path
            report_file = self.project_process_path / "video_details.xlsx"
            
            logger.info(f"📋 Arquivo de relatório: {report_file}")
            logger.info(f"🎬 Extensões de vídeo: {video_extensions}")
            logger.info(f"🔄 Plano de recodificação: {reencode_plan}")
            
            # Update progress
            await self._update_progress("reporting", "Gerando relatório de vídeos")
            
            # Generate report using vidtool
            vidtool.step_create_report_filled(
                path_folder=self.source_folder,
                file_path_report=report_file,
                video_extensions=video_extensions,
                reencode_plan=reencode_plan,
            )
            
            logger.info(f"✅ Relatório gerado com sucesso: {report_file}")
            logger.info("📝 Você pode editar o arquivo para ajustar o plano de recodificação")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro durante geração de relatório: {e}")
            return False
    
    async def _step_reencode(self) -> bool:
        """
        Step 3: Reencode videos according to plan.
        
        This step reencodes videos marked in the video_details.xlsx report
        and corrects duration metadata.
        
        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            logger.info(f"🎬 Iniciando recodificação de vídeos para: {self.source_folder}")
            
            # Define paths
            report_file = self.project_process_path / "video_details.xlsx"
            videos_encoded_path = self.project_process_path / "videos_encoded"
            
            # Ensure encoded videos directory exists
            videos_encoded_path.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"📋 Arquivo de relatório: {report_file}")
            logger.info(f"🎬 Pasta de vídeos recodificados: {videos_encoded_path}")
            
            # Update progress
            await self._update_progress("reencoding", "Recodificando vídeos")
            
            # Reencode videos marked in the report
            vidtool.set_make_reencode(str(report_file), str(videos_encoded_path))
            logger.info("✅ Recodificação de vídeos concluída")
            
            # Correct duration metadata if using group plan
            if self.config.reencode_plan == "group":
                logger.info("🔄 Corrigindo metadados de duração")
                vidtool.set_correct_duration(str(report_file))
                logger.info("✅ Metadados de duração corrigidos")
            
            logger.info(f"✅ Recodificação concluída com sucesso")
            logger.info(f"📁 Vídeos recodificados salvos em: {videos_encoded_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro durante recodificação: {e}")
            return False
    
    async def _step_join(self) -> bool:
        """
        Step 4: Join files according to plan.
        
        This step splits videos that are too big and joins them according
        to the group plan defined in the video_details.xlsx report.
        
        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            logger.info(f"🔗 Iniciando junção de arquivos para: {self.source_folder}")
            
            # Get configuration parameters
            file_size_limit_mb = int(self.config.file_size_limit_mb)
            duration_limit = self.config.duration_limit
            start_index = int(self.config.start_index)
            activate_transition = self.config.activate_transition
            
            # Define paths
            report_file = self.project_process_path / "video_details.xlsx"
            videos_splitted_path = self.project_process_path / "videos_splitted"
            videos_joined_path = self.project_output_path
            videos_cache_path = self.project_process_path / "cache"
            videos_encoded_path = self.project_process_path / "videos_encoded"
            
            # Ensure directories exist
            videos_splitted_path.mkdir(parents=True, exist_ok=True)
            videos_joined_path.mkdir(parents=True, exist_ok=True)
            videos_cache_path.mkdir(parents=True, exist_ok=True)
            
            # Get normalized folder name for output
            filename_output = vidtool.get_folder_name_normalized(self.source_folder)
            
            logger.info(f"📋 Arquivo de relatório: {report_file}")
            logger.info(f"✂️ Pasta de vídeos divididos: {videos_splitted_path}")
            logger.info(f"🔗 Pasta de vídeos juntados: {videos_joined_path}")
            logger.info(f"💾 Pasta de cache: {videos_cache_path}")
            logger.info(f"📁 Nome do arquivo de saída: {filename_output}")
            
            # Update progress
            await self._update_progress("joining", "Juntando arquivos de vídeo")
            
            # Fill group column if using group plan
            if self.config.reencode_plan == "group":
                logger.info("📊 Preenchendo coluna de grupo")
                vidtool.set_group_column(str(report_file))
                logger.info("✅ Coluna de grupo preenchida")
            
            # Split videos that are too big
            logger.info("✂️ Dividindo vídeos muito grandes")
            vidtool.set_split_videos(
                str(report_file),
                file_size_limit_mb,
                str(videos_splitted_path),
                duration_limit,
            )
            logger.info("✅ Vídeos divididos")
            
            # Join videos if using group plan
            if self.config.reencode_plan == "group":
                logger.info("🔗 Juntando vídeos")
                vidtool.set_join_videos(
                    str(report_file),
                    file_size_limit_mb,
                    filename_output,
                    str(videos_joined_path),
                    str(videos_cache_path),
                    duration_limit,
                    start_index,
                    activate_transition,
                )
                logger.info("✅ Vídeos juntados")
            else:
                # Modo single: copiar vídeos finais para output_videos
                logger.info("📋 Modo single: copiando vídeos finais para output_videos")
                # Preferir vídeos recodificados, senão originais
                encoded_videos = list(videos_encoded_path.glob("*.mp4"))
                if encoded_videos:
                    for video in encoded_videos:
                        shutil.copy2(video, videos_joined_path / video.name)
                else:
                    # Se não houver recodificados, copiar originais
                    for video in self.source_folder.glob("*.mp4"):
                        shutil.copy2(video, videos_joined_path / video.name)
                logger.info("✅ Vídeos copiados para output_videos")
            
            logger.info(f"✅ Junção de arquivos concluída com sucesso")
            logger.info(f"📁 Arquivos finais salvos em: {videos_joined_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro durante junção de arquivos: {e}")
            return False
    
    async def _step_timestamp(self) -> bool:
        """
        Step 5: Add timestamps to files.
        
        This step creates descriptions.xlsx and summary.txt files with
        timestamps and metadata for the project.
        
        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            logger.info(f"⏰ Iniciando geração de timestamps para: {self.source_folder}")
            
            # Get configuration parameters
            hashtag_index = self.config.hashtag_index
            start_index = int(self.config.start_index)
            path_summary_top = self.config.path_summary_top
            path_summary_bot = self.config.path_summary_bot
            document_hashtag = self.config.document_hashtag
            document_title = self.config.document_title
            
            # Create summary dictionary
            dict_summary = {
                "path_summary_top": path_summary_top,
                "path_summary_bot": path_summary_bot
            }
            
            # Define paths
            report_file = self.project_process_path / "video_details.xlsx"
            
            logger.info(f"📋 Arquivo de relatório: {report_file}")
            logger.info(f"📊 Configuração: hashtag_index={hashtag_index}, start_index={start_index}")
            
            # Update progress
            await self._update_progress("timestamping", "Gerando timestamps e descrições")
            
            # Create summary file
            summary_file = self.project_process_path / "summary.txt"
            descriptions_file = self.project_process_path / "descriptions.xlsx"
            upload_plan_file = self.project_process_path / "upload_plan.csv"
            
            # Create upload plan including both ZIP files (first) and videos (second)
            files_to_upload = []
            
            # Add ZIP files (documents) FIRST with enumerated tags
            zip_files = list(self.project_output_path.glob("*.zip*"))
            if zip_files:
                logger.info(f"📋 Encontrados {len(zip_files)} arquivos ZIP para upload")
                for i, zip_file in enumerate(zip_files, start=1):
                    # Create enumerated document tag using config prefix with #
                    doc_tag = f"#{document_hashtag}{i:03d}"
                    files_to_upload.append({
                        'file_output': str(zip_file),
                        'description': doc_tag,
                        'type': 'document',
                        'order': i  # ZIP files come first
                    })
            
            # Add output videos SECOND
            output_videos = list(self.project_output_path.glob("*.mp4"))
            if output_videos:
                logger.info(f"📋 Encontrados {len(output_videos)} vídeos para upload")
                for i, video_file in enumerate(output_videos, start=start_index):
                    # Caption: hashtag do índice (3 dígitos) + nome do vídeo (com extensão)
                    if hashtag_index and hashtag_index.strip() and hashtag_index.lower() != "false":
                        description = f"#{hashtag_index}{i:03d} {video_file.name}"
                    else:
                        description = f"#{i:03d} {video_file.name}"
                    files_to_upload.append({
                        'file_output': str(video_file),
                        'description': description,
                        'type': 'video',
                        'order': len(zip_files) + i  # Videos come after ZIPs
                    })
            
            # Write upload plan (ZIPs first, then videos)
            if files_to_upload:
                logger.info(f"📋 Criando plano de upload com {len(files_to_upload)} arquivos")
                
                with open(upload_plan_file, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(['file_output', 'description'])
                    
                    # Sort by order to ensure ZIPs come first
                    files_to_upload.sort(key=lambda x: x['order'])
                    
                    for file_info in files_to_upload:
                        writer.writerow([file_info['file_output'], file_info['description']])
                
                logger.info(f"✅ Plano de upload criado: {upload_plan_file}")
            else:
                logger.warning("⚠️ Nenhum arquivo encontrado para upload")
            
            # Create summary with folder structure and video links
            summary_content = "⚠️ Clique aqui para ver o sumário! ⚠️\n\n"
            summary_content += "Siga o contéudo do mapa:\n\n\n"
            
            # Add documents section
            if zip_files:
                summary_content += f"{document_title}\n"
                for i, zip_file in enumerate(zip_files, start=1):
                    summary_content += f"#{document_hashtag}{i:03d}\n"
                summary_content += "\n"
            
            # Add video structure with folder hierarchy
            if output_videos:
                # Get folder structure from source folder
                source_path = Path(self.source_folder)
                folder_name = source_path.name
                
                summary_content += f"= {folder_name}\n"
                summary_content += "== 1.Introducao\n"
                
                # Add video hashtags
                video_hashtags = []
                for i, video_file in enumerate(output_videos, start=start_index):
                    if hashtag_index and hashtag_index.strip() and hashtag_index.lower() != "false":
                        # Use the hashtag_index value from config (e.g., "F", "Block")
                        video_hashtags.append(f"#{hashtag_index}{i:03d}")
                    else:
                        video_hashtags.append(f"#{i:03d}")
                
                summary_content += " ".join(video_hashtags) + "\n"
            
            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write(summary_content)
            
            # Create a simple descriptions file (placeholder)
            # In the future, this should use vidtool to create proper descriptions
            with open(descriptions_file, 'w', encoding='utf-8') as f:
                f.write("Arquivo de descrições gerado pelo pipeline\n")
                f.write("Este arquivo será implementado na Fase 3\n")
            
            logger.info(f"✅ Timestamps e descrições gerados com sucesso")
            logger.info(f"📄 Arquivo de sumário: {summary_file}")
            logger.info(f"📋 Arquivo de descrições: {descriptions_file}")
            if files_to_upload:
                logger.info(f"📋 Plano de upload: {upload_plan_file}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro durante geração de timestamps: {e}")
            return False
    
    async def _step_upload(self) -> bool:
        """
        Step 6: Upload files to Telegram.
        
        This step uploads all processed files to a Telegram channel and
        pins the summary message. No audio extraction is performed.
        
        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            logger.info(f"📤 Iniciando upload para Telegram para: {self.source_folder}")
            
            # Update progress
            await self._update_progress("uploading", "Preparando upload para Telegram")
            
            # Ensure destination channel exists
            dest_chat_id = await self._ensure_destination_channel()
            logger.info(f"🎯 Canal de destino confirmado: {dest_chat_id}")
            
            # Read upload plan
            files_to_upload = self._read_upload_plan()
            
            if not files_to_upload:
                logger.warning("⚠️ No files found in upload plan")
                # Try to upload summary anyway
                await self._upload_summary_and_pin(dest_chat_id)
                return True
            
            # Get last uploaded file for resume functionality
            last_uploaded = self.task.get('last_uploaded_file', '')
            started_uploading = False
            
            # Upload each file
            total_files = len(files_to_upload)
            uploaded_count = 0
            
            for i, file_info in enumerate(files_to_upload):
                try:
                    # Get file path and description
                    file_output = file_info.get('file_output', '')
                    description = file_info.get('description', '')
                    
                    if not file_output:
                        logger.warning(f"⚠️ Skipping file with no output path at index {i}")
                        continue
                    
                    file_path = Path(file_output)
                    
                    # Resume functionality: skip files already uploaded
                    if last_uploaded and not started_uploading:
                        if str(file_path) == last_uploaded:
                            started_uploading = True
                            logger.info(f"🔄 Resuming upload from: {file_path.name}")
                        else:
                            logger.info(f"⏭️ Skipping already uploaded: {file_path.name}")
                            continue
                    else:
                        started_uploading = True
                    
                    # Update progress
                    await self._update_progress(
                        "uploading", 
                        f"Enviando {file_path.name} ({i+1}/{total_files})",
                        str(file_path)
                    )
                    
                    # Upload file (no audio extraction)
                    success = await self._upload_file(
                        file_path, dest_chat_id, description
                    )
                    
                    if success:
                        uploaded_count += 1
                        logger.info(f"✅ Uploaded {file_path.name} ({uploaded_count}/{total_files})")
                        
                        # Update last uploaded file in database
                        from ..database import update_publish_task_progress
                        update_publish_task_progress(
                            self.task['source_folder_path'], 
                            "uploading", 
                            str(file_path)
                        )
                    else:
                        logger.error(f"❌ Failed to upload {file_path.name}")
                    
                    # Small delay between uploads to avoid rate limits
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    logger.error(f"❌ Error uploading file at index {i}: {e}")
                    continue
            
            # Upload and pin summary
            logger.info("📋 Uploading summary and pinning message")
            summary_success = await self._upload_summary_and_pin(dest_chat_id)
            
            if summary_success:
                logger.info("✅ Summary uploaded and pinned successfully")
            else:
                logger.warning("⚠️ Failed to upload or pin summary")
            
            # Mark upload as complete
            update_publish_task_step(self.task['source_folder_path'], 'is_published', True)
            await self._update_progress("completed", f"Upload concluído: {uploaded_count}/{total_files} arquivos")
            
            logger.info(f"🎉 Upload completed successfully: {uploaded_count}/{total_files} files uploaded")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro durante upload: {e}")
            return False
    
    async def _update_step_status(self, step_flag: str, status: bool) -> None:
        """
        Update the status of a pipeline step in the database.
        
        Args:
            step_flag: The step flag to update (e.g., 'is_zipped').
            status: The new status value.
        """
        try:
            update_publish_task_step(
                self.task['source_folder_path'], 
                step_flag, 
                status
            )
            logger.info(f"💾 Status atualizado: {step_flag} = {status}")
        except Exception as e:
            logger.error(f"❌ Erro ao atualizar status {step_flag}: {e}")
    
    async def _update_progress(self, current_step: str, description: str, last_file: Optional[str] = None) -> None:
        """
        Update the current progress in the database.
        
        Args:
            current_step: The current step being executed.
            description: Description of the current operation.
            last_file: The last file that was processed (optional).
        """
        try:
            update_publish_task_progress(
                self.task['source_folder_path'],
                current_step,
                last_file
            )
            logger.info(f"📈 Progresso atualizado: {current_step} - {description}")
        except Exception as e:
            logger.error(f"❌ Erro ao atualizar progresso: {e}")
    
    async def _ensure_destination_channel(self) -> int:
        """
        Ensure a destination channel exists for publishing.
        
        If no destination channel is set in the task, creates a new one.
        If one exists, verifies access to it.
        
        Returns:
            int: The destination channel ID.
        """
        try:
            # Check if we already have a destination channel
            if self.task.get('destination_chat_id'):
                dest_chat_id = self.task['destination_chat_id']
                logger.info(f"🎯 Using existing destination channel: {dest_chat_id}")
                
                # Verify the destination channel exists and we have access
                try:
                    dest_chat = await self.client.get_chat(dest_chat_id)
                    logger.info(f"✅ Destination channel verified: {dest_chat.title} (ID: {dest_chat_id})")
                    return dest_chat_id
                except Exception as e:
                    logger.warning(f"⚠️ Cannot access destination channel {dest_chat_id}: {e}")
                    logger.info("🆕 Will create a new destination channel")
            
            # Create new destination channel
            logger.info("🆕 Creating new destination channel for publishing")
            
            # Create channel title based on project name (replace underscores with spaces)
            channel_title = self.project_name.replace('_', ' ')
            
            # Calculate channel description with metadata
            total_size = self._calculate_total_size()
            total_duration = self._calculate_total_duration()
            
            # Get channel description configuration
            size_label = self.config.channel_size_label
            duration_label = self.config.channel_duration_label
            invite_label = self.config.channel_invite_label
            
            # Create the channel with empty description first
            dest_chat = await self.client.create_channel(
                title=channel_title,
                description=""
            )
            
            dest_chat_id = dest_chat.id
            logger.info(f"✅ Destination channel created: {channel_title} (ID: {dest_chat_id})")
            
            # Get invite link
            invite_link = await self._get_channel_invite_link(dest_chat_id)
            
            # Create full description with title and metadata
            full_description = f"{channel_title}\n{size_label}: {total_size}\n{duration_label}: {total_duration}\n{invite_label}: {invite_link}"
            
            try:
                # Update the description using set_chat_description
                logger.info(f"🔄 Attempting to update channel description for channel ID: {dest_chat_id}")
                logger.info(f"📝 Description content: {full_description}")
                
                # Update the description using the simpler method
                await self.client.set_chat_description(
                    chat_id=dest_chat_id,
                    description=full_description
                )
                
                logger.info("✅ Channel description updated successfully")
                
                # Verify the update by getting the channel info
                try:
                    updated_chat = await self.client.get_chat(dest_chat_id)
                    if updated_chat.description:
                        logger.info(f"✅ Description verified: {updated_chat.description[:100]}...")
                    else:
                        logger.warning("⚠️ Description appears to be empty after update")
                except Exception as verify_error:
                    logger.warning(f"⚠️ Could not verify description update: {verify_error}")
                
            except Exception as e:
                logger.error(f"❌ Could not update channel description: {e}")
                logger.error(f"❌ Error type: {type(e).__name__}")
                logger.error(f"❌ Error details: {str(e)}")
                logger.info(f"📋 Manual update needed. Description: {full_description}")
            
            # Save the destination channel ID to the database
            set_publish_destination_chat(self.task['source_folder_path'], dest_chat_id)
            logger.info(f"💾 Destination channel ID saved to database: {dest_chat_id}")
            
            return dest_chat_id
            
        except Exception as e:
            logger.error(f"❌ Error ensuring destination channel: {e}")
            raise
    
    def _read_upload_plan(self) -> List[Dict[str, str]]:
        """
        Read the upload_plan.csv file to get the list of files to upload.
        
        Returns:
            List[Dict[str, str]]: List of file information dictionaries.
        """
        upload_plan_path = self.project_process_path / "upload_plan.csv"
        
        if not upload_plan_path.exists():
            logger.warning(f"⚠️ Upload plan not found: {upload_plan_path}")
            return []
        
        try:
            files_to_upload = []
            with open(upload_plan_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    files_to_upload.append(row)
            
            logger.info(f"📋 Found {len(files_to_upload)} files in upload plan")
            return files_to_upload
            
        except Exception as e:
            logger.error(f"❌ Error reading upload plan: {e}")
            return []
    
    def _get_message_type(self, file_path: Path) -> str:
        """
        Determine the message type based on file extension.
        
        Args:
            file_path: Path to the file.
            
        Returns:
            str: Message type (video, document, photo, audio).
        """
        suffix = file_path.suffix.lower()
        
        if suffix in ['.mp4', '.mkv', '.avi', '.mov']:
            return 'video'
        elif suffix in ['.jpg', '.jpeg', '.png', '.gif']:
            return 'photo'
        elif suffix in ['.mp3', '.ogg', '.wav', '.flac']:
            return 'audio'
        else:
            return 'document'
    
    async def _upload_file(self, file_path: Path, dest_chat_id: int, caption: str = "") -> bool:
        """
        Upload a file to Telegram (no audio extraction).
        
        Args:
            file_path: Path to the file to upload.
            dest_chat_id: Destination chat ID.
            caption: Optional caption for the file.
            
        Returns:
            bool: True if upload was successful.
        """
        try:
            if not file_path.exists():
                logger.warning(f"⚠️ File not found: {file_path}")
                return False
            
            message_type = self._get_message_type(file_path)
            logger.info(f"📤 Uploading {file_path.name} as {message_type}")
            
            # Upload the original file
            await upload_media(
                client=self.client,
                file_path=file_path,
                destination_chat=dest_chat_id,
                caption=caption,
                message_type=message_type
            )
            
            logger.info(f"✅ Successfully uploaded {file_path.name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to upload {file_path.name}: {e}")
            return False
    
    async def _upload_summary_and_pin(self, dest_chat_id: int) -> bool:
        """
        Upload the summary.txt file and pin it to the channel.
        
        Args:
            dest_chat_id: Destination chat ID.
            
        Returns:
            bool: True if successful.
        """
        try:
            summary_path = self.project_process_path / "summary.txt"
            
            if not summary_path.exists():
                logger.warning(f"⚠️ Summary file not found: {summary_path}")
                return False
            
            # Read summary content
            with open(summary_path, 'r', encoding='utf-8') as f:
                summary_content = f.read()
            
            if not summary_content.strip():
                logger.warning("⚠️ Summary file is empty")
                return False
            
            logger.info("📋 Uploading summary to channel")
            
            # Split content if it's too long (Telegram limit is 4096 characters)
            max_length = 4000
            if len(summary_content) > max_length:
                # Split by lines first
                lines = summary_content.split('\n')
                chunks = []
                current_chunk = []
                current_length = 0
                
                for line in lines:
                    if current_length + len(line) + 1 > max_length:
                        if current_chunk:
                            chunks.append('\n'.join(current_chunk))
                            current_chunk = [line]
                            current_length = len(line)
                        else:
                            # Single line is too long, split by words
                            words = line.split()
                            for word in words:
                                if current_length + len(word) + 1 > max_length:
                                    if current_chunk:
                                        chunks.append(' '.join(current_chunk))
                                        current_chunk = [word]
                                        current_length = len(word)
                                    else:
                                        chunks.append(word[:max_length])
                                        current_chunk = []
                                        current_length = 0
                                else:
                                    current_chunk.append(word)
                                    current_length += len(word) + 1
                    else:
                        current_chunk.append(line)
                        current_length += len(line) + 1
                
                if current_chunk:
                    chunks.append('\n'.join(current_chunk))
            else:
                chunks = [summary_content]
            
            # Upload each chunk
            first_message = None
            for i, chunk in enumerate(chunks):
                message = await self.client.send_message(
                    chat_id=dest_chat_id,
                    text=chunk,
                    disable_notification=True
                )
                
                if i == 0:
                    first_message = message
                    logger.info(f"📌 First summary message sent (ID: {message.id})")
            
            # Pin the first message
            if first_message:
                await self.client.pin_chat_message(dest_chat_id, first_message.id)
                logger.info(f"📌 Summary message pinned (ID: {first_message.id})")
            
            logger.info("✅ Summary uploaded and pinned successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to upload and pin summary: {e}")
            return False
    
    def _calculate_total_size(self) -> str:
        """
        Calculate total size of all files to be uploaded.
        
        Returns:
            str: Total size in human readable format (e.g., "109.3 GB")
        """
        try:
            total_size = 0
            
            # Calculate size of ZIP files
            zip_files = list(self.project_output_path.glob("*.zip*"))
            for zip_file in zip_files:
                total_size += zip_file.stat().st_size
            
            # Calculate size of video files
            video_files = list(self.project_output_path.glob("*.mp4"))
            for video_file in video_files:
                total_size += video_file.stat().st_size
            
            # Convert to human readable format
            if total_size >= 1024**3:  # GB
                return f"{total_size / (1024**3):.1f} GB"
            elif total_size >= 1024**2:  # MB
                return f"{total_size / (1024**2):.1f} MB"
            elif total_size >= 1024:  # KB
                return f"{total_size / 1024:.1f} KB"
            else:
                return f"{total_size} B"
                
        except Exception as e:
            logger.warning(f"⚠️ Error calculating total size: {e}")
            return "Unknown"
    
    def _calculate_total_duration(self) -> str:
        """
        Calculate total duration of all video files.
        
        Returns:
            str: Total duration in human readable format (e.g., "447h 47min")
        """
        try:
            import subprocess
            total_seconds = 0
            
            # Get duration of all video files
            video_files = list(self.project_output_path.glob("*.mp4"))
            for video_file in video_files:
                try:
                    # Use ffprobe to get duration
                    result = subprocess.run([
                        'ffprobe', '-v', 'quiet', '-show_entries', 
                        'format=duration', '-of', 'csv=p=0', str(video_file)
                    ], capture_output=True, text=True, timeout=10)
                    
                    if result.returncode == 0:
                        duration = float(result.stdout.strip())
                        total_seconds += duration
                except Exception as e:
                    logger.warning(f"⚠️ Error getting duration for {video_file.name}: {e}")
                    continue
            
            # Convert to hours and minutes
            if total_seconds > 0:
                hours = int(total_seconds // 3600)
                minutes = int((total_seconds % 3600) // 60)
                return f"{hours}h {minutes}min"
            else:
                return "0h 0min"
                
        except Exception as e:
            logger.warning(f"⚠️ Error calculating total duration: {e}")
            return "Unknown"
    
    async def _get_channel_invite_link(self, chat_id: int) -> str:
        """
        Get or create invite link for the channel.
        
        Args:
            chat_id: Channel ID.
            
        Returns:
            str: Invite link.
        """
        try:
            logger.info(f"🔗 Generating invite link for channel ID: {chat_id}")
            
            # Generate the invite link using Pyrogram
            try:
                invite_link = await self.client.export_chat_invite_link(chat_id)
                logger.info(f"🔗 Generated invite link: {invite_link}")
                return invite_link
            except Exception as e:
                logger.warning(f"⚠️ Could not generate invite link, using direct link: {e}")
                # Fallback to direct link if invite link generation fails
                invite_link = f"https://t.me/c/{str(chat_id)[4:]}/1"
                logger.info(f"🔗 Using fallback direct link: {invite_link}")
                return invite_link
            
        except Exception as e:
            logger.error(f"❌ Failed to get invite link for channel {chat_id}: {e}")
            return "Link não disponível"
    
    # Placeholder methods for future phases
    # Note: These methods are now implemented above 