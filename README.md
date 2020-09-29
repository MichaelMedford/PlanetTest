# Measuring Green Vegetation

### Measuring Vegetative Health
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

### Masks
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

### Clipping to a Uniform Extent

The first image in the strip is 15 rows shorter than the rest of the images. 
The strip mask mentioned above requires that all images in the strip be of 
the same extent. Therefore the analysis can either be performed by removing 
the first image (see `--remove-first-image` option in `analysis.py`), or 
by keeping the first image and clipping the remaining images by 15 rows. 
Clipping the rows of the rest of the images has no noticeable impact on the 
NDVI results, and therefore this is the default behavior in order to retain 
the first image in the strip.

### Figures
This analysis script generates plots:
- **plot_ndvi_hist** : Histograms of the NDVI pixels for each scene, 
'with and without masks
- **plot_ndvi_trends** : Trends of the NDVI evolution across the scenes, 
as well as rate of change of the NDVI trends across the scenes.
- **plot_ndvi_trends_water_mask** : Trends of the NDVI evolution across 
the scenes, with and without masks.
- **plot_water_mask** : Images of the water mask for a single scene.

### Generating Plots

The `analysis.py` script loads images into memory as instances of 
`product.py:Scene` and generates plots for analysis and diagnostics.

Options for running the script can be seen with

    python analysis.py -h
    
An example execution would be

    python analysis.py -water-mask-percentile 50
    
Plots of the scene images and masks are generated into the `data` folder, 
while analysis figures are generated in the `figures` folder. The mask plots 
are useful to inspect individual scenes for inaccurate masks. It was through 
this inspection that the `clear` mask was determined to be of good quality 
for all scenes in the strip.
   