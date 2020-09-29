#!python

"""
Measuring the rate of change from green vegetation to bare soil
in the scenes of this strip requires a measurement of vegetative health.
I have opted to use the Normalized Difference Vegetation Index, or NDVI,
to make this measurement. NDVI is an industry standard for measuring
vegetative health, leveraging the fact that vegetation absorbs light in the
optical spectrum (to process solar photons into cholorophyll) and reflects
radiation in the near-infrared. NDVI is defined as:

NDVI = (NIR - red) / (NIR + red)

Plants that are extremely green due to chlorophyll production will be
dark in red (due to absorption) and bright in NIR (due to reflection),
leading to a large NDVI. Therefore a larger NDVI indicates more green
vegatation, and a smaller NDVI indicates bare soil.

Cleaning the data is required to get a pristine sample for measurement. This
analysis script uses two masks, that are combined together for each scene:
    1. A strip mask is created by finding pixels which are similarly `clean`
       across all of the scenes in the strip. This is a conservative mask, as
       there are valuable pixels in a given scene that may  be clouded out in a
       separate scene. However this ensures that there are only good pixels in
       the final sample.
    2. Pixels that contain water cannot be either vegetation or bare soil and
       are therefore contaminants to our measurement. These pixels are masked
       by masking out pixels in each scene where the blue value is above
       a percentile threshold. This percentile is transformed into a pixel
       value for each scene and generated into a mask.

This analysis script generates plots:
    plot_ndvi_hist
        Histograms of the NDVI pixels for each scene, with and without masks
    plot_ndvi_trends
        Trends of the NDVI evolution across the scenes.
        Rate of change of the NDVI trends across the scenes.
    plot_ndvi_trends_water_mask
        Trends of the NDVI evolution across the scenes, with and without masks.
    plot_water_mask
        Images of the water mask for a single scene.
"""

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
    """
    Loads scenes into memory from disk. A later step builds a mask out of
    overlapping pixels from the scenes, requiring them to be of the same
    extent. However the first image is 15 rows short, requiring either
    (1) removing the first image from the analysis, or (2) clipping the
    remaining scenes by 15 rows. The default is to clip images
    in order to keep as many epochs as possible.

    :param bool remove_first_image: If True, remove the first image from
        the strip due to its missing rows. If false, clip the remaining
        images by 15 rows to create a match in size between all scenes.
    :returns list Scene: List of scenes
    """
    print('\nLoading scenes...')
    fname_arr = glob.glob('data/*AnalyticMS_clip.tif')
    fname_arr.sort()

    # Remove the first scene from the list (if selected)
    if remove_first_image:
        fname_arr = fname_arr[1:]

    # Load each scene into memory
    scene_arr = []
    for i, fname in enumerate(fname_arr):
        if remove_first_image:
            scene = Scene(fname)
        else:
            if i == 0:
                scene = Scene(fname)
            else:
                scene = Scene(fname, row_clip=15)
                print('-- row_clip on')
        scene_arr.append(scene)

    return scene_arr


def plot_images_and_masks(scene_arr):
    """
    Plot images and masks for each scene

    :param list Scene scene_arr: List of scenes
    :returns None:
    """
    print('\nPlotting images and masks...')
    for scene in scene_arr:
        scene.plot_images()
        scene.plot_udm2()


def calculate_strip_mask(scene_arr):
    """
    Creates a mask from the pixels that are marked `clear`
    for all scenes in the strip.

    :param list Scene scene_arr: List of scenes
    :returns None:
    """
    mask_arr = [s.udm2['clear'].astype(bool) for s in scene_arr]
    strip_mask = np.logical_and.reduce(mask_arr)
    return strip_mask


def calculate_ndvi_stats(scene_arr, water_mask_percentile=50):
    """
    Calculates the NDVI median and standard deviation for each scene
    in the strip. A strip mask (see `calculate_strip_mask`) and a water mask
    are applied to each scene to generate a sample of pixels that are both
    reliable and contain vegetation.

    :param list Scene scene_arr: List of scenes
    :param int water_mask_percentile: Percentile above which
        blue pixels are masked
    :returns None:
    """
    mask_strip = calculate_strip_mask(scene_arr)

    # Find and characterize the NDVI pixels for each scene
    ndvi_med_arr = []
    ndvi_std_arr = []
    acquired_arr = []
    for scene in scene_arr:
        mask_water = scene.calculate_percentile_mask('blue',
                                                     water_mask_percentile)
        mask_scene = np.logical_and(mask_strip, mask_water)
        ndvi = scene.calculate_ndvi(convert_to_toa=True)

        ndvi_med_arr.append(np.median(ndvi[mask_scene]))
        ndvi_std_arr.append(np.std(ndvi[mask_scene]))
        acquired_arr.append(scene.acquired)

    return acquired_arr, ndvi_med_arr, ndvi_std_arr


def calculate_ndvi_arr(scene_arr, apply_mask=True, water_mask_percentile=50):
    """
    Retrieve the NDVI pixels for each scene
    in the strip. If apply_mask = True, a strip mask
    (see `calculate_strip_mask`) and a water mask are applied to each scene
    to generate a sample of pixels that are both reliable and contain
    vegetation.

    :param list Scene scene_arr: List of scenes
    :param bool apply_mask: If True, apply all masks. If False, skip masks.
    :param int water_mask_percentile: Percentile above which
        blue pixels are masked
    :returns None:
    """
    mask_strip = calculate_strip_mask(scene_arr)

    # Find NDVI pixels for each scene
    ndvi_arr = []
    for scene in scene_arr:
        mask_water = scene.calculate_percentile_mask('blue',
                                                     water_mask_percentile)
        mask_scene = np.logical_and(mask_strip, mask_water)
        ndvi = scene.calculate_ndvi(convert_to_toa=True)
        if apply_mask:
            ndvi_arr.append(ndvi[mask_scene])
        else:
            ndvi_arr.append(ndvi.flatten())

    return ndvi_arr


def generate_delta_days(acquired_arr):
    """
    Calculate the difference (in days) between subsequent observations.

    :param list datetime acquired_arr: List of observations dates
    :returns list float: List of days between subsequent observations.
    """
    delta_days_arr = []
    for i in range(len(acquired_arr) - 1):
        date_start = acquired_arr[i]
        date_end = acquired_arr[i + 1]
        delta_seconds = (date_end - date_start).total_seconds()
        delta_days = delta_seconds / (60 * 60 * 24)
        delta_days_arr.append(delta_days)
    return np.array(delta_days_arr)


def plot_ndvi_hist(scene_arr, remove_first_image=False,
                   water_mask_percentile=50):
    """
    Plot the NDVI pixels for each scene in the strip.

    If remove_first_image=True, remove the first image from the strip due to
    its missing rows. If False, clip the remaining images by 15 rows to
    create a match in size between all scenes.

    The subplots demonstrate the effect of applying a mask, creating a less
    noisy and more reliable sample. They also show a clear progression to a
    more vegetative state (higher NDVI) followed by a drop-off at the
    latest dates.

    :param list Scene scene_arr: List of scenes
    :param bool remove_first_image: If True, remove the first image from
        the strip due to its missing rows. If false, clip the remaining
        images by 15 rows to create a match in size between all scenes.
    :param int water_mask_percentile: Percentile above which
        blue pixels are masked
    :returns None:
    """
    ndvi_arr = calculate_ndvi_arr(scene_arr,
                                  water_mask_percentile=water_mask_percentile)
    ndvi_unmasked_arr = calculate_ndvi_arr(scene_arr, apply_mask=False)

    bins = np.linspace(0.01, 1, 100)
    fig, axes = plt.subplots(3, 2, figsize=(8, 6))
    axes = axes.flatten()
    fig.suptitle(f'NDIV Pixels', fontsize=14)
    for i, ax in enumerate(axes):
        scene = scene_arr[i]
        ax.set_title(scene.acquired_label)
        ax.hist(ndvi_arr[i], bins=bins, histtype='step', color='b',
                label='Masked', lw=2, density=True)
        ax.hist(ndvi_unmasked_arr[i], bins=bins, histtype='step', color='g',
                label='No Mask', lw=2, density=True)
        ax.grid(True)
        ax.legend(loc=2)
        ax.set_xlabel('NDVI', fontsize=12)
        ax.set_ylabel('Relative Density', fontsize=12)

    fig.tight_layout()
    fig.subplots_adjust(top=.9)

    fname = 'figures/ndvi_hist'
    if remove_first_image:
        fname += '_clipped'
    fname += f'_blue{water_mask_percentile}.png'
    fig.savefig(fname, dpi=75, bbox_inches='tight', pad_inches=0.05)
    print(f'{fname} saved')


def plot_ndvi_trends(scene_arr, remove_first_image=False,
                     water_mask_percentile=50):
    """
    Plot the NDVI trends across the entire strip, as well as the approximate
    rate of change of the NDVI across the observations.

    If remove_first_image=True, remove the first image from the strip due to
    its missing rows. If False, clip the remaining images by 15 rows to
    create a match in size between all scenes.

    The trend shows a clear progression to a more vegetative state
    (higher NDVI) in September, followed by a drop-off at the
    latest date.

    :param list Scene scene_arr: List of scenes
    :param bool remove_first_image: If True, remove the first image from
        the strip due to its missing rows. If false, clip the remaining
        images by 15 rows to create a match in size between all scenes.
    :param int water_mask_percentile: Percentile above which
        blue pixels are masked
    :returns None:
    """
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


def plot_ndvi_trends_water_mask(scene_arr):
    """
    Plot the NDVI trends across the entire strip and demonstrate the
    effect of applying a water mask to the images. Both curves have
    the strip mask applied.

    The application of the water mask reduces the uncertainty in the
    measurement, while maintaining the same evolution of the curve.

    :param list Scene scene_arr: List of scenes
    :returns None:
    """
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

    fname = 'figures/ndvi_trends_water_mask.png'
    fig.savefig(fname, dpi=75, bbox_inches='tight', pad_inches=0.05)
    print(f'{fname} saved')


def plot_water_mask(scene_arr, water_mask_percentile=50):
    """
    Plot the water mask for the first scene in the strip.

    The water mask threshold is calculated by taking a percentile of the blue
    pixels in the image. For example `mwater_mask_percentile=50` calculates
    the 50th percentile value for a blue pixel, and
    `calculate_percentile_mask` returns a mask that indicates which pixels
    are above (and below) this threshold. Pixels which are above the water
    mask threshold are masked out, while pixels below the water mask threshold
    are retained.

    The mask is successfully removing the water features in the image. There
    are vegetative pixels that are lost as well, but the resulting sample
    is a cleaner one that will better indicate the vegetative health of the
    region.

    :param list Scene scene_arr: List of scenes
    :param int water_mask_percentile: Percentile above which
        blue pixels are masked
    :returns None:
    """
    scene = scene_arr[0]
    blue = scene.images['blue']
    mask_water = scene.calculate_percentile_mask('blue',
                                                 water_mask_percentile)

    #  Pixels below the water mask threshold are retained
    blue_below_threshold = np.zeros_like(blue)
    blue_below_threshold[:] = blue
    blue_below_threshold[mask_water] = 0

    #  Pixels which are above the water mask threshold are masked out
    blue_above_threshold = np.zeros_like(blue)
    blue_above_threshold[:] = blue
    blue_above_threshold[~mask_water] = 0

    fig, ax = plt.subplots(1, 2, figsize=(6, 3))
    fig.suptitle('Effect of Water Mask')
    ax[0].set_title('Above Water Mask Threshold', fontsize=14)
    ax[0].imshow(blue_below_threshold, cmap='Blues')
    ax[0].axis('off')
    ax[1].set_title('Below Water Mask Threshold', fontsize=14)
    ax[1].imshow(blue_above_threshold, cmap='Blues')
    ax[1].axis('off')
    fig.tight_layout()
    fig.subplots_adjust(top=.8)

    fname = 'figures/water_mask.png'
    fig.savefig(fname, dpi=75, bbox_inches='tight', pad_inches=0.05)
    print(f'{fname} saved')


def analyze_scenes(remove_first_image, water_mask_percentile,
                   skip_plot_image_masks):
    """
    Generate analysis plots that indicate the trends in vegetative health
    across the scenes.

    A later step builds a mask out of overlapping pixels from the scenes,
    requiring them to be of the same extent. However the first image is 15 rows
    short, requiring either (1) removing the first image from the analysis,
    or (2) clipping the remaining scenes by 15 rows. If
    remove_first_image=True, remove the first image from the strip due to
    its missing rows. If False, clip the remaining images by 15 rows to
    create a match in size between all scenes.

    A mask that removes water features is calculated by thresholding a
    percentile of the blue pixels in the image. For example
    `water_mask_percentile=50` calculates the 50th percentile value for a
    blue pixel, and `calculate_percentile_mask` returns a mask that indicates
    which pixels are above (and below) this threshold. Pixels which are above
    the water mask threshold are masked out, while pixels below the water mask
    threshold are retained.

    The mask is successfully removing the water features in the image. There
    are vegetative pixels that are lost as well, but the resulting sample
    is a cleaner one that will better indicate the vegetative health of the
    region.

    :param bool remove_first_image: If True, remove the first image from
        the strip due to its missing rows. If false, clip the remaining
        images by 15 rows to create a match in size between all scenes.
    :param int water_mask_percentile: Percentile above which
        blue pixels are masked
    :param bool skip_plot_image_masks: If True, skip generating image and
        mask plots for the scenes.
    :returns None:
    """

    scene_arr = load_scenes(remove_first_image=remove_first_image)
    if not skip_plot_image_masks:
        plot_images_and_masks(scene_arr)

    print('\nPlotting analysis figures')
    plot_water_mask(scene_arr, water_mask_percentile=water_mask_percentile)
    plot_ndvi_hist(scene_arr, remove_first_image=remove_first_image,
                   water_mask_percentile=water_mask_percentile)
    plot_ndvi_trends_water_mask(scene_arr)
    plot_ndvi_trends(scene_arr, remove_first_image=remove_first_image,
                     water_mask_percentile=water_mask_percentile)


def main():
    formatter = argparse.ArgumentDefaultsHelpFormatter
    parser = argparse.ArgumentParser(description='Analyze scenes for '
                                                 'vegetation trends.',
                                     formatter_class=formatter)

    help_str = 'This analysis script generates plots of the images and ' \
               'masks for each scene. This flag skips that output.'
    parser.add_argument('--skip-plot-images-masks',
                        action='store_false', help=help_str)
    parser.set_defaults(skip_plot_image_masks=False)

    help_str = 'A strip mask is constructed by finding the "clear" pixels ' \
               'that all scenes in the set of imaages have in common. ' \
               'The first analysis has 15 less rows than the remaining ' \
               'images, despite being clipped to the same extent. ' \
               'Activating this flag removes the first image from the ' \
               'analysis. If not selected, the remaining scenes are ' \
               'clipped by 15 rows to generate a strip mask.'
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
