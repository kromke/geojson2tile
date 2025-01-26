from flask import Flask, request, jsonify
import os


class FileUploader:
    def __init__(self, upload_folder='uploads'):
        self.upload_folder = upload_folder
        if not os.path.exists(self.upload_folder):
            os.makedirs(self.upload_folder)

    def save_file(self):
        if 'file' not in request.files:
            return jsonify({"error": "No file part"}), 400

        file = request.files['file']

        filename = file.filename.split(".")[0]
        if filename == '':
            return jsonify({"error": "No selected file"}), 400

        # Save the file to disk
        file_path = os.path.join(self.upload_folder, filename)
        file.save(file_path)

        return [filename, file_path], 200

