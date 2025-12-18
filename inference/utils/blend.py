import rasterio
import numpy as np
import os
from rasterio.warp import reproject, Resampling
from rasterio.transform import from_origin
from rasterio.windows import Window 
from tqdm import tqdm
from collections import defaultdict

def _distance_weight(h, w):
    """
    Generate a smooth linear distance-to-edge weight map.
    Weight = min distance to edge / (half of min dimension)
    """
    yy, xx = np.mgrid[0:h, 0:w]
    dist_y = np.minimum(yy, h - 1 - yy)
    dist_x = np.minimum(xx, w - 1 - xx)
    dist = np.minimum(dist_y, dist_x)
    norm = np.maximum(dist / (0.5 * min(h, w)), 0)
    return norm.astype(np.float16)


def _hann_weight(h, w):
    """
    Generate a 2D Hann (cosine) weight map.
    """
    wy = np.hanning(h)
    wx = np.hanning(w)
    return np.outer(wy, wx).astype(np.float16)

def blend_patches_to_raster(
    output_path,
    patch_files=None,
    patch_folder=None,
    blend="average",
    dtype="uint16",
    mask_file=None,
):
    """
    Blend overlapping patch GeoTIFFs into one raster.
    Optionally apply a mask raster (same or larger extent).

    Parameters:
    - output_path: str, path to save the blended raster
    - patch_files: list of file paths (optional)
    - patch_folder: folder containing patches (used only if patch_files is None)
    - blend: 'average', 'smooth', or 'hann'
    - dtype: 'uint16' or 'uint8'
    - mask_file: optional path to a mask raster; 1=keep, 0=mask out
    """

    if patch_files is None:
        if patch_folder is None:
            raise ValueError("Either patch_files or patch_folder must be provided")
        patch_files = sorted([
            os.path.join(patch_folder, f)
            for f in os.listdir(patch_folder)
            if f.lower().endswith(".tif") or f.lower().endswith(".vrt")
        ])

    if not patch_files:
        raise FileNotFoundError("No patches found")

    # reference metadata
    with rasterio.open(patch_files[0]) as ref:
        crs = ref.crs
        transform_ref = ref.transform
        pixel_size_x = transform_ref.a
        pixel_size_y = -transform_ref.e

    # define output bounds
    minx = miny = maxx = maxy = None
    for pf in patch_files:
        with rasterio.open(pf) as src:
            left, bottom, right, top = src.bounds
            minx = left if minx is None else min(minx, left)
            miny = bottom if miny is None else min(miny, bottom)
            maxx = right if maxx is None else max(maxx, right)
            maxy = top if maxy is None else max(maxy, top)

    width = int(np.ceil((maxx - minx) / pixel_size_x))
    height = int(np.ceil((maxy - miny) / pixel_size_y))
    transform = from_origin(minx, maxy, pixel_size_x, pixel_size_y)

    print(f"Output raster size: {width} × {height}")

    # initialize acummulator
    acc = np.zeros((height, width), dtype=np.float32)
    weight_sum = np.zeros((height, width), dtype=np.float32)

    # process each patch
    for pf in tqdm(patch_files, desc=f"Blending ({blend})"):
        with rasterio.open(pf) as src:
            data = src.read(1).astype(np.float32)
            h, w = data.shape

            if blend == "average":
                weight = np.ones((h, w), dtype=np.float32)
            elif blend == "smooth":
                weight = _distance_weight(h, w)
            elif blend == "hann":
                weight = _hann_weight(h, w)
            else:
                raise ValueError("blend must be 'average', 'smooth', or 'hann'")

            left, top = src.transform * (0, 0)
            col_off = int(round((left - minx) / pixel_size_x))
            row_off = int(round((maxy - top) / pixel_size_y))

            acc[row_off:row_off+h, col_off:col_off+w] += data * weight
            weight_sum[row_off:row_off+h, col_off:col_off+w] += weight

    # combine patches
    result = np.divide(acc, weight_sum, out=np.zeros_like(acc), where=(weight_sum > 0))

    # optional mask
    if mask_file:
        print(f"Applying mask: {mask_file}")
        with rasterio.open(mask_file) as mask_src:
            mask_data = np.zeros((height, width), dtype=np.uint8)
            reproject(
                source=rasterio.band(mask_src, 1),
                destination=mask_data,
                src_transform=mask_src.transform,
                src_crs=mask_src.crs,
                dst_transform=transform,
                dst_crs=crs,
                resampling=Resampling.nearest,
            )
        result *= (mask_data == 1)  # keep only where mask==1

    # convert dtype
    if dtype == "uint16":
        result = np.clip(result, 0, 65535).astype(np.uint16)
    elif dtype == "uint8":
        result = np.clip(result, 0, 255).astype(np.uint8)

    # save output
    meta = {
        'driver': 'GTiff',
        'height': height,
        'width': width,
        'count': 1,
        'dtype': dtype,
        'crs': crs,
        'transform': transform,
        'compress': 'lzw',
        'photometric': 'minisblack',
        'nodata': 0,
    }

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with rasterio.open(output_path, 'w', **meta) as dst:
        dst.write(result, 1)

    print(f"Blended raster saved: {output_path}")