import os

from flask import Flask, jsonify, send_file, abort

from file_handler import FileHandler
from file_uploader import FileUploader

app = Flask(__name__)

uploader = FileUploader()
handler = FileHandler()


# @app.route('/v1/upload', methods=['POST'])
# def upload_file():
#     result, code = uploader.save_file()
#     if code == 400:
#         return result, code
#     else:
#         file_name, file_path = result
#         file_size = os.path.getsize(file_path)
#
#         uuid_ = uuid.uuid4()
#
#         handler.handle_to_tiles(file_path, file_name,
#                                 uuid_)
#
#         return jsonify({"message": f"File '{file_name}' uploaded successfully",
#                         "size": f'{file_size / 1024 / 1024:.1f} Mb',
#                         "key": uuid_})

@app.route('/v1/upload', methods=['POST'])
def upload_file():
    result, code = uploader.save_file()
    file_name, file_path = result
    handler.reprod(file_path, file_name)
    if code == 400:
        return result, code
    else:
        file_size = os.path.getsize(file_path)
        return jsonify({"message": f"File '{file_name}' uploaded successfully",
                        "size": f'{file_size / 1024 / 1024:.1f} Mb',
                        "key": file_name})


@app.route('/v1/<string:id>/<int:z>/<int:x>/<int:y>', methods=['GET'])
def get_tile(id, z, x, y):
    handler.save_tile(id, z, x, y)
    file_path = os.path.join('out', id, str(z), str(x), f'{y}.png')

    if os.path.exists(file_path):
        return send_file(file_path)
    else:
        abort(404, description="Tile not found")


if __name__ == '__main__':
    app.run(debug=True)
