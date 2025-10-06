from pathlib import Path
import subprocess
import os
from typing import Tuple

from ..utils.logger import logger

class MediaProcessor:
    """Classe responsável por extrair o áudio de arquivos de vídeo."""

    @staticmethod
    def extract_audio(video_path: Path) -> Path:
        """Extrai o áudio de um arquivo de vídeo para um arquivo .mp3.

        Args:
            video_path: Caminho para o arquivo de vídeo.

        Returns:
            Caminho para o arquivo de áudio extraído (.mp3).
        """
        # Usa os.path para garantir compatibilidade
        video_str = str(video_path)
        video_dir = os.path.dirname(video_str)
        filename = os.path.splitext(os.path.basename(video_str))[0]        
        audio_file_path = Path(os.path.join(video_dir, f"{filename}.mp3"))
        logger.info(f"Extraindo áudio de {video_path} para {audio_file_path}")
        if not audio_file_path.exists():
            try:
                command = [
                    'ffmpeg',
                    '-i', video_str,
                    '-vn',
                    '-acodec', 'libmp3lame',
                    '-b:a', '192k',
                    str(audio_file_path)
                ]
                subprocess.run(command, check=True)
                logger.info(f"Áudio extraído com sucesso: {audio_file_path}")
            except subprocess.CalledProcessError as e:
                logger.error(f"Erro ao extrair áudio: {e.stderr.decode() if e.stderr else e}")
                raise RuntimeError(f"Falha ao extrair áudio de {video_path}") from e
        else:
            logger.warning(f"Arquivo de áudio já existe: {audio_file_path}")
        return audio_file_path 