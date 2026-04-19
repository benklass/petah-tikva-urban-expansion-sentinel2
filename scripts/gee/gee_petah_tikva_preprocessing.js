// Area of influence (AOI)
var aoi = ee.Geometry.Rectangle([34.86, 32.05, 35.02, 32.16]);

Map.centerObject(aoi, 11);
Map.addLayer(aoi, {color: 'red'}, 'AOI');

// Sentinel-2 Harmonized Surface Reflectance collection
var s2 = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED');

// Cloud masking function
function maskS2Clouds(img) {
  var qa = img.select('QA60');
  var cloudBitMask = 1 << 10;
  var cirrusBitMask = 1 << 11;

  var mask = qa.bitwiseAnd(cloudBitMask).eq(0)
               .and(qa.bitwiseAnd(cirrusBitMask).eq(0));

  return img.updateMask(mask)
            .divide(10000)
            .copyProperties(img, img.propertyNames());
}

// Add spectral indices
function addIndices(img) {
  var ndvi = img.normalizedDifference(['B8', 'B4']).rename('NDVI');
  var ndbi = img.normalizedDifference(['B11', 'B8']).rename('NDBI');

  var bsi = img.expression(
    '((SWIR + RED) - (NIR + BLUE)) / ((SWIR + RED) + (NIR + BLUE))',
    {
      SWIR: img.select('B11'),
      RED: img.select('B4'),
      NIR: img.select('B8'),
      BLUE: img.select('B2')
    }
  ).rename('BSI');

  return img.addBands([ndvi, ndbi, bsi]);
}

// Create a dry-season composite for a given year
function seasonalComposite(year) {
  var start = ee.Date.fromYMD(year, 5, 1);
  var end = ee.Date.fromYMD(year, 7, 15);

  var comp = s2.filterBounds(aoi)
               .filterDate(start, end)
               .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
               .map(maskS2Clouds)
               .map(addIndices)
               .median()
               .clip(aoi);

  return comp.set('year', year);
}

// Years to process
var years = [2018, 2021, 2023, 2025];

var composites = ee.ImageCollection.fromImages(
  years.map(function(y) { return seasonalComposite(y); })
);

// Create specific year composites for display
var img2018 = seasonalComposite(2018);
var img2025 = seasonalComposite(2025);

// RGB visualization
var rgbVis = {
  bands: ['B4', 'B3', 'B2'],
  min: 0.02,
  max: 0.3
};

// NDVI visualization: light gray = unvegetated, dark green = dense vegetation
var ndviVis = {
  min: -0.2,
  max: 0.8,
  palette: [
    '#f0f0f0',
    '#d9d9d9',
    '#bdbdbd',
    '#c7e9c0',
    '#74c476',
    '#238b45',
    '#00441b'
  ]
};

// NDBI visualization
var ndbiVis = {
  min: -0.4,
  max: 0.4,
  palette: ['#1a9850', '#f7f7f7', '#d73027']
};

// Add map layers
Map.addLayer(img2018, rgbVis, 'RGB 2018');
Map.addLayer(img2025, rgbVis, 'RGB 2025');

Map.addLayer(img2018.select('NDVI'), ndviVis, 'NDVI 2018');
Map.addLayer(img2025.select('NDVI'), ndviVis, 'NDVI 2025');

Map.addLayer(img2025.select('NDBI'), ndbiVis, 'NDBI 2025');

// Export full yearly stacks for Python processing
function exportYear(year) {
  var img = seasonalComposite(year).select([
    'B2', 'B3', 'B4', 'B8', 'B11', 'B12',
    'NDVI', 'NDBI', 'BSI'
  ]);

  Export.image.toDrive({
    image: img,
    description: 'PetahTikva_S2_' + year,
    folder: 'GEE_PetahTikva_Change',
    fileNamePrefix: 'PetahTikva_S2_' + year,
    region: aoi,
    scale: 10,
    maxPixels: 1e13
  });
}

// Create visualized NDVI images for export
var ndvi2018_rgb = img2018.select('NDVI').visualize(ndviVis);
var ndvi2025_rgb = img2025.select('NDVI').visualize(ndviVis);

// Export NDVI 2018 as styled RGB image
Export.image.toDrive({
  image: ndvi2018_rgb,
  description: 'PetahTikva_NDVI_2018_RGB',
  folder: 'GEE_PetahTikva_Change',
  fileNamePrefix: 'PetahTikva_NDVI_2018_RGB',
  region: aoi,
  scale: 10,
  maxPixels: 1e13
});

// Export NDVI 2025 as styled RGB image
Export.image.toDrive({
  image: ndvi2025_rgb,
  description: 'PetahTikva_NDVI_2025_RGB',
  folder: 'GEE_PetahTikva_Change',
  fileNamePrefix: 'PetahTikva_NDVI_2025_RGB',
  region: aoi,
  scale: 10,
  maxPixels: 1e13
});

// Export all annual multiband stacks
years.forEach(exportYear);
