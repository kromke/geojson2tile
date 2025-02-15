import json
import os
import re
from uuid import uuid4

from osgeo import gdal
from osgeo_utils.gdal2tiles import GlobalMercator
from osgeo_utils.gdal2tiles import main as gdal2tiles

from src.file_uploader import ensure_folder_exists


def get_basename(file):
    return os.path.basename(file).split(".")[0]


def save_color_table(color_table, h_f):
    file = os.path.join(h_f, 'color_table')
    with open(file, 'w+', encoding='utf-8') as f:
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
    reprods = os.path.join(handle_folder, "epsg3857.geojson")
    input_filename = input_file.name
    gdal.VectorTranslate(reprods, input_filename,
                         dstSRS="epsg:3857", reproject=True)


def get_color_dict(filename):
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


class FileHandler:

    def __init__(
            self, handle_folder="../handle", out_folder="../out",
            rgb=(75, 75, 100)
    ):
        self.handle_folder = handle_folder
        self.out_folder = out_folder
        self.rgb = rgb
        ensure_folder_exists(self.handle_folder)
        ensure_folder_exists(self.out_folder)
        self.gm = GlobalMercator()

    def handle_upload_geojson(self, input_file):
        h_f = self.get_handle_dir(input_file)
        ensure_folder_exists(h_f)
        color_dict = get_color_dict(input_file)
        file_c = add_color_numbers_to_file(input_file, color_dict)
        color_table = self.create_color_table(color_dict)
        save_color_table(color_table, h_f)
        reprod(file_c, h_f)
        os.remove(file_c.name)

    def get_handle_dir(self, file):
        return os.path.join(self.handle_folder, get_basename(file))

    def save_tile(self, id_, z, x, y):
        session_name = str(uuid4())
        h_f = self.get_handle_dir(id_)
        if not os.path.exists(h_f):
            raise AssertionError("file not exists")

        reprods = os.path.join(h_f, "epsg3857.geojson")

        bounds = self.get_bounds(x, y, z)

        o_f = os.path.join(self.out_folder, id_, session_name)
        ensure_folder_exists(o_f)
        raster = self.rasterize(reprods, z, bounds, session_name)
        vrt = self.get_vrt(raster, session_name)
        color_table = self.get_color_table(h_f)
        vrt = self.add_colors_to_vrt(vrt, color_table)
        raster_c = self.get_colored_raster(vrt, session_name)
        vrt_1 = vrt.replace('.vrt', '_1.vrt')
        gdal.Translate(vrt_1, raster_c, format='VRT', rgbExpand='rgba')

        gdal2tiles(
            [
                "this arg is required but ignored",
                vrt_1,
                o_f,
                "-z",
                f"{z}",
                "-q",
                "-w",
                "none",
                "--xyz",
                "--tilesize=512",
            ]
        )

        os.remove(raster)
        os.remove(vrt)
        os.remove(raster_c)
        os.remove(vrt_1)
        return o_f

    def get_colored_raster(self, vrt, session_name):
        path = os.path.dirname(vrt)
        raster_c = os.path.join(path, f"{session_name}_c.tif")
        gdal.Translate(raster_c, vrt)
        return raster_c

    def get_vrt(self, raster, session_name):
        path = os.path.dirname(raster)
        vrt = os.path.join(path, f"{session_name}.vrt")
        gdal.Translate(vrt, raster, format='VRT')
        return vrt

    def add_colors_to_vrt(self, vrt, colors):
        content = ''
        with open(vrt, 'r', encoding='utf-8') as f:
            content = f.read()
        content = re.sub(r'<ColorInterp>.*</ColorInterp>',
                         '<ColorInterp>Palette</ColorInterp>', content)
        content = content.replace('</ColorInterp>', '</ColorInterp>' + colors)
        with open(vrt, 'w') as f:
            f.write(content)
        return vrt

    def create_color_table(self, color_dict):
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
        colors = [self.hex_to_rgba(c) for c in colors]
        colors = [f'<Entry c1="{c[0]}" c2="{c[1]}" c3="{c[2]}" c4="{c[3]}"/>'
                  for c in colors]  # type: ignore
        colors = '<ColorTable>' + ''.join(colors) + '</ColorTable>'
        return colors

    def hex_to_rgba(self, hex_code):
        red = int(hex_code[1:3], 16)
        green = int(hex_code[3:5], 16)
        blue = int(hex_code[5:7], 16)
        return red, green, blue, 255

    def get_bounds(self, x, y, z):
        x_g, y_g = self.gm.GoogleTile(x, y, z)
        return self.gm.TileBounds(x_g, y_g, z)

    def rasterize(self, reprods, zoom, bounds, session_name):
        resolution = self.gm.Resolution(zoom + 2)
        path = os.path.dirname(reprods)
        buffds = os.path.join(path, f"{session_name}.tif")
        gdal.Rasterize(
            buffds,
            reprods,
            noData=0,
            xRes=resolution,
            yRes=resolution,
            outputBounds=bounds,
            outputType=gdal.GDT_Byte,
            attribute='c'
        )
        return buffds

    def get_color_table(self, h_f):
        file = os.path.join(h_f, 'color_table')
        with open(file, 'r', encoding='utf-8') as f:
            return f.read()
