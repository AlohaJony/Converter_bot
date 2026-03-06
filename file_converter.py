import os
import tempfile
import logging
import subprocess
import time
from PIL import Image
import pysubs2

logger = logging.getLogger(__name__)

class FileConverter:
    def __init__(self):
        self.temp_dir = tempfile.mkdtemp()

    def convert(self, input_path: str, target_format: str) -> str:
        ext = os.path.splitext(input_path)[1].lower().lstrip('.')
        logger.info(f"Converting file from .{ext} to .{target_format}")

        # Определяем категорию по расширению
        if ext in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'tiff', 'ico', 'heic', 'psd', 'svg']:
            return self._convert_image(input_path, target_format)
        elif ext in ['mp3', 'wav', 'ogg', 'flac', 'aac', 'm4a', 'opus', 'wma', 'amr']:
            return self._convert_audio(input_path, target_format)
        elif ext in ['mp4', 'avi', 'mkv', 'mov', 'webm', 'flv', '3gp', 'wmv', 'mpeg', 'vob']:
            return self._convert_video(input_path, target_format)
        elif ext in ['txt', 'rtf', 'doc', 'docx', 'odt', 'pdf']:
            return self._convert_document(input_path, target_format)
        elif ext in ['xls', 'xlsx', 'ods', 'csv']:
            return self._convert_spreadsheet(input_path, target_format)
        elif ext in ['ppt', 'pptx', 'odp']:
            return self._convert_presentation(input_path, target_format)
        elif ext in ['epub', 'mobi', 'fb2', 'cbr', 'cbz', 'djvu']:
            return self._convert_ebook(input_path, target_format)
        elif ext in ['srt', 'vtt', 'ass', 'ssa', 'lrc']:
            return self._convert_subtitle(input_path, target_format)
        elif ext in ['ttf', 'otf', 'woff', 'woff2']:
            return self._convert_font(input_path, target_format)
        else:
            raise ValueError(f"Unsupported input format: {ext}")

    # --- Изображения (Pillow + ImageMagick для сложных) ---
    def _convert_image(self, input_path, target_format):
        # Для форматов, не поддерживаемых Pillow, используем ImageMagick
        if input_path.endswith('.heic') or input_path.endswith('.psd') or input_path.endswith('.svg'):
            cmd = ['convert', input_path, f"{target_format}:{self._get_output_path(input_path, target_format)}"]
            subprocess.run(cmd, check=True)
            return self._get_output_path(input_path, target_format)

        img = Image.open(input_path)
        fmt = target_format.upper()
        if fmt == 'JPG':
            fmt = 'JPEG'
        output_path = self._get_output_path(input_path, target_format)
        img.save(output_path, format=fmt)
        return output_path

    # --- Аудио (через pydub / ffmpeg) ---
    def _convert_audio(self, input_path, target_format):
        from pydub import AudioSegment
        audio = AudioSegment.from_file(input_path)
        output_path = self._get_output_path(input_path, target_format)
        # Для aac и m4a используем формат 'ipod' (MP4 контейнер с AAC)
        if target_format in ('aac', 'm4a'):
            audio.export(output_path, format='ipod', codec='aac')
        else:
            audio.export(output_path, format=target_format)
        return output_path

    # --- Видео (через moviepy / ffmpeg) ---
    def _convert_video(self, input_path, target_format):
        from moviepy.editor import VideoFileClip
        clip = VideoFileClip(input_path)
        output_path = self._get_output_path(input_path, target_format)
        try:
            if target_format == 'gif':
                # Уменьшаем размер для GIF
                clip_resized = clip.resize(height=480)
                clip_resized.write_gif(output_path, fps=10, program='ffmpeg')
            else:
                clip.write_videofile(output_path, codec='libx264')
            return output_path
        finally:
            clip.close()

    # --- Документы ---
    def _convert_document(self, input_path, target_format):
        base, ext = os.path.splitext(os.path.basename(input_path))
        output_path = os.path.join(self.temp_dir, f"{base}.{target_format.lower()}")

        # PDF -> TXT
        if input_path.endswith('.pdf') and target_format == 'txt':
            subprocess.run(['pdftotext', input_path, output_path], check=True)
            return output_path

        # PDF -> DOCX
        if input_path.endswith('.pdf') and target_format == 'docx':
            from pdf2docx import Converter
            cv = Converter(input_path)
            cv.convert(output_path, start=0, end=None)
            cv.close()
            return output_path

        # Документы Office через libreoffice
        cmd = ['libreoffice', '--headless', '--convert-to', target_format,
               '--outdir', self.temp_dir, input_path]
        subprocess.run(cmd, check=True, timeout=60)

        # Ищем созданный файл
        for f in os.listdir(self.temp_dir):
            if f.lower().endswith(f".{target_format.lower()}"):
                return os.path.join(self.temp_dir, f)
        raise Exception("Output file not found after conversion")

    # --- Электронные таблицы ---
    def _convert_spreadsheet(self, input_path, target_format):
        import pandas as pd
        base = os.path.splitext(os.path.basename(input_path))[0]
        output_path = os.path.join(self.temp_dir, f"{base}.{target_format.lower()}")

        if target_format in ['xlsx', 'xls', 'ods']:
            df = pd.read_excel(input_path) if input_path.endswith(('.xlsx','.xls')) else pd.read_csv(input_path)
            df.to_excel(output_path, index=False)
        elif target_format == 'csv':
            df = pd.read_excel(input_path) if input_path.endswith(('.xlsx','.xls')) else pd.read_csv(input_path)
            df.to_csv(output_path, index=False)
        return output_path

    # --- Презентации ---
    def _convert_presentation(self, input_path, target_format):
        # Для PPTX используем python-pptx, для остальных - libreoffice
        if target_format == 'pdf':
            cmd = ['libreoffice', '--headless', '--convert-to', 'pdf',
                   '--outdir', self.temp_dir, input_path]
            subprocess.run(cmd, check=True)
            base = os.path.splitext(os.path.basename(input_path))[0]
            return os.path.join(self.temp_dir, f"{base}.pdf")
        else:
            # Для конвертации между PPT и PPTX можно использовать python-pptx, но пока через libreoffice
            cmd = ['libreoffice', '--headless', '--convert-to', target_format,
                   '--outdir', self.temp_dir, input_path]
            subprocess.run(cmd, check=True)
            base = os.path.splitext(os.path.basename(input_path))[0]
            return os.path.join(self.temp_dir, f"{base}.{target_format}")

    # --- Электронные книги ---
    def _convert_ebook(self, input_path, target_format):
        # Используем pandoc или calibre
        if target_format in ['epub', 'mobi', 'fb2', 'pdf', 'txt']:
            output_path = self._get_output_path(input_path, target_format)
            cmd = ['pandoc', input_path, '-o', output_path]
            subprocess.run(cmd, check=True)
            return output_path
        else:
            raise Exception(f"Unsupported ebook target format: {target_format}")

    # --- Субтитры ---
    def _convert_subtitle(self, input_path, target_format):
        subs = pysubs2.load(input_path)
        output_path = self._get_output_path(input_path, target_format)
        subs.save(output_path)
        return output_path

    # --- Шрифты (базово) ---
    def _convert_font(self, input_path, target_format):
        from fontTools.ttLib import TTFont
        font = TTFont(input_path)
        output_path = self._get_output_path(input_path, target_format)
        font.save(output_path)
        return output_path

    # --- Вспомогательный метод ---
    def _get_output_path(self, input_path, target_format):
        base = os.path.splitext(os.path.basename(input_path))[0]
        return os.path.join(self.temp_dir, f"{base}.{target_format.lower()}")

    def cleanup(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
