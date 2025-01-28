import os

from osgeo import gdal
from osgeo_utils.gdal2tiles import GlobalMercator
from osgeo_utils.gdal2tiles import main as gdal2tiles

from src.file_uploader import ensure_folder_exists


class FileHandler:
    def __init__(self, handle_folder='../handle', out_folder='../out',
                 rgb=(75, 75, 100)):
        self.handle_folder = handle_folder
        self.out_folder = out_folder
        self.rgb = rgb
        ensure_folder_exists(self.handle_folder)
        ensure_folder_exists(self.out_folder)

    def reprod(self, input_file, file_name):
        h_f = os.path.join(self.handle_folder, file_name)
        ensure_folder_exists(h_f)
        reprods = os.path.join(h_f, 'epsg3857.geojson')
        gdal.VectorTranslate(reprods, input_file, dstSRS="epsg:3857",
                             reproject=True)


    def save_tile(self, id_, z, x, y, session_name):
        h_f = os.path.join(self.handle_folder, id_)
        if not os.path.exists(h_f):
            raise AssertionError("file not exists")

        reprods = os.path.join(h_f, 'epsg3857.geojson')
        gm = GlobalMercator()

        o_f = os.path.join(self.out_folder, id_, session_name)
        ensure_folder_exists(o_f)

        buffds = os.path.join(o_f, f'{session_name}.tif')
        resolution = gm.Resolution(z)
        bounds = gm.TileBounds(x, y, z)

        gdal.Rasterize(
            buffds,
            reprods,
            noData=0,
            xRes=resolution,
            yRes=resolution,
            outputBounds=bounds,
            burnValues=self.rgb,
            outputType=gdal.GDT_Byte,
            creationOptions={"compress": "deflate"}
        )
        gdal2tiles(
            ["this arg is required but ignored", buffds, o_f, "-z",
             f"{z}", "-e", "-q", "-w", "none", "-x"])

        os.remove(buffds)
        return o_f

