import os
import tempfile
import logging
from PIL import Image
import subprocess
import shutil

logger = logging.getLogger(__name__)

class FileConverter:
    def __init__(self):
        self.temp_dir = tempfile.mkdtemp()

    def convert(self, input_path: str, target_format: str) -> str:
        ext = os.path.splitext(input_path)[1].lower().lstrip('.')
        logger.info(f"Converting file from .{ext} to .{target_format}")
        if ext in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'tiff']:
            return self._convert_image(input_path, target_format)
        elif ext in ['mp3', 'wav', 'ogg', 'flac', 'aac', 'm4a']:
            return self._convert_audio(input_path, target_format)
        elif ext in ['mp4', 'avi', 'mkv', 'mov', 'webm']:
            return self._convert_video(input_path, target_format)
        elif ext in ['doc', 'docx', 'odt', 'pdf', 'txt', 'rtf']:
            return self._convert_document(input_path, target_format)
        else:
            raise ValueError(f"Unsupported input format: {ext}")

    def _convert_image(self, input_path, target_format):
        img = Image.open(input_path)
        fmt = target_format.upper()
        if fmt == 'JPG':
            fmt = 'JPEG'
        logger.info(f"Saving as {fmt} to {target_format}")
        base = os.path.splitext(os.path.basename(input_path))[0]
        output_path = os.path.join(self.temp_dir, f"{base}.{target_format.lower()}")
        img.save(output_path, format=fmt)
        # Проверка фактического формата
        try:
            with Image.open(output_path) as img2:
                actual = img2.format
                logger.info(f"Actual saved format: {actual}")
        except Exception as e:
            logger.warning(f"Could not verify output: {e}")
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
        if not shutil.which('libreoffice'):
            logger.error("libreoffice not found in PATH")
            raise Exception("libreoffice is not installed")
        base = os.path.splitext(os.path.basename(input_path))[0]
        output_path = os.path.join(self.temp_dir, f"{base}.{target_format.lower()}")
        # Используем libreoffice в headless-режиме
        cmd = [
            'libreoffice', '--headless', '--convert-to', target_format,
            '--outdir', self.temp_dir, input_path
        ]
        logger.info(f"Running: {' '.join(cmd)}")
        subprocess.run(cmd, check=True, capture_output=True)
        # libreoffice создаст файл в выходной директории с именем base.target_format
        expected = os.path.join(self.temp_dir, f"{base}.{target_format.lower()}")
        if os.path.exists(expected):
            return expected
        else:
            # На случай, если имя немного отличается (например, добавил суффикс)
            for f in os.listdir(self.temp_dir):
                if f.endswith(f".{target_format.lower()}"):
                    return os.path.join(self.temp_dir, f)
            raise Exception("Output file not found after conversion")

    def cleanup(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
