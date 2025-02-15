"""
Модуль для обработки загрузки файлов.

Этот модуль содержит класс `FileUploader`, который предоставляет методы для 
сохранения загруженных файлов на диск. Он использует Flask для обработки 
HTTP-запросов и обеспечивает создание необходимой директории для сохранения 
файлов, если она не существует.

Класс:
    FileUploader: Класс, который управляет загрузкой и сохранением файлов.
"""
import os

from flask import request

from src.common import ensure_folder_exists

class FileUploader:
    """
    Класс для обработки загрузки файлов.

    Этот класс предоставляет методы для сохранения загруженных файлов на диск. 
    Он использует Flask для обработки HTTP-запросов и обеспечивает создание 
    необходимой директории для сохранения файлов, если она не существует.

    :param upload_folder (str): Путь к директории, в которую будут сохраняться загруженные файлы.
    """
    def __init__(self, upload_folder='../uploads'):
        self.upload_folder = upload_folder
        ensure_folder_exists(self.upload_folder)

    def save_file(self):
        """
        Обрабатывает загруженный файл и сохраняет его на диск.

        Метод извлекает файл, переданный через HTTP-запрос, и передает его в метод `save_file_to_disk` для сохранения.

        :return: Путь к сохраненному файлу, если файл был передан; в противном случае возвращается None.
        """
        file = request.files.get('file')
        if file:
            return self.save_file_to_disk(file)
        else:
            return None

    def save_file_to_disk(self, file) -> str:
        """
        Сохраняет загруженный файл на диск в указанную директорию.

        :param file: объект файла, переданный через HTTP-запрос.
        :return: путь к сохраненному файлу.
        """
        filename = file.filename.split(".")[0]
        file_path = os.path.join(self.upload_folder, filename)
        file.save(file_path)
        return file_path