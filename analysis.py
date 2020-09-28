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
    print('\nLoading scenes...')
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

    return scene_arr


def plot_images_and_masks(scene_arr):
    print('\nPlotting images and masks...')
    for scene in scene_arr:
        scene.plot_images()
        scene.plot_udm2()


def calculate_stack_mask(scene_arr):
    mask_arr = [s.udm2['clear'].astype(bool) for s in scene_arr]
    stack_mask = np.logical_and.reduce(mask_arr)
    return stack_mask


def calculate_ndvi_stats(scene_arr, water_mask_percentile=50):
    mask_stack = calculate_stack_mask(scene_arr)

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


def plot_ndvi_trends(scene_arr, remove_first_image=False,
                     water_mask_percentile=50):
    ndvi_stats = calculate_ndvi_stats(scene_arr,
                                      water_mask_percentile=water_mask_percentile)
    acquired_arr, ndvi_med_arr, ndvi_std_arr = ndvi_stats

    ndvi_med_arr = np.array(ndvi_med_arr)
    delta_days_arr = generate_delta_days(acquired_arr)
    ndvi_rate_of_change = (ndvi_med_arr[1:] - ndvi_med_arr[
                                              :-1]) / delta_days_arr
    fig, ax = plt.subplots(2, 1, figsize=(8, 6))
    fig.suptitle(f'Presence of Green Vegetation | '
                 f'{water_mask_percentile} Percentile Water Mask', fontsize=14)
    ax[0].errorbar(acquired_arr, ndvi_med_arr, yerr=ndvi_std_arr, lw=5)
    ax[0].set_ylabel('NDVI')
    ax[0].set_ylim(.4, .9)
    ax[1].plot(acquired_arr[:-1], ndvi_rate_of_change, marker='s',
               ms=10, lw=5)
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


def plot_water_mask(scene_arr):
    ndvi_stats = calculate_ndvi_stats(scene_arr, water_mask_percentile=100)
    acquired_arr, ndvi_med_arr_raw, ndvi_std_arr_raw = ndvi_stats
    ndvi_stats = calculate_ndvi_stats(scene_arr, water_mask_percentile=50)
    _, ndvi_med_arr_clipped, ndvi_std_arr_clipped = ndvi_stats

    fig, ax = plt.subplots(figsize=(8, 6))
    fig.suptitle('Presence of Green Vegetation')
    ax.errorbar(acquired_arr, ndvi_med_arr_raw, yerr=ndvi_std_arr_raw,
                color='g', label='No Water Mask', lw=5)
    ax.errorbar(acquired_arr, ndvi_med_arr_clipped, yerr=ndvi_std_arr_clipped,
                color='b', label='50 Percentile Water Mask', lw=5)
    ax.set_xlabel('Observation Date')
    ax.set_ylabel('NDVI')
    ax.format_xdata = mdates.DateFormatter('%Y-%m-%d')
    ax.set_ylim(.4, .9)
    for item in ([ax.title, ax.xaxis.label, ax.yaxis.label] +
                 ax.get_xticklabels() + ax.get_yticklabels()):
        item.set_fontsize(14)
    for label in ax.get_xticklabels():
        label.set_rotation(20)
    ax.legend(loc=9, fontsize=14)
    fig.tight_layout()
    fig.subplots_adjust(top=.9)


    fname = 'figures/water_mask.png'
    fig.savefig(fname, dpi=75, bbox_inches='tight', pad_inches=0.05)
    print(f'{fname} saved')


def analyze_scenes(remove_first_image, water_mask_percentile,
                   skip_plot_image_masks):
    scene_arr = load_scenes(remove_first_image=remove_first_image)
    if not skip_plot_image_masks:
        plot_images_and_masks(scene_arr)

    print('\nPlotting analysis figures')
    plot_water_mask(scene_arr)
    plot_ndvi_trends(scene_arr, remove_first_image=remove_first_image,
                     water_mask_percentile=water_mask_percentile)


def main():
    parser = argparse.ArgumentParser(description='Analyze scenes for '
                                                 'vegetation trends.',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    help_str = 'This analysis script generates plots of the images and ' \
               'masks for each scene. This flag skips that output.'
    parser.add_argument('--skip-plot-images-masks',
                        action='store_false', help=help_str)
    parser.set_defaults(skip_plot_image_masks=True)

    help_str = 'A stack mask is constructed by finding the "clear" pixels ' \
               'that all scenes in the set of imaages have in common. ' \
               'The first analysis has 15 less rows than the remaining ' \
               'images, despite being clipped to the same extent. ' \
               'Activating this flag removes the first image from the ' \
               'analysis. If not selected, the remaining scenes are ' \
               'clipped by 15 rows to generate a stack mask.'
    parser.add_argument('--remove-first-image',
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

    analyze_scenes(args.remove_first_image, args.water_mask_percentile,
                   args.skip_plot_image_masks)


if __name__ == '__main__':
    main()
