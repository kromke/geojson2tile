"""
File: common.py
Description: общие функции
"""
import os
import shutil

from flask import send_file


def ensure_folder_exists(folder):
    if not os.path.exists(folder):
        os.makedirs(folder)


def construct_file_path(o_f, z, x, y):
    return os.path.join(o_f, str(z), str(x), f'{y}.png')


def file_exists(file_path):
    return os.path.exists(file_path)


def send_and_remove_file(file_path, o_f):
    response = send_file(file_path)
    shutil.rmtree(o_f)
    return response
