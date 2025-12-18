import os
from osgeo import gdal
import numpy as np
from glob import glob

# --- Parameters ---
resolution = 1  # meters
pixel_size = resolution ** 2  # m²
min_size = 100  # m² (0.01 ha)
min_pixel_amount = int(min_size / pixel_size)
print(f"Minimum pixel amount: {min_pixel_amount}")

# --- Function ---
def gdal_sieve(input_path, output_path, threshold=64, connectivity=4, prob_threshold=0.5, apply_mask=False, masked_output_path=None):
    """Apply GDAL’s SieveFilter after thresholding a probability raster."""
    src_ds = gdal.Open(input_path)
    if src_ds is None:
        print(f"Could not open {input_path}")
        return None

    srcband = src_ds.GetRasterBand(1)
    arr = srcband.ReadAsArray()

    # Threshold probabilities -> binary mask
    binary = (arr >= prob_threshold).astype(np.uint8)

    # Create temporary in-memory raster
    driver = gdal.GetDriverByName("MEM")
    src_mem = driver.Create("", src_ds.RasterXSize, src_ds.RasterYSize, 1, gdal.GDT_Byte)
    src_mem.SetGeoTransform(src_ds.GetGeoTransform())
    src_mem.SetProjection(src_ds.GetProjection())
    src_mem.GetRasterBand(1).WriteArray(binary)

    # Prepare output dataset
    out_driver = gdal.GetDriverByName("GTiff")
    out_ds = out_driver.Create(
        output_path,
        src_ds.RasterXSize,
        src_ds.RasterYSize,
        1,
        gdal.GDT_Byte,
        options=["COMPRESS=LZW", "TILED=YES"]
    )
    out_ds.SetGeoTransform(src_ds.GetGeoTransform())
    out_ds.SetProjection(src_ds.GetProjection())

    # Apply sieve filter
    gdal.SieveFilter(src_mem.GetRasterBand(1), None, out_ds.GetRasterBand(1), threshold, connectivity)
    out_ds.GetRasterBand(1).SetNoDataValue(0)
    out_ds.FlushCache()

    print(f"Sieved mask saved to: {output_path}")

    # --- Optional: apply sieved mask to original probability raster ---
    if apply_mask:
        if masked_output_path is None:
            masked_output_path = output_path.replace(".tif", "_masked.tif")

        sieved_mask = out_ds.GetRasterBand(1).ReadAsArray().astype(bool)
        masked_prob = np.where(sieved_mask, arr, 0).astype(np.uint16)

        masked_ds = out_driver.Create(
            masked_output_path,
            src_ds.RasterXSize,
            src_ds.RasterYSize,
            1,
            gdal.GDT_UInt16,
            options=["COMPRESS=LZW", "TILED=YES"]
        )
        masked_ds.SetGeoTransform(src_ds.GetGeoTransform())
        masked_ds.SetProjection(src_ds.GetProjection())
        masked_ds.GetRasterBand(1).WriteArray(masked_prob)
        masked_ds.GetRasterBand(1).SetNoDataValue(0)
        masked_ds.FlushCache()

        print(f"Masked probability raster saved to: {masked_output_path}")

        masked_ds = None

    src_ds = None
    src_mem = None
    out_ds = None


# --- Batch mode ---
input_dir = "/postprocessing/mosaic/tile_masked"
output_dir = "/postprocessing/mosaic/tile_masked_sieved"
os.makedirs(output_dir, exist_ok=True)

tifs = sorted(glob(os.path.join(input_dir, "*.tif")))

print(f"Found {len(tifs)} input rasters to process.\n")

for tif in tifs:
    fname = os.path.basename(tif)
    out_mask = os.path.join(output_dir, fname.replace(".tif", "_mask.tif"))
    out_prob = os.path.join(output_dir, fname.replace(".tif", "_masked_prob.tif"))

    gdal_sieve(
        input_path=tif,
        output_path=out_mask,
        threshold=min_pixel_amount,
        prob_threshold=500,  # adjust threshold based on your data scale
        apply_mask=True,
        masked_output_path=out_prob
    )
