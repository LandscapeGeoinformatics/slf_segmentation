# slf_segmentation
[![DOI](https://zenodo.org/badge/1115127521.svg)](https://doi.org/10.5281/zenodo.17981736)
[![Open In Collab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/drive/1t3qIKnCiAzeVRBo7ap6kf2PxeseQHxgT)
<br>
Code supplement for Fauzan et al. (2026). Mapping small landscape features in agricultural lands using CNN-based semantic segmentation.
- Paper: [https://doi.org/10.1080/10106049.2026.2691353](https://doi.org/10.1080/10106049.2026.2691353)<br>
- Dataset and model weights: [https://doi.org/10.5281/zenodo.17978513](https://doi.org/10.5281/zenodo.17978513)<br>
- Google colab demo (simplified): [https://colab.research.google.com/drive/1t3qIKnCiAzeVRBo7ap6kf2PxeseQHxgT](https://colab.research.google.com/drive/1t3qIKnCiAzeVRBo7ap6kf2PxeseQHxgT)

## Summary

## Environment setup
- Install micromamba. See https://mamba.readthedocs.io/en/latest/installation/micromamba-installation.html
- Clone the repository
- Navigate to the repository folder, and create a new micromamba environment using `micromamba env create --file environment.yml`

## Usage
### Model training
- Specify input data and hyperparameters in `training/train.py` and run
- Use the training logs (*.csv) to plot the model behavior during training with `notebook/plot_loss.ipynb`
### Model testing
- Run `evaluation/test_inference.py` on one or more large images (e.g. 5x5km2) to obtain mosaicked probability prediction raster(s)
- Calculate AUC/ROC to define optimal probability threshold and accuracy metrics with `evaluation/test_accuracy.py`.
### Inference on mosaic
- Run `inference/inference_patches.py` to obtain probability prediction at patch level
- Batch resample each probability patch into coarser resolution virtual rasters (vrt) with `inference/resample_patches.sh`
- Group each vrt into processing tiles using `inference/group_patches_to_tiles.py`.
- Run `inference/mosaic_tile.py` to create a mosaic based on patches
### Post-processing
- To apply non-arable land mask, run `postprocessing/mask.sh`
- To remove sieve pixels, run `postprocessing/sieve_removal.py`
- Convert probability mosaic raster(s)/tiles into polygon (geopackage) using `postprocessing/polygonize.py` 
- Simplify and smooth the vertices of each polygon feature using `postprocessing/smooth_polygon.py`.
