"""
File: file_handler.py
Description: 
    Модуль для работы с географическими данными и файлами
    Этот модуль предоставляет утилиты для работы с географическими данными,
    включая загрузку и преобразование изображений.
    В нем используются библиотеки `osgeo` для работы с GDAL и другие стандартные библиотеки Python.
"""
import json
import os
import re
from uuid import uuid4

from osgeo import gdal
from osgeo_utils.gdal2tiles import GlobalMercator
from osgeo_utils.gdal2tiles import main as gdal2tiles

from src.common import get_basename
from src.file_uploader import ensure_folder_exists


def save_color_table(color_table, h_f):
    """
    Сохраняет таблицу цветов в указанный файл.
    :args:
        color_table (str): Строка, представляющая таблицу цветов.
        h_f (str): Путь к директории, в которую будет сохранен файл.
    :return:
        file: Объект файла, который был записан.
    """
    file = os.path.join(h_f, 'color_table')
    with open(file, 'w', encoding='utf-8') as f:
        f.write(color_table)
        return f


def add_color_numbers_to_file(filename, color_dict: dict,
                              black_color='#000000'):
    """
    Добавляет порядковые номера цветов в файл GeoJSON.

    Эта функция читает файл GeoJSON, извлекает цвета из свойств каждого объекта
    и добавляет к ним порядковые номера на основе предоставленного словаря цветов.
    Если цвет не найден в словаре, используется черный цвет по умолчанию.

    :param filename: Путь к файлу GeoJSON, который нужно обработать.
    :param color_dict: Словарь, где ключи - это цветовые коды в формате HEX,
                       а значения - их порядковые номера.
    :param black_color: Цвет по умолчанию, который будет использоваться, если
                        цвет не найден в словаре (по умолчанию '#000000').
    :return: Файл, в который записан обновленный объект JSON с добавленными
             порядковыми номерами цветов.
    """
    with open(filename, 'r', encoding='utf-8') as file:
        content = file.read()

    json_object = json.loads(content)

    for feature in json_object['features']:
        color = feature['properties'].get('color')
        feature['properties']['c'] = color_dict.get(color, black_color)

    with open(filename.replace('.json', '_c.json'), 'w+',
              encoding='utf-8') as file:
        json.dump(json_object, file, ensure_ascii=False, indent=4)

    return file


def reprod(input_file, handle_folder):
    """
    Функция для преобразования векторных данных из исходного пространства координат в EPSG:3857.
    :args:
    input_file (file): Объект файла с входными векторными данными.
    handle_folder (str): Путь к папке, где будет сохранён результат преобразования.
    """
    reprods = os.path.join(handle_folder, "epsg3857.geojson")
    input_filename = input_file.name
    gdal.VectorTranslate(reprods, input_filename,
                         dstSRS="epsg:3857", reproject=True)


def get_color_dict(filename):
    """
    Читает файл и извлекает уникальные цвета, представленные в формате HEX.

    :args:
        filename (str): Имя файла, содержащего данные, где упоминаются цвета.

    :return:
        dict: Словарь с уникальными цветами в качестве ключей
        и порядковыми номерами в качестве значений.

    :description:
        Функция открывает указанный файл и читает его построчно. 
        Для каждой строки использует регулярное выражение для поиска фрагментов,
        содержащих цвета в формате HEX.
        Если найдены уникальные цвета, они добавляются в словарь color_dict
        с соответствующими порядковыми номерами.
    """
    color_dict = {'#000000': 0}
    with open(filename, 'r', encoding='utf-8') as file:
        for line in file:
            match = re.findall(r'color":"#[A-Za-z0-9]+"', line)
            if match:
                colors = {m.split('":"')[1][:-1] for m in match}
                for color in colors:
                    if color not in color_dict:
                        color_dict[color] = len(color_dict)
    return color_dict


def hex_to_rgba(hex_code):
    """
    Преобразует шестнадцатеричный цвет в RGBA-значение.
    :args:
        hex_code (str): Шестнадцатеричный код цвета, например, "#RRGGBB".
    :return:
        tuple: Кортеж из четырех элементов:
        красный, зеленый, синий и альфа-канал (значение от 0 до 255).
    Описание:
    Функция принимает шестнадцатеричный цветовой код и преобразует его в RGBA-значение.
    Шестнадцатеричный код должен быть в формате "#RRGGBB",
    где RR, GG и BB являются значениями красной, зеленой и синей компонент соответственно.
    Функция извлекает каждый цветовой компонент из шестнадцатеричного кода,
    преобразует его в десятичное число и возвращает кортеж (красный, зеленый, синий, 255).
    """
    red = int(hex_code[1:3], 16)
    green = int(hex_code[3:5], 16)
    blue = int(hex_code[5:7], 16)
    return red, green, blue, 255


def create_color_table(color_dict):
    """
    Создает таблицу цветов на основе предоставленного словаря.

    :param:
        color_dict (dict): Словарь, где ключи - это цветовые коды в формате HEX,
                           а значения - их порядковые номера.

    :return:
        str: Строка, представляющая таблицу цветов в формате XML,
             содержащая элементы <Entry> для каждого цвета.
    """
    colors = sorted(color_dict.items(), key=lambda x: x[1])
    colors = [c[0] for c in colors]
    colors = [hex_to_rgba(c) for c in colors]
    colors = [f'<Entry c1="{c[0]}" c2="{c[1]}" c3="{
        c[2]}" c4="{c[3]}"/>' for c in colors]
    colors = '<ColorTable>' + ''.join(colors) + '</ColorTable>'
    return colors


