from __future__ import annotations

import cv2
import numpy as np
from pathlib import Path
from typing import Optional


def to_grayscale(img: np.ndarray) -> np.ndarray:
    if len(img.shape) == 3:
        return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return img


def enhance_contrast(img: np.ndarray) -> np.ndarray:
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return clahe.apply(img)


def threshold_image(
    img: np.ndarray,
    method: str = "auto",
    block_size: int = 31,
    c: int = 10,
) -> np.ndarray:
    if method == "auto":
        return cv2.adaptiveThreshold(
            img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, block_size, c,
        )
    elif method == "otsu":
        _, binary = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return binary
    else:
        try:
            thresh_val = int(method)
            _, binary = cv2.threshold(img, thresh_val, 255, cv2.THRESH_BINARY)
            return binary
        except (ValueError, TypeError):
            _, binary = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            return binary


def denoise(img: np.ndarray) -> np.ndarray:
    return cv2.fastNlMeansDenoising(img, h=10)


def sharpen(img: np.ndarray) -> np.ndarray:
    kernel = np.array([[-1, -1, -1],
                       [-1,  9, -1],
                       [-1, -1, -1]])
    return cv2.filter2D(img, -1, kernel)


def invert(img: np.ndarray) -> np.ndarray:
    return cv2.bitwise_not(img)


def preprocess_image(
    img: np.ndarray,
    do_grayscale: bool = True,
    do_contrast: bool = True,
    do_denoise: bool = True,
    do_sharpen: bool = True,
    do_invert: bool = False,
    threshold_method: str = "auto",
) -> np.ndarray:
    if do_grayscale:
        img = to_grayscale(img)
    if do_contrast:
        img = enhance_contrast(img)
    if do_denoise:
        img = denoise(img)
    if do_sharpen:
        img = sharpen(img)
    img = threshold_image(img, method=threshold_method)
    if do_invert:
        img = invert(img)
    return img


def batch_preprocess(
    image_paths: list[Path],
    output_dir: Path,
    invert: bool = False,
    threshold: str = "auto",
) -> list[Path]:
    """Preprocess cropped frames with noise reduction.
    Skips contrast enhancement and sharpening which amplify noise/speckles.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    processed_paths = []
    for i, fpath in enumerate(image_paths):
        img = cv2.imread(str(fpath))
        if img is None:
            continue
        # Clean pipeline: gray -> strong denoise -> threshold
        gray = to_grayscale(img)
        denoised = cv2.fastNlMeansDenoising(
            gray, h=30, templateWindowSize=7, searchWindowSize=21,
        )
        binary = threshold_image(denoised, method=threshold)
        if invert:
            binary = invert(binary)
        out_path = output_dir / f"prep_{i:06d}.png"
        cv2.imwrite(str(out_path), binary)
        processed_paths.append(out_path)
    return processed_paths
def deduplicate_frames(
    frame_paths: list[Path],
    threshold_pct: float = 0.2,
    top_crop: float = 0.2,
    bottom_crop: float = 0.9,
) -> list[Path]:
    """Remove near-duplicate frames.
    Uses fixed threshold + dilation to remove thin cursor lines,
    then compares pixel difference in the dynamic content region
    (excludes static headers, top 20%% by default).
    """
    if len(frame_paths) <= 1:
        return frame_paths

    kernel = np.ones((3, 3), np.uint8)

    def _prepare(p: Path) -> np.ndarray:
        img = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
        _, binary = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return cv2.dilate(binary, kernel, iterations=1)

    result = [frame_paths[0]]
    prev = _prepare(frame_paths[0])
    h = prev.shape[0]
    y0, y1 = int(h * top_crop), int(h * bottom_crop)

    for path in frame_paths[1:]:
        curr = _prepare(path)
        diff = cv2.absdiff(prev[y0:y1], curr[y0:y1])
        changed_pct = float(np.mean(diff > 30)) * 100
        if changed_pct > threshold_pct:
            result.append(path)
            prev = curr

    return result

