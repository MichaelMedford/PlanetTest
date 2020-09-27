import os
import rasterio
import json
import xml.etree.ElementTree as ET
import matplotlib.pyplot as plt


class Scene(object):
    def __init__(self, filename):
        self.filename_base = self.parse_filename_base(filename)
        self.filename_scene = f'{self.filename_base}_3B_AnalyticMS_clip.tif'
        self.filename_metadata_xml = f'{self.filename_base}_3B_' \
                                     f'AnalyticMS_metadata_clip.xml'
        self.filename_metadata_json = f'{self.filename_base}_metadata.json'
        self.filename_udm2 = f'{self.filename_base}_3B_udm2_clip.tif'

        self.check_for_files()

        self.scene_bands = ['blue', 'green', 'red', 'nir']
        self.udm2_bands = ['clear', 'snow', 'shadow', 'light_haze',
                           'heavy_haze', 'cloud', 'confidence', 'unusable']
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
                rasters[band] = f.read(raster_idx)
        return rasters

    def load_scenes(self):
        return self._load_rasters(self.filename_scene,
                                  self.scene_bands, 'scenes')

    def load_udm2(self):
        return self._load_rasters(self.filename_udm2,
                                  self.udm2_bands, 'udm2')

    def load_metadata_xml(self):
        tree = ET.parse(self.filename_metadata_xml)
        return tree.getroot()

    def load_metadata_json(self):
        with open(self.filename_metadata_json) as f:
            metadata_json = json.load(f)
        return metadata_json

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
