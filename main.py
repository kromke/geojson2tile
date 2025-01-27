import os

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
    result, code = uploader.save_file()
    file_name, file_path = result
    handler.reprod(file_path, file_name)
    if code == 400:
        return result, code
    else:
        file_size = os.path.getsize(file_path)
        os.remove(file_path)
        return jsonify({"message": f"File '{file_name}' uploaded successfully",
                        "size": f'{file_size / 1024 / 1024:.1f} Mb',
                        "key": file_name})


@app.route('/v1/<string:id>/<int:z>/<int:x>/<int:y>', methods=['GET'])
def get_tile(id, z, x, y):
    handler.save_tile(id, z, x, y)
    file_path = construct_file_path(id, z, x, y)

    if file_exists(file_path):
        return send_and_remove_file(file_path)
    else:
        abort(404, description="Tile not found")


def construct_file_path(id, z, x, y):
    return os.path.join('../out', id, str(z), str(x), f'{y}.png')


def file_exists(file_path):
    return os.path.exists(file_path)


def send_and_remove_file(file_path):
    response = send_file(file_path)
    os.remove(handler.out_folder)
    return response


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
