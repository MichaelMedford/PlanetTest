# Task

The data folder includes GeoTIFFs for a number of PlanetScope acquisitions over Sumatra between June and September, 2020.  The `AnalyticMS` files are `analytic` assets from [PSScene4Band][PSScene4Band] imagery; the `udm2` files are [Usable Data Masks][UDM2]; and the `metadata.json` and `.xml` files include the full imagery footprint, acquisition times, and additional metadata.  All raster data is clipped to the same extent (which is different than the full imagery footprints). Please note, the `udm2` files are not always accurate and it is recommended that you preview them before trusting the mask. For information, e.g. about the band order or units, please see the linked documentation.

Your task is to write a program that analyzes the imagery and produces an approximate measure indicating the rate of change from green vegetation to bare soil over the time period represented by the image series.

In submitting your task, please provide instructions on running your program and include any additional detail describing the choices you made or issues you encountered.

 [PSScene4Band]: https://developers.planet.com/docs/data/psscene4band/
 [UDM2]: https://developers.planet.com/docs/data/udm-2/
