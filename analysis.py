#!python

import glob
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import argparse

try:
    import seaborn as sns
    sns.set()
except ModuleNotFoundError:
    pass

from product import Scene


def load_scenes(remove_first_image=False):
    print('Loading scenes...')
    fname_arr = glob.glob('data/*AnalyticMS_clip.tif')
    fname_arr.sort()

    if remove_first_image:
        fname_arr = fname_arr[1:]

    scene_arr = []
    for i, fname in enumerate(fname_arr):
        if remove_first_image:
            scene = Scene(fname)
        else:
            if i == 0:
                scene = Scene(fname)
            else:
                scene = Scene(fname, row_clip=15)
        scene_arr.append(scene)

    print('\n')
    return scene_arr


def calculate_mask(scene_arr):
    mask_arr = [s.udm2['clear'].astype(bool) for s in scene_arr]
    mask = np.logical_and.reduce(mask_arr)
    return mask


def calculate_ndvi_stats(scene_arr, water_mask_percentile=50):
    mask_stack = calculate_mask(scene_arr)

    ndvi_med_arr = []
    ndvi_std_arr = []
    acquired_arr = []
    for scene in scene_arr:
        mask_water = scene.calculate_percentile_mask('blue',
                                                     water_mask_percentile)
        mask_scene = np.logical_and(mask_stack, mask_water)
        ndvi = scene.calculate_ndvi(convert_to_toa=True)

        ndvi_med_arr.append(np.median(ndvi[mask_scene]))
        ndvi_std_arr.append(np.std(ndvi[mask_scene]))
        acquired_arr.append(scene.acquired)

    return acquired_arr, ndvi_med_arr, ndvi_std_arr


def generate_delta_days(acquired_arr):
    delta_days_arr = []
    for i in range(len(acquired_arr) - 1):
        date_start = acquired_arr[i]
        date_end = acquired_arr[i + 1]
        delta_seconds = (date_end - date_start).total_seconds()
        delta_days = delta_seconds / (60 * 60 * 24)
        delta_days_arr.append(delta_days)
    return np.array(delta_days_arr)


def plot_iamges_and_masks(scene_arr):
    print('Plotting images and masks...')
    for scene in scene_arr:
        scene.plot_images()
        scene.plot_udm2()
    print('\n')


def plot_ndvi_trends(scene_arr, remove_first_image=False,
                     water_mask_percentile=50):
    ndvi_stats = calculate_ndvi_stats(scene_arr,
                                      water_mask_percentile=water_mask_percentile)
    acquired_arr, ndvi_med_arr, ndvi_std_arr = ndvi_stats

    ndvi_med_arr = np.array(ndvi_med_arr)
    delta_days_arr = generate_delta_days(acquired_arr)
    ndvi_rate_of_change = (ndvi_med_arr[1:] - ndvi_med_arr[
                                              :-1]) / delta_days_arr
    fig, ax = plt.subplots(2, 1, figsize=(12, 6))
    fig.suptitle('Presence of Green Vegetation')
    ax[0].errorbar(acquired_arr, ndvi_med_arr, yerr=ndvi_std_arr)
    ax[0].set_ylabel('NDVI')
    ax[0].set_ylim(.4, .9)
    ax[1].plot(acquired_arr[:-1], ndvi_rate_of_change, marker='.', ms=10)
    ax[1].set_ylabel(r'$\delta$(NDVI) / day')
    ax[1].set_ylim(-.02, .08)
    ax[1].set_xlim(ax[0].get_xlim())
    ax[1].axhline(0, color='k', alpha=.5)

    for a in ax:
        a.set_xlabel('Observation Date')
        a.format_xdata = mdates.DateFormatter('%Y-%m-%d')
        for item in ([a.title, a.xaxis.label, a.yaxis.label] +
                     a.get_xticklabels() + a.get_yticklabels()):
            item.set_fontsize(14)
        for label in a.get_xticklabels():
            label.set_rotation(20)
    fig.tight_layout()
    fig.subplots_adjust(top=.9)

    fname = 'figures/ndvi_trends'
    if remove_first_image:
        fname += '_clipped'
    fname += f'_blue{water_mask_percentile}.png'
    fig.savefig(fname, dpi=75, bbox_inches='tight', pad_inches=0.05)
    print(f'{fname} saved')


def analyze_scenes(remove_first_image, water_mask_percentile):
    scene_arr = load_scenes(remove_first_image=remove_first_image)
    plot_iamges_and_masks(scene_arr)
    plot_ndvi_trends(scene_arr, remove_first_image=remove_first_image,
                     water_mask_percentile=water_mask_percentile)


def main():
    parser = argparse.ArgumentParser(description='Analyze scenes for '
                                                 'vegetation trends.',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    help_str = 'A stack mask is constructed by finding the "clear" pixels ' \
               'that all scenes in the set of imaages have in common. ' \
               'The first analysis has 15 less rows than the remaining ' \
               'images, despite being clipped to the same extent. ' \
               'Activating this flag removes the first image from the ' \
               'analysis. If not selected, the remaining scenes are ' \
               'clipped by 15 rows to generate a stack mask.'
    parser.add_argument('--remove-first-image', dest='remove_first_image',
                        action='store_true', help=help_str)
    parser.set_defaults(remove_first_image=False)

    help_str = 'A water mask is generated for each scene to remove pixels ' \
               'without vegetation and increase the SNR of the ' \
               'vegetation measurement. This mask is generated by only ' \
               'keeping pixels with a blue value below this percentile.'
    parser.add_argument('-water-mask-percentile', type=int,
                        help=help_str)
    parser.set_defaults(remove_first_image=False,
                        water_mask_percentile=50)

    args = parser.parse_args()

    analyze_scenes(args.remove_first_image, args.water_mask_percentile)


if __name__ == '__main__':
    main()
