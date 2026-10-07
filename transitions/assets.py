"""
transitions/assets.py - Spatial transition mask images (PNG threshold maps).

Pure asset loader with no dependency on the rest of the project, so it can move
into the sealed `transitions/` package unchanged. Lazy: images load on first use.
"""
import glob
import logging
import os

import numpy as np
from PIL import Image

logger = logging.getLogger("transitions.assets")

spatial_images = {}
_images_loaded = False


def load_spatial_images() -> None:
    """Load every assets/transitions/*.png once into `spatial_images` as (X, Y) float maps."""
    global _images_loaded
    if _images_loaded:
        return
    _images_loaded = True
    assets_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'assets', 'transitions'))
    if not os.path.exists(assets_dir):
        logger.warning(f"Spatial transition folder not found at {assets_dir}")
        return

    png_files = glob.glob(os.path.join(assets_dir, "*.png"))
    for file_path in png_files:
        name = os.path.splitext(os.path.basename(file_path))[0]
        try:
            img = Image.open(file_path).convert('L')
            # np.array(img) has shape (height, width); transpose gives (X, Y) to match coords
            arr = np.array(img).T.astype(np.float32) / 255.0
            spatial_images[name] = arr
            logger.debug(f"Loaded spatial transition image: {name}")
        except Exception as e:
            logger.error(f"Failed to load spatial image {file_path}: {e}")
