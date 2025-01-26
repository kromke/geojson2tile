import os
from concurrent.futures import ProcessPoolExecutor

from osgeo import gdal
from osgeo_utils.gdal2tiles import GlobalMercator, main as gdal2tiles


class FileHandler:
    def __init__(self, handle_folder='handle', out_folder='out',
                 zoom_levels=[16, 16], rgb=(75, 75, 100)):
        self.handle_folder = handle_folder
        self.out_folder = out_folder
        self.zoom_levels = range(zoom_levels[0], zoom_levels[1] + 1)
        self.rgb = rgb
        if not os.path.exists(self.handle_folder):
            os.makedirs(self.handle_folder)
        if not os.path.exists(self.out_folder):
            os.makedirs(self.out_folder)

    def handle_to_tiles(self, input_file, file_name, uuid_):
        h_f = f'{self.handle_folder}/{file_name}'
        if not os.path.exists(h_f):
            os.makedirs(h_f)
        reprods = f'{h_f}/epsg3857.geojson'
        gdal.VectorTranslate(reprods, input_file, dstSRS="epsg:3857",
                             reproject=True)
        gm = GlobalMercator()

        o_f = f'{self.out_folder}/{uuid_}'
        if not os.path.exists(o_f):
            os.makedirs(o_f)

        self.loop_rasterize_and_tiling(gm, h_f, o_f, reprods)

    def reprod(self, input_file, file_name):
        h_f = f'{self.handle_folder}/{file_name}'
        if not os.path.exists(h_f):
            os.makedirs(h_f)
        reprods = f'{h_f}/epsg3857.geojson'
        gdal.VectorTranslate(reprods, input_file, dstSRS="epsg:3857",
                             reproject=True)

    def loop_rasterize_and_tiling(self, gm, h_f, o_f, reprods):
        for zoom in self.zoom_levels:
            buffds = f'{h_f}/epsg3857buff{zoom}z.tif'
            resolution = gm.Resolution(zoom)
            self.rasterize_and_tile(buffds, reprods, resolution, o_f, zoom)

    def concurrent_rasterize_and_tiling(self, gm, h_f, o_f, reprods):
        with ProcessPoolExecutor() as executor:
            futures = []
            for zoom in self.zoom_levels:
                buffds = f'{h_f}/epsg3857buff{zoom}z.tif'
                resolution = gm.Resolution(zoom)

                # Submit the rasterization task to the thread pool
                futures.append(
                    executor.submit(self.rasterize_and_tile, buffds, reprods,
                                    resolution, o_f, zoom))

            # Wait for all futures to complete
            for future in futures:
                future.result()

    def rasterize_and_tile(self, buffds, reprods, resolution, o_f, zoom):
        gdal.Rasterize(
            buffds,
            reprods,
            noData=0,
            xRes=resolution,
            yRes=resolution,
            burnValues=self.rgb,
            outputType=gdal.GDT_Byte,
            creationOptions={"compress": "deflate"}
        )
        gdal2tiles(
            ["this arg is required but ignored", buffds, o_f, "-z",
             f"{zoom}", "--processes", "2"])

    def save_tile(self, id, z, x, y):
        h_f = f'{self.handle_folder}/{id}'
        if not os.path.exists(h_f):
            raise AssertionError("file not exists")

        reprods = f'{h_f}/epsg3857.geojson'

        gm = GlobalMercator()

        o_f = f'{self.out_folder}/{id}'
        if not os.path.exists(o_f):
            os.makedirs(o_f)

        buffds = f'{h_f}/epsg3857buff{z}.tif'

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
             f"{z}", "-e", "-q", "-w", "none"])
