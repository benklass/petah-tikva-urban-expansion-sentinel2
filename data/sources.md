# Data Sources

This file documents all datasets, satellite imagery, derived raster layers, spectral indices, geospatial outputs, and analytical products used in the **Petah Tikva Urban Expansion Detection Using Sentinel-2** project.

---

# 1. Study Area Boundary

## Area of Interest (AOI)

The study area represents the southeastern fringe of **Petah Tikva**, located within the Gush Dan metropolitan region of central Israel.

Used for:

- clipping Sentinel-2 imagery  
- focusing urban-rural interface analysis  
- hotspot detection  
- map centering  
- export boundaries for Google Earth Engine  

---

# 2. Satellite Imagery

## Sentinel-2 Surface Reflectance

**Source:**

European Space Agency (ESA) / Copernicus Programme via Google Earth Engine

Used to analyze land-cover and urban expansion trends between 2018 and 2025.

### Years Used

- 2018  
- 2021  
- 2023  
- 2025  

### Resolution

- 10 m (primary bands)

### Format

- GeoTIFF (.tif)

### Files Used

- PetahTikva_S2_2018.tif  
- PetahTikva_S2_2021.tif  
- PetahTikva_S2_2023.tif  
- PetahTikva_S2_2025.tif  

---

# 3. Spectral Bands Used

The following Sentinel-2 bands were extracted for analysis:

- B2 (Blue)  
- B3 (Green)  
- B4 (Red)  
- B8 (Near Infrared)  
- B11 (SWIR-1)  
- B12 (SWIR-2)

### Purpose

Used for:

- vegetation detection  
- built-up detection  
- bare soil detection  
- index generation  
- temporal comparison  

---

# 4. Derived Spectral Indices

The following indices were calculated in Google Earth Engine:

## NDVI

Normalized Difference Vegetation Index

Used to measure vegetation presence and decline.

## NDBI

Normalized Difference Built-up Index

Used to identify increasing built-up surfaces.

## BSI

Bare Soil Index

Used to detect exposed soil, disturbed surfaces, and likely construction-stage land.

---

# 5. Temporal Composites

## Seasonal Composite Method

Cloud-filtered dry-season median composites were created for each year.

### Time Window

- May to July

### Purpose

Used to:

- reduce cloud contamination  
- improve year-to-year comparability  
- minimize seasonal vegetation effects  

---

# 6. Change Detection Layers

The following change layers were generated in Python:

## ΔNDVI

Difference between 2025 and 2018 NDVI.

## ΔNDBI

Difference between 2025 and 2018 NDBI.

## ΔBSI

Difference between 2025 and 2018 BSI.

### Purpose

Used to identify likely urban conversion areas.

---

# 7. Urban Conversion Logic

Urban land conversion was identified using rule-based thresholds:

- NDVI decline  
- NDBI increase  
- BSI increase  
- Previously vegetated/open land transitioning toward built surfaces

### Derived Output

- candidate_conversion  
- candidate_construction  

---

# 8. Raster Post-Processing

The following processing steps were applied:

## Speckle Removal

Small isolated raster patches removed using connected-pixel filtering.

## Binary Masks

Generated outputs:

- conversion_2018_2025.tif  
- construction_2018_2025.tif  

## Polygon Extraction

Raster masks converted to polygons.

### Output

- conversion_hotspots.geojson

---

# 9. Statistical Outputs

The following summary metrics were calculated:

## Mean Change in Hotspots

- Mean ΔNDVI = -0.46  
- Mean ΔNDBI = +0.29  
- Mean ΔBSI = +0.27

### Interpretation

Indicates:

- vegetation loss  
- built-up expansion  
- exposed soil linked to construction activity  

---

# 10. Exported Figures

Generated outputs include:

## Maps

- ndvi_2018.png  
- ndvi_2025.png  
- ndvi2018_hotspots_overlay.png  
- bsi2025_construction_overlay.png  
- conversion_mask.png  

## Histograms

- hist_ndvi.png  
- hist_ndbi.png  
- hist_bsi.png  

## Documents

- report.pdf  
- project_poster.pdf  
- project_poster.jpg  

---

# 11. Scripts and Code

## Google Earth Engine

- gee_petah_tikva_preprocessing.js

Used for:

- cloud masking  
- composite generation  
- index calculation  
- GeoTIFF export  

## Python

- main.py

Used for:

- raster analysis  
- threshold change detection  
- hotspot extraction  
- visualization  

---

# 12. Software Environment

## Platforms Used

- Google Earth Engine  
- Python  
- GitHub  

## Python Libraries

- rasterio  
- numpy  
- geopandas  
- matplotlib  
- shapely  

---

# 13. Notes

- Sentinel-2 imagery was composited using dry-season scenes to improve temporal consistency.
- Spectral thresholds represent analytical decision rules rather than absolute land-cover truth.
- Construction hotspots indicate likely active transformation zones, not legal planning status.
- Urban expansion outputs should be interpreted as remote sensing evidence of land-cover change.

---

# 14. Citation Suggestions

European Space Agency (Copernicus Sentinel-2)  
Google Earth Engine  
Rasterio Documentation  
GeoPandas Documentation  
Matplotlib Documentation  
NumPy Documentation

---