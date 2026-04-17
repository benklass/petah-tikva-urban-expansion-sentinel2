import rasterio
import numpy as np
from pathlib import Path
from rasterio.features import sieve, shapes
from shapely.geometry import shape
import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, ListedColormap

# --------------------------------------------------
# Add the .tif file paths
# --------------------------------------------------
data_dir = Path("data")

files = {
    2018: data_dir / "PetahTikva_S2_2018.tif",
    2021: data_dir / "PetahTikva_S2_2021.tif",
    2023: data_dir / "PetahTikva_S2_2023.tif",
    2025: data_dir / "PetahTikva_S2_2025.tif",
}

def read_stack(path):
    with rasterio.open(path) as src:
        arr = src.read()  # shape: (bands, rows, cols)
        profile = src.profile
    return arr, profile

stacks = {}
profiles = {}

for year, path in files.items():
    arr, profile = read_stack(path)
    stacks[year] = arr
    profiles[year] = profile

# --------------------------------------------------
# Create a band index
# --------------------------------------------------
BAND_INDEX = {
    "B2": 0,
    "B3": 1,
    "B4": 2,
    "B8": 3,
    "B11": 4,
    "B12": 5,
    "NDVI": 6,
    "NDBI": 7,
    "BSI": 8,
}

# --------------------------------------------------
# Compute the change layers (layer differences)
# --------------------------------------------------
def diff_band(year1, year2, band_name):
    i = BAND_INDEX[band_name]
    return stacks[year2][i] - stacks[year1][i]

d_ndvi_18_25 = diff_band(2018, 2025, "NDVI")
d_ndbi_18_25 = diff_band(2018, 2025, "NDBI")
d_bsi_18_25  = diff_band(2018, 2025, "BSI")

# --------------------------------------------------
# Create a rule-based urban conversion mask
# --------------------------------------------------
ndvi_2018 = stacks[2018][BAND_INDEX["NDVI"]]
ndvi_2025 = stacks[2025][BAND_INDEX["NDVI"]]
ndbi_2018 = stacks[2018][BAND_INDEX["NDBI"]]
ndbi_2025 = stacks[2025][BAND_INDEX["NDBI"]]
bsi_2025  = stacks[2025][BAND_INDEX["BSI"]]

candidate_conversion = (
    (ndvi_2018 > 0.35) &               # was vegetated/open
    (ndvi_2025 < 0.30) &               # vegetation declined
    (d_ndvi_18_25 < -0.15) &           # clear NDVI drop
    (d_ndbi_18_25 > 0.10) &            # built-up signal rose
    (ndbi_2025 > 0.00)                 # now more built-like
)

# Detect likely construction zones
candidate_construction = (
    (d_ndvi_18_25 < -0.15) &
    (d_bsi_18_25 > 0.10) &
    (bsi_2025 > 0.05)
)

# --------------------------------------------------
# Remove very small isolated patches
# size=20 means remove connected patches smaller than 20 pixels
# --------------------------------------------------
conversion_clean = sieve(candidate_conversion.astype("uint8"), size=20).astype(bool)
construction_clean = sieve(candidate_construction.astype("uint8"), size=20).astype(bool)

print("Conversion pixels after cleaning:", conversion_clean.sum())
print("Construction pixels after cleaning:", construction_clean.sum())

# --------------------------------------------------
# Save change masks as GeoTIFF
# --------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
outputs_dir = BASE_DIR / "outputs"
outputs_dir.mkdir(exist_ok=True)

def write_single_band_geotiff(output_path, array, reference_profile, dtype="uint8"):
    profile = reference_profile.copy()
    profile.update(
        count=1,
        dtype=dtype,
        compress="lzw"
    )

    with rasterio.open(output_path, "w", **profile) as dst:
        dst.write(array.astype(dtype), 1)

write_single_band_geotiff(
    outputs_dir / "conversion_2018_2025.tif",
    conversion_clean,
    profiles[2018]
)

write_single_band_geotiff(
    outputs_dir / "construction_2018_2025.tif",
    construction_clean,
    profiles[2018]
)

print("Change masks saved successfully.")

# --------------------------------------------------
# Save cleaned conversion mask as PNG (black and white)
# --------------------------------------------------
plt.figure(figsize=(8, 8))
plt.imshow(conversion_clean, cmap="gray", vmin=0, vmax=1)
plt.title("Cleaned conversion mask (2018–2025)")
plt.axis("off")
plt.savefig(
    outputs_dir / "conversion_2018_2025_mask.png",
    bbox_inches="tight",
    pad_inches=0,
    dpi=300
)
plt.show()

print("Black-and-white PNG mask saved successfully.")

# --------------------------------------------------
# Calculate changed areas and convert to hectares
# --------------------------------------------------
pixel_area_m2 = 10 * 10  # Sentinel-2 10 m pixel

conversion_area_m2 = conversion_clean.sum() * pixel_area_m2
construction_area_m2 = construction_clean.sum() * pixel_area_m2

conversion_area_ha = conversion_area_m2 / 10000
construction_area_ha = construction_area_m2 / 10000

print(f"Likely vegetation/open-to-built conversion: {conversion_area_ha:.2f} ha")
print(f"Likely construction-stage land: {construction_area_ha:.2f} ha")

# --------------------------------------------------
# Load the same raster and convert it to polygons
# --------------------------------------------------
def raster_mask_to_polygons(mask, transform, crs):
    geoms = []

    for geom, value in shapes(mask.astype("uint8"), mask=mask, transform=transform):
        if value == 1:
            geoms.append(shape(geom))

    gdf = gpd.GeoDataFrame(geometry=geoms, crs=crs)

    if not gdf.empty:
        gdf = gdf.to_crs(epsg=2039)
        gdf["area_m2"] = gdf.geometry.area
        gdf["area_ha"] = gdf["area_m2"] / 10000
        gdf = gdf.sort_values("area_m2", ascending=False).reset_index(drop=True)

    return gdf

