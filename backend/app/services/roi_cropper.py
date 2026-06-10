from __future__ import annotations

import cv2
import numpy as np
from pathlib import Path

from app.models.schemas import ROI


def crop_roi(frame_path: str | Path, roi: ROI) -> np.ndarray:
    """Crop a single frame to the ROI region. Returns the cropped image array."""
    img = cv2.imread(str(frame_path))
    if img is None:
        raise ValueError(f"Cannot read frame: {frame_path}")
    h, w = img.shape[:2]
    x1 = max(0, roi.x)
    y1 = max(0, roi.y)
    x2 = min(w, roi.x + roi.width)
    y2 = min(h, roi.y + roi.height)
    if x2 <= x1 or y2 <= y1:
        raise ValueError(f"ROI {roi} is outside frame dimensions ({w}x{h})")
    return img[y1:y2, x1:x2]


def batch_crop(
    frame_paths: list[Path],
    roi: ROI,
    output_dir: Path,
    save_debug: bool = False,
) -> list[Path]:
    """Crop all frames to ROI and save to output_dir. Returns list of cropped paths."""
    output_dir.mkdir(parents=True, exist_ok=True)
    cropped_paths = []
    debug_dir = output_dir.parent / "debug" if save_debug else None
    if debug_dir:
        debug_dir.mkdir(parents=True, exist_ok=True)

    for i, fpath in enumerate(frame_paths):
        try:
            cropped = crop_roi(fpath, roi)
            out_path = output_dir / f"crop_{i:06d}.jpg"
            cv2.imwrite(str(out_path), cropped)
            cropped_paths.append(out_path)
        except Exception as e:
            print(f"  [cropper] Skipping {fpath.name}: {e}")
            continue

    return cropped_paths
