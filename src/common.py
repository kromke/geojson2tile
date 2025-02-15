import os

# from flask import jsonify


# def get_filename(file):
#     """
#
#     :param file:
#     :return:
#     """
#     return file.filename.split(".")[0]


def ensure_folder_exists(folder):
    if not os.path.exists(folder):
        os.makedirs(folder)


# def create_error_response(message, status_code):
#     return jsonify({"error": message}), status_code


