import os
import shutil

from flask import Flask, jsonify, send_file, abort

from src.file_handler import FileHandler
from src.file_uploader import FileUploader

app = Flask(__name__)

uploader = FileUploader()
handler = FileHandler()


@app.route('/', methods=['GET'])
def test():
    return 'OK'


@app.route('/v1/upload', methods=['POST'])
def upload_file():
    """
    Загрузка файла
    """
    result, code = uploader.save_file()
    if code == 400:
        return result, code

    file_name, file_path = result  # type: ignore
    file_size = os.path.getsize(file_path)
    handler.handle_upload_geojson(file_path, file_name)
    return jsonify({"message": f"File '{file_name}' uploaded successfully",
                    "size": f'{file_size / 1024 / 1024:.1f} Mb',
                    "key": file_name})


@app.route('/v1/<string:id>/<int:z>/<int:x>/<int:y>', methods=['GET'])
def get_tile(id, z, x, y):
    """
    Получить тайл
    """
    o_f = ''
    try:
        o_f = handler.save_tile(id, z, x, y)
    except AssertionError:
        return abort(404, description="Id not found")

    file_path = construct_file_path(o_f, z, x, y)

    if file_exists(file_path):
        return send_and_remove_file(file_path, o_f)

    abort(404, description="Tile not found")


def construct_file_path(o_f, z, x, y):
    return os.path.join(o_f, str(z), str(x), f'{y}.png')


def file_exists(file_path):
    return os.path.exists(file_path)


def send_and_remove_file(file_path, o_f):
    response = send_file(file_path)
    shutil.rmtree(o_f)
    return response


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
