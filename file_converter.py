import os
import tempfile
import logging
from PIL import Image
import subprocess

logger = logging.getLogger(__name__)

class FileConverter:
    def __init__(self):
        self.temp_dir = tempfile.mkdtemp()

    def convert(self, input_path: str, target_format: str) -> str:
        ext = os.path.splitext(input_path)[1].lower().lstrip('.')
        logger.info(f"Converting file from .{ext} to .{target_format}")
        if ext in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'tiff']:
            return self._convert_image(input_path, target_format)
        elif ext in ['mp3', 'wav', 'ogg', 'flac', 'm4a']:
            return self._convert_audio(input_path, target_format)
        elif ext in ['mp4', 'avi', 'mkv', 'mov', 'webm']:
            return self._convert_video(input_path, target_format)
        elif ext in ['doc', 'docx', 'odt', 'pdf', 'txt']:
            return self._convert_document(input_path, target_format)
        else:
            raise ValueError(f"Unsupported input format: {ext}")

    def _convert_image(self, input_path, target_format):
        img = Image.open(input_path)
        # Преобразуем target_format в формат, понятный Pillow
        fmt = target_format.upper()
        if fmt == 'JPG':
            fmt = 'JPEG'
        # Для TIFF fmt останется 'TIFF' – это правильно
        logger.info(f"Saving as {fmt} to {target_format}")
        base = os.path.splitext(os.path.basename(input_path))[0]
        output_path = os.path.join(self.temp_dir, f"{base}.{target_format.lower()}")
        img.save(output_path, format=fmt)
        return output_path

    def _convert_audio(self, input_path, target_format):
        base = os.path.splitext(os.path.basename(input_path))[0]
        output_path = os.path.join(self.temp_dir, f"{base}.{target_format.lower()}")
        cmd = ['ffmpeg', '-i', input_path, output_path]
        logger.info(f"Running: {' '.join(cmd)}")
        subprocess.run(cmd, check=True, capture_output=True)
        return output_path

    def _convert_video(self, input_path, target_format):
        base = os.path.splitext(os.path.basename(input_path))[0]
        output_path = os.path.join(self.temp_dir, f"{base}.{target_format.lower()}")
        cmd = ['ffmpeg', '-i', input_path, output_path]
        logger.info(f"Running: {' '.join(cmd)}")
        subprocess.run(cmd, check=True, capture_output=True)
        return output_path

    def _convert_document(self, input_path, target_format):
        base = os.path.splitext(os.path.basename(input_path))[0]
        output_path = os.path.join(self.temp_dir, f"{base}.{target_format.lower()}")
        cmd = ['unoconv', '-f', target_format, '-o', output_path, input_path]
        logger.info(f"Running: {' '.join(cmd)}")
        subprocess.run(cmd, check=True, capture_output=True)
        return output_path

    def cleanup(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
