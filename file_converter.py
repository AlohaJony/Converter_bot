import os
import tempfile
import logging
from PIL import Image

logger = logging.getLogger(__name__)

class ImageConverter:
    """Конвертер изображений с использованием Pillow."""

    def __init__(self):
        self.temp_dir = tempfile.mkdtemp()

    def convert(self, input_path: str, target_format: str) -> str:
        """
        Конвертирует изображение в указанный формат.
        Возвращает путь к сконвертированному файлу.
        """
        # Открываем изображение
        img = Image.open(input_path)
        # Формируем имя выходного файла
        base = os.path.splitext(os.path.basename(input_path))[0]
        output_filename = f"{base}.{target_format.lower()}"
        output_path = os.path.join(self.temp_dir, output_filename)

        # Сохраняем в нужном формате
        # Для некоторых форматов нужно указать параметры
        if target_format.lower() == 'jpg':
            target_format = 'jpeg'  # PIL использует 'jpeg'
        img.save(output_path, format=target_format.upper())
        return output_path

    def cleanup(self):
        """Удаляет временную папку."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
