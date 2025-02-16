"""
Модуль для обработки и управления GeoJSON файлами с использованием Flask.

Этот модуль предоставляет веб-интерфейс для загрузки GeoJSON файлов, их обработки
и получения тайлов. Он включает в себя следующие основные функции:

1. Загрузка файлов: Позволяет пользователям загружать GeoJSON файлы на сервер.
2. Обработка файлов: Обрабатывает загруженные файлы, добавляя порядковые номера цветов
   и трансформируя их в нужный формат.
3. Получение тайлов: Предоставляет возможность получать тайлы на основе загруженных
   и обработанных GeoJSON файлов.

Основные маршруты:
- GET /: Тестовый маршрут для проверки работы сервера.
- POST /v1/upload: Загружает файл на сервер.
- GET /v1/<layer_id>/<z>/<x>/<y>: Получает тайл по заданным параметрам.

Зависимости:
- Flask
- src.file_handler
- src.file_uploader
"""

import os

from flask import Flask, abort, jsonify, request

from src.common import construct_file_path, file_exists, send_and_remove_file
from src.file_handler import FileHandler, get_basename
from src.file_uploader import FileUploader

app = Flask(__name__)

uploader = FileUploader()
handler = FileHandler()


@app.route('/', methods=['GET'])
def test():
    """
    Тестовый метод проверки работоспособности
    :return: str
    """
    return 'OK'


@app.route('/v1/upload', methods=['POST'])
def upload_file():
    """
    Загрузить файл на диск в /uploads/layer_name, обработать.
    :return: json
    """
    file = uploader.save_file()
    if not file:
        return "Загрузка не удалась", 400

    filesize = os.path.getsize(file)
    filename = get_basename(file)

    handler.handle_upload_geojson(file)
    return jsonify({"message": f"File '{filename}' uploaded successfully",
                    "size": f'{filesize / 1024 / 1024:.1f} Mb',
                    "key": filename})


@app.route('/v1/<string:layer_id>/<int:z>/<int:x>/<int:y>', methods=['GET'])
def get_tile(layer_id, z, x, y):
    """
    route для получения картографических тайлов.
    Обрабатывает GET-запросы, возвращая картографические тайлы по идентификатору слоя,
    уровню масштаба и координатам тайла.
    Обрабатывает параметры `zoom_add_raster` и `black`.
    :route:
        /v1/<string:layer_id>/<int:z>/<int:x>/<int:y>
    :args:
        zoom_add_raster (необязательный): целочисленный, по умолчанию 2.
        black (необязательный): булевый, по умолчанию False.
    :return:
        200 OK: тайл получен и отправлен.
        404 Not Found: тайл или файл не найдены.
    """
    zoom_add_raster = request.args.get('zoom_add_raster', default=2, type=int)
    black = request.args.get('black', default=False, type=bool)

    try:
        o_f = handler.save_tile(layer_id, z=z, x=x, y=y, za=zoom_add_raster, blck=black)
    except AssertionError:
        return abort(404, description="Id not found")

    file_path = construct_file_path(o_f, z, x, y)

    if file_exists(file_path):
        return send_and_remove_file(file_path, o_f)

    abort(404, description="Tile not found")


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
