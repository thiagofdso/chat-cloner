"""
Publish Pipeline implementation for Clonechat.
Handles the processing and publishing of local folders to Telegram.
"""
import asyncio
from typing import Dict, Any, Optional
from pathlib import Path

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
            
            # TODO: Implement remaining steps in future phases
            logger.info("✅ Etapas 1 e 2 concluídas com sucesso")
            logger.info("📋 Próximas etapas serão implementadas na Fase 2.2")
            
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
    async def _step_reencode(self) -> bool:
        """Step 3: Reencode videos according to plan."""
        logger.info("🎬 Etapa 3: Recodificação de vídeos (a ser implementada)")
        return True
    
    async def _step_join(self) -> bool:
        """Step 4: Join files according to plan."""
        logger.info("🔗 Etapa 4: Junção de arquivos (a ser implementada)")
        return True
    
    async def _step_timestamp(self) -> bool:
        """Step 5: Add timestamps to files."""
        logger.info("⏰ Etapa 5: Adição de timestamps (a ser implementada)")
        return True
    
    async def _step_upload(self) -> bool:
        """Step 6: Upload files to Telegram."""
        logger.info("📤 Etapa 6: Upload para Telegram (a ser implementada)")
        return True 