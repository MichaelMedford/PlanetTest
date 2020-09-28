import os
import rasterio
import json
from xml.dom import minidom
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime


class Scene(object):
    def __init__(self, filename):
        # parse filenames
        self.filename_base = self.parse_filename_base(filename)
        self.filename_scene = f'{self.filename_base}_3B_AnalyticMS_clip.tif'
        self.filename_metadata_xml = f'{self.filename_base}_3B_' \
                                     f'AnalyticMS_metadata_clip.xml'
        self.filename_metadata_json = f'{self.filename_base}_metadata.json'
        self.filename_udm2 = f'{self.filename_base}_3B_udm2_clip.tif'

        # check for files
        self.check_for_files()

        # load files into memory
        self.scene_bands = {'blue': 1, 'green': 2, 'red': 3, 'nir': 4}
        self.udm2_bands = {'clear': 1, 'snow': 2, 'shadow': 3,
                           'light_haze': 4, 'heavy_haze': 5, 'cloud': 6,
                           'confidence': 7, 'unusable': 8}
        self.scenes = self.load_scenes()
        self.udm2 = self.load_udm2()
        self.metadata_xml = self.load_metadata_xml()
        self.metadata_json = self.load_metadata_json()

    def parse_filename_base(self, filename):
        return filename.replace('_3B_AnalyticMS_clip.tif', '')

    def check_for_files(self):
        for filename in [self.filename_scene, self.filename_udm2,
                         self.filename_metadata_xml,
                         self.filename_metadata_json]:
            if not os.path.exists(filename):
                raise FileNotFoundError(f'{filename} missing')

    def _load_rasters(self, filename, bands, raster_type):
        print(f'{self.filename_base}: loading {raster_type}')
        rasters = {}
        for raster_idx, band in enumerate(bands, 1):
            with rasterio.open(filename) as f:
                rasters[band] = f.read(raster_idx).astype(float)
        return rasters

    def load_scenes(self):
        return self._load_rasters(self.filename_scene,
                                  self.scene_bands, 'scenes')

    def load_udm2(self):
        return self._load_rasters(self.filename_udm2,
                                  self.udm2_bands, 'udm2')

    def load_metadata_xml(self):
        return minidom.parse(self.filename_metadata_xml)

    def load_metadata_json(self):
        with open(self.filename_metadata_json) as f:
            metadata_json = json.load(f)
        return metadata_json

    @property
    def acquired(self):
        return datetime.strptime(self.metadata_json['properties']['acquired'],
                                 '%Y-%m-%dT%H:%M:%S.%fz')

    @property
    def acquired_label(self):
        return self.acquired.strftime('%Y-%m-%d')

    def _load_toa_reflectance_coeff(self, band_idx):
        nodes = self.metadata_xml.getElementsByTagName("ps:bandSpecificMetadata")
        coeff = nodes[band_idx].getElementsByTagName("ps:reflectanceCoefficient")[0].firstChild.data
        return float(coeff)

    def _load_scene_toa_reflectance(self, scene_band):
        band = self.scenes[scene_band]
        band_idx = self.scene_bands[scene_band] - 1
        coeff = self._load_toa_reflectance_coeff(band_idx)
        return band * coeff

    def calculate_ndvi(self, convert_to_toa=True):
        np.seterr(divide='ignore', invalid='ignore')
        if convert_to_toa:
            nir = self._load_scene_toa_reflectance('nir')
            red = self._load_scene_toa_reflectance('red')
        else:
            nir = self.scenes['nir']
            red = self.scenes['red']
        return (nir - red) / (nir + red)

    def _plot_bands(self, fig, ax, bands, labels, ext):
        fig.suptitle(self.filename_base + f' {ext}')
        ax = ax.flatten()
        for i, band in enumerate(labels):
            ax[i].set_title(band, fontsize=12)
            ax[i].imshow(bands[band], cmap='viridis')
        fig.tight_layout()
        fig.subplots_adjust(top=.95)
        fname = self.filename_base + f'_{ext}.png'
        fig.savefig(fname, dpi=75)
        print(f'{fname} saved')
        plt.close(fig)

    def plot_scenes(self):
        fig, ax = plt.subplots(2, 2, figsize=(8, 8))
        self._plot_bands(fig, ax, self.scenes, self.scene_bands, 'scenes')

    def plot_udm2(self):
        fig, ax = plt.subplots(4, 2, figsize=(8, 12))
        self._plot_bands(fig, ax, self.udm2, self.udm2_bands, 'udm2')