def get_colored_raster(vrt, out_folder):
    """
    Создает цветной растр из входного файла VRT и сохраняет его в указанную папку.
    :args:
        self (объект): Объект класса, содержащий данную функцию.
        vrt (str): Путь к файлу VRT, из которого будет создан растр.
        out_folder (str): Папка, в которую будет сохранен сгенерированный растр.
    :return:
        str: Путь к сохраненному цветному растру.
    """
    raster_c = os.path.join(out_folder, 'raster_c.tif')
    gdal.Translate(raster_c, vrt)
    return raster_c


def get_vrt(raster, out_folder):
    """
    Создает VRT-файл на основе входного растрового файла.
    :args:
        raster (str): Путь к входному растровому файлу.
        out_folder (str): Папка, в которую будет сохранен VRT-файл.
    :return:
        str: Путь к созданному VRT-файлу.
    """
    vrt = os.path.join(out_folder, 'vrt.vrt')
    gdal.Translate(vrt, raster, format='VRT')
    return vrt


def add_colors_to_vrt(vrt, colors):
    """
    Добавляет заданные цвета в элемент <ColorInterp> в файле VRT (Vector Tile Reference).
    :args:
        vrt (str): Путь к файлу VRT.
        colors (str): Строка с цветами, которые нужно добавить.
    :return:
        str: Путь к измененному файлу VRT.
    """
    content = ''
    with open(vrt, 'r', encoding='utf-8') as f:
        content = f.read()
    content = re.sub(r'<ColorInterp>.*</ColorInterp>',
                     '<ColorInterp>Palette</ColorInterp>', content)
    content = content.replace('</ColorInterp>', '</ColorInterp>' + colors)
    with open(vrt, 'w', encoding='utf-8') as f:
        f.write(content)
    return vrt



class FileHandler:

    def __init__(
            self, handle_folder="../handle", out_folder="../out",
            rgb=(75, 75, 100)
    ):
        self.handle_folder = handle_folder
        self.out_folder = out_folder
        self.rgb = rgb
        self.gm = GlobalMercator()
        ensure_folder_exists(self.handle_folder)
        ensure_folder_exists(self.out_folder)

    def handle_upload_geojson(self, input_file):
        h_f = self.get_handle_dir(input_file)
        ensure_folder_exists(h_f)
        color_dict = get_color_dict(input_file)
        file_c = add_color_numbers_to_file(input_file, color_dict)
        color_table = create_color_table(color_dict)
        save_color_table(color_table, h_f)
        reprod(file_c, h_f)
        os.remove(file_c.name)

    def get_handle_dir(self, file):
        return os.path.join(self.handle_folder, get_basename(file))

    def save_tile(self, layer_id, **kwargs):
        z = kwargs.get('z')
        x = kwargs.get('x')
        y = kwargs.get('y')
        za = kwargs.get('za')
        blck = kwargs.get('blck')

        session_name = str(uuid4())
        h_f = self.get_handle_dir(layer_id)
        if not os.path.exists(h_f):
            raise AssertionError("file not exists")

        reprods = os.path.join(h_f, "epsg3857.geojson")

        bounds = self.get_bounds(x, y, z)

        out_folder = os.path.join(self.out_folder, layer_id, session_name)
        ensure_folder_exists(out_folder)

        raster = self.rasterize(reprods, z, bounds, out_folder, za, blck)

        if blck:
            srs = raster
        else:
            vrt = get_vrt(raster, out_folder)
            color_table = self.get_color_table(h_f)
            vrt = add_colors_to_vrt(vrt, color_table)
            raster_c = get_colored_raster(vrt, out_folder)
            srs = vrt.replace('.vrt', '_1.vrt')
            gdal.Translate(srs, raster_c, format='VRT', rgbExpand='rgba')

        gdal2tiles(
            [
                "this arg is required but ignored",
                srs,
                out_folder,
                "-z",
                f"{z}",
                "-q",
                "-w",
                "none",
                "--xyz",
                "--tilesize=512",
            ]
        )

        return out_folder

    def get_bounds(self, x, y, z):
        x_g, y_g = self.gm.GoogleTile(x, y, z)
        return self.gm.TileBounds(x_g, y_g, z)

    def rasterize(self, reprods, zoom, bounds, out_folder, za, blck):
        resolution = self.gm.Resolution(zoom + int(za))
        buffds = os.path.join(out_folder, 'raster.tif')
        if blck:
            gdal.Rasterize(
                buffds,
                reprods,
                noData=0,
                xRes=resolution,
                yRes=resolution,
                outputBounds=bounds,
                outputType=gdal.GDT_Byte,
                burnValues=self.rgb,
                creationOptions={"COMPRESS": "DEFLATE"}
            )
        else:
            gdal.Rasterize(
                buffds,
                reprods,
                noData=0,
                xRes=resolution,
                yRes=resolution,
                outputBounds=bounds,
                outputType=gdal.GDT_Byte,
                attribute='c',
                creationOptions={"COMPRESS": "DEFLATE"}
            )
        return buffds

    def get_color_table(self, h_f):
        file = os.path.join(h_f, 'color_table')
        with open(file, 'r', encoding='utf-8') as f:
            return f.read()
