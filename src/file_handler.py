"""
File Handler module
"""
import os
import re
from uuid import uuid4

from osgeo import gdal
from osgeo_utils.gdal2tiles import GlobalMercator
from osgeo_utils.gdal2tiles import main as gdal2tiles

from src.file_uploader import ensure_folder_exists


class FileHandler:
    """
    Обработчик файлов geojson для создания тайла
    """

    def __init__(
        self, handle_folder="../handle", out_folder="../out", rgb=(75, 75, 100)
    ):
        self.handle_folder = handle_folder
        self.out_folder = out_folder
        self.rgb = rgb
        ensure_folder_exists(self.handle_folder)
        ensure_folder_exists(self.out_folder)
        self.gm = GlobalMercator()

    def handle_upload_geojson(self, input_path, file_name):
        """
        Загрузка файла и обработка
        """
        h_f = self.get_handle_dir(file_name)
        ensure_folder_exists(h_f)
        file_c, color_dict = self.pre_handle_geojson(input_path)
        color_table = self.create_color_table(color_dict)
        self.save_color_table(color_table, h_f)
        self.reprod(file_c, h_f)
        os.remove(file_c.name)

    def save_color_table(self, color_table, h_f):
        '''
        Сохранение таблицы цветов
        '''
        file = os.path.join(h_f, 'color_table')
        with open(file, 'w+', encoding='utf-8') as f:
            f.write(color_table)
            return f

    def pre_handle_geojson(self, input_file):
        """
        Предобработка GeoJSON
        """
        color_dict = self.get_color_dict(input_file)
        return self.add_color_numbers_to_file(input_file, color_dict), color_dict

    def get_handle_dir(self, file_name):
        """
        Директория для обработки
        """
        return os.path.join(self.handle_folder, file_name)

    def get_color_dict(self, filename):
        """
        Получение словаря цветов
        Читать файл и находить паттерн типа "color":"#BDBDBD"
        Складывать в словарь с порядковым значением
        """
        color_dict = {}
        with open(filename, 'r', encoding='utf-8') as file:
            for line in file:
                match = re.findall(r'color":"#[A-Za-z0-9]+"', line)
                if match:
                    colors = {m.split('":"')[1][:-1] for m in match}
                    for color in colors:
                        if color not in color_dict:
                            color_dict[color] = len(color_dict)
        return color_dict

    def add_color_numbers_to_file(self, filename, color_dict: dict):
        """
        Добавление наименований цветов в файл, значения из словаря
        """
        content = ''
        with open(filename, 'r', encoding='utf-8') as file:
            content = file.read()
        for e in color_dict.items():
            content = content.replace(
                f'"color":"{e[0]}"', f'"color":"{e[0]}", "c":{e[1]}')
        with open(filename.replace('.json', '_c.json'), 'w+', encoding='utf-8') as file:
            file.write(content)
            return file

    def reprod(self, input_file, handle_folder):
        """
        трансформация файла в data_source
        """
        reprods = os.path.join(handle_folder, "epsg3857.geojson")
        input_filename = input_file.name
        gdal.VectorTranslate(reprods, input_filename,
                             dstSRS="epsg:3857", reproject=True)

    def save_tile(self, id_, z, x, y):
        """
        Сохранение тайла
        """
        session_name = str(uuid4())
        h_f = self.get_handle_dir(id_)
        if not os.path.exists(h_f):
            raise AssertionError("file not exists")

        reprods = os.path.join(h_f, "epsg3857.geojson")

        bounds = self.get_bounds(x, y, z)

        o_f = os.path.join(self.out_folder, id_, session_name)
        ensure_folder_exists(o_f)
        raster = self.rasterize(reprods, z, bounds, session_name)
        # Достаем стили
        vrt = self.get_vrt(raster, session_name)
        color_table=  self.get_color_table(h_f)
        # Добавляем таблицу цветов в стили
        vrt = self.add_colors_to_vrt(vrt, color_table)
        # Красим растр
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
        '''
        Генерируем растер с цветами из виртуального растра
        '''
        path = os.path.dirname(vrt)
        raster_c = os.path.join(path, f"{session_name}_c.tif")
        gdal.Translate(raster_c, vrt)
        return raster_c

    def get_vrt(self, raster, session_name):
        '''
        Создаем файл виртуальный растр
        '''
        path = os.path.dirname(raster)
        vrt = os.path.join(path, f"{session_name}.vrt")
        gdal.Translate(vrt, raster, format='VRT')
        return vrt

    def add_colors_to_vrt(self, vrt, colors):
        '''
        Перезаписываем файл с добавлением таблицы
        '''
        content = ''
        with open(vrt, 'r', encoding='utf-8') as f:
            content = f.read()
        content = re.sub(r'<ColorInterp>.*</ColorInterp>', '<ColorInterp>Palette</ColorInterp>', content)
        content = content.replace('</ColorInterp>', '</ColorInterp>' + colors)
        with open(vrt, 'w') as f:
           f.write(content) 
        return vrt

    def create_color_table(self, color_dict):
        colors = sorted(color_dict.items(), key=lambda x: x[1])
        colors = [c[0] for c in colors]
        colors = [self.hex_to_rgba(c) for c in colors]
        colors = [f'<Entry c1="{c[0]}" c2="{c[1]}" c3="{c[2]}" c4="{c[3]}"/>' for c in colors]  # type: ignore
        colors = '<ColorTable>' + ''.join(colors) + '</ColorTable>'
        return colors

    def hex_to_rgba(self, hex_code):
        red = int(hex_code[1:3], 16);
        green = int(hex_code[3:5], 16);
        blue = int(hex_code[5:7], 16);
        return (red, green, blue, 255)


    def get_bounds(self, x, y, z):
        '''
        Рассчет границ растра
        '''
        x_g, y_g = self.gm.GoogleTile(x, y, z)
        return self.gm.TileBounds(x_g, y_g, z)


    def rasterize(self, reprods, zoom, bounds, session_name):
        '''
        Растеризация
        '''
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