print("Candidate conversion pixels:", candidate_conversion.sum())
print("Cleaned conversion pixels:", conversion_clean.sum())

# Create hotspots variable with geospatial table
with rasterio.open(outputs_dir / "conversion_2018_2025.tif") as src:
    conv_mask = src.read(1).astype(bool)
    transform = src.transform
    crs = src.crs

hotspots = raster_mask_to_polygons(conv_mask, transform, crs)

print(hotspots.head(10))
print("Number of hotspot polygons:", len(hotspots))

# Save hotspot polygons
if not hotspots.empty:
    hotspots.to_file(outputs_dir / "conversion_hotspots.geojson", driver="GeoJSON")
    print("Hotspots saved as GeoJSON.")
else:
    print("No hotspot polygons found.")

# Show top hotspot patches
if not hotspots.empty:
    print("\nTop 10 largest conversion hotspots:")
    print(hotspots[["area_ha"]].head(10))
else:
    print("No hotspots to display.")

# --------------------------------------------------
# Colormaps
# --------------------------------------------------

# NDVI colormap matching the GEE NDVI palette
ndvi_colors = [
    "#f0f0f0",  # light gray
    "#d9d9d9",
    "#bdbdbd",
    "#c7e9c0",  # pale green
    "#74c476",  # medium green
    "#238b45",
    "#00441b"   # dark green
]
ndvi_cmap = LinearSegmentedColormap.from_list("gee_ndvi", ndvi_colors, N=256)

# Harmonized hotspot overlay color
hotspot_cmap = ListedColormap(["#7f0000"])

# Fixed BSI colormap: green -> yellow -> brown
bsi_colors = [
    "#1a9850",  # vegetation / low BSI
    "#91cf60",
    "#d9ef8b",
    "#fee08b",
    "#fdae61",
    "#a6611a",
    "#6b3d0c"   # strong bare soil / high BSI
]
bsi_cmap = LinearSegmentedColormap.from_list("bsi_clean", bsi_colors, N=256)

# --------------------------------------------------
# Plot the cleanest conversion mask
# --------------------------------------------------
plt.figure(figsize=(8, 8))
plt.imshow(conversion_clean, cmap="gray", vmin=0, vmax=1)
plt.title("Cleaned conversion mask (2018–2025)")
plt.axis("off")
plt.show()

# --------------------------------------------------
# Plot the conversion mask over the NDVI background
# --------------------------------------------------
plt.figure(figsize=(8, 8))
plt.imshow(ndvi_2018, cmap=ndvi_cmap, vmin=-0.2, vmax=0.8)
plt.imshow(
    np.ma.masked_where(~conversion_clean, conversion_clean),
    cmap=hotspot_cmap,
    alpha=0.45,
    vmin=0,
    vmax=1
)
plt.title("Likely urban conversion hotspots over 2018 NDVI")
plt.axis("off")
plt.savefig(
    outputs_dir / "ndvi2018_hotspots_overlay.png",
    bbox_inches="tight",
    pad_inches=0,
    dpi=300
)
plt.show()

print("NDVI 2018 hotspot overlay PNG saved successfully.")

# --------------------------------------------------
# Plot the construction mask over the BSI background
# --------------------------------------------------
plt.figure(figsize=(8, 8))
plt.imshow(bsi_2025, cmap=bsi_cmap, vmin=-0.3, vmax=0.4)
plt.imshow(
    np.ma.masked_where(~construction_clean, construction_clean),
    cmap=hotspot_cmap,
    alpha=0.55,
    vmin=0,
    vmax=1
)
plt.title("Likely construction-stage areas over 2025 BSI")
plt.axis("off")
plt.savefig(
    outputs_dir / "bsi2025_construction_overlay.png",
    bbox_inches="tight",
    pad_inches=0,
    dpi=300
)
plt.show()

print("BSI 2025 construction overlay PNG saved successfully.")

# --------------------------------------------------
# Plot index-change histograms for threshold tuning
# --------------------------------------------------
plt.figure(figsize=(7, 4))
plt.hist(d_ndvi_18_25.ravel(), bins=100)
plt.title("Distribution of ΔNDVI (2018–2025)")
plt.xlabel("ΔNDVI")
plt.ylabel("Pixel count")
plt.show()

plt.figure(figsize=(7, 4))
plt.hist(d_ndbi_18_25.ravel(), bins=100)
plt.title("Distribution of ΔNDBI (2018–2025)")
plt.xlabel("ΔNDBI")
plt.ylabel("Pixel count")
plt.show()

plt.figure(figsize=(7, 4))
plt.hist(d_bsi_18_25.ravel(), bins=100)
plt.title("Distribution of ΔBSI (2018–2025)")
plt.xlabel("ΔBSI")
plt.ylabel("Pixel count")
plt.show()

# --------------------------------------------------
# Determine NDVI, NDBI and BSI trends
# --------------------------------------------------
print("Mean ΔNDVI in hotspots:", d_ndvi_18_25[conversion_clean].mean())
print("Mean ΔNDBI in hotspots:", d_ndbi_18_25[conversion_clean].mean())
print("Mean ΔBSI in construction hotspots:", d_bsi_18_25[construction_clean].mean())

construction_overlay = np.where(construction_clean, 1.0, np.nan)

plt.figure(figsize=(8, 8))
plt.imshow(construction_overlay, cmap=ListedColormap(["#7f0000"]))
plt.title("Construction overlay only")
plt.axis("off")
plt.show()