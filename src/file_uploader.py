import os

from flask import request, jsonify


def get_file_from_request():
    return request.files.get('file')


def get_filename(file):
    filename = file.filename.split(".")[0]
    return filename if filename else None


def ensure_folder_exists(folder):
    if not os.path.exists(folder):
        os.makedirs(folder)


def create_error_response(self, message, status_code):
    return jsonify({"error": message}), status_code


class FileUploader:
    def __init__(self, upload_folder='../uploads'):
        self.upload_folder = upload_folder
        ensure_folder_exists(self.upload_folder)

    def save_file(self):
        file = get_file_from_request()
        if file is None:
            return create_error_response("No file part", 400)

        filename = get_filename(file)
        if filename is None:
            return create_error_response("No selected file", 400)

        file_path = self.save_file_to_disk(file, filename)
        return [filename, file_path], 200

    def save_file_to_disk(self, file, filename):
        file_path = os.path.join(self.upload_folder, filename)
        file.save(file_path)
        return file_path
