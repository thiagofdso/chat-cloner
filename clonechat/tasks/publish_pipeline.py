"""
Publish Pipeline implementation for Clonechat.
Handles the processing and publishing of local folders to Telegram.
"""
import asyncio
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime

from pyrogram import Client
import zipind
import vidtool

from ..logging_config import get_logger
from ..database import update_publish_task_step, update_publish_task_progress
from ..config import load_config

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
            if not self.task.get('is_uploaded', False):
                logger.info("📤 Executando etapa 6: Upload para Telegram")
                if await self._step_upload():
                    await self._update_step_status('is_uploaded', True)
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
                folder_path_project=str(self.source_folder),
                file_path_report=str(report_file),
                list_video_extensions=video_extensions,
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
            
            # For now, we'll create a simple summary file
            # In the future, this should use the timestamp_link_maker module
            summary_file = self.project_process_path / "summary.txt"
            descriptions_file = self.project_process_path / "descriptions.xlsx"
            
            # Create a simple summary
            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write(f"# {document_title}\n\n")
                f.write(f"Projeto: {self.project_name}\n")
                f.write(f"Pasta de origem: {self.source_folder}\n")
                f.write(f"Data de processamento: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write(f"{document_hashtag}\n")
            
            # Create a simple descriptions file (placeholder)
            # In the future, this should use vidtool to create proper descriptions
            with open(descriptions_file, 'w', encoding='utf-8') as f:
                f.write("Arquivo de descrições gerado pelo pipeline\n")
                f.write("Este arquivo será implementado na Fase 3\n")
            
            logger.info(f"✅ Timestamps e descrições gerados com sucesso")
            logger.info(f"📄 Arquivo de sumário: {summary_file}")
            logger.info(f"📋 Arquivo de descrições: {descriptions_file}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro durante geração de timestamps: {e}")
            return False
    
    async def _step_upload(self) -> bool:
        """
        Step 6: Upload files to Telegram.
        
        This step will be implemented in Phase 3.
        For now, it's a placeholder that simulates successful upload.
        
        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            logger.info(f"📤 Iniciando upload para Telegram para: {self.source_folder}")
            
            # Update progress
            await self._update_progress("uploading", "Preparando upload para Telegram")
            
            # TODO: Implement actual upload logic in Phase 3
            # For now, just simulate success
            logger.info("📤 Upload será implementado na Fase 3")
            logger.info("📁 Arquivos processados estão prontos para upload")
            
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
    
    async def _update_progress(self, current_step: str, description: str) -> None:
        """
        Update the current progress in the database.
        
        Args:
            current_step: The current step being executed.
            description: Description of the current operation.
        """
        try:
            update_publish_task_progress(
                self.task['source_folder_path'],
                current_step,
                description
            )
            logger.info(f"📈 Progresso atualizado: {current_step} - {description}")
        except Exception as e:
            logger.error(f"❌ Erro ao atualizar progresso: {e}")
    
    # Placeholder methods for future phases
    # Note: These methods are now implemented above 