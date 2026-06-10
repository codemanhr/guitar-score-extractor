from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

from app.models.schemas import ScrollDirection


# ── Displacement estimation ──────────────────────────

def estimate_displacement_phase(
    prev: np.ndarray,
    curr: np.ndarray,
    max_shift: int = 200,
) -> tuple[float, float, float]:
    """Estimate (dx, dy, confidence) using phase correlation.
    Falls back to template matching when confidence is low."""
    # Phase correlation
    prev_f32 = prev.astype(np.float32)
    curr_f32 = curr.astype(np.float32)

    # Apply window to reduce edge effects
    h, w = prev.shape
    window = cv2.createHanningWindow((w, h), cv2.CV_32F)
    prev_w = prev_f32 * window
    curr_w = curr_f32 * window

    # Phase correlation
    (dx, dy), response = cv2.phaseCorrelate(prev_w, curr_w)
    confidence = float(response)

    # Clamp to max_shift
    dx = max(-max_shift, min(max_shift, dx))
    dy = max(-max_shift, min(max_shift, dy))

    # Confidence threshold — try template matching fallback
    if confidence < 0.05:
        return _estimate_displacement_template(prev, curr, max_shift)

    return (dx, dy, confidence)


def _estimate_displacement_template(
    prev: np.ndarray,
    curr: np.ndarray,
    max_shift: int = 200,
    edge_only: bool = True,
) -> tuple[float, float, float]:
    """Estimate displacement using edge-based template matching."""
    # Edge detection for robustness
    if edge_only:
        prev_e = cv2.Canny(prev, 50, 150)
        curr_e = cv2.Canny(curr, 50, 150)
    else:
        prev_e = prev
        curr_e = curr

    h, w = prev.shape
    # Use rightmost strip of prev as template (where new content should have appeared)
    strip_w = min(w // 3, 100)
    template = prev_e[:, -strip_w:]

    # Search in current frame
    result = cv2.matchTemplate(curr_e, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)

    # displacement = template_origin - match_origin
    # Template was at (w - strip_w, 0) in prev
    # Match is at max_loc in curr
    dx = (w - strip_w) - max_loc[0]

    dx = max(-max_shift, min(max_shift, dx))
    return (float(dx), 0.0, float(max_val))


# ── Stitch assembly ──────────────────────────────────

def estimate_scroll_direction(
    crop_paths: list[Path],
    sample_count: int = 10,
) -> str:
    """Auto-detect scroll direction from early frames."""
    if len(crop_paths) < 2:
        return "left"

    dx_sum = 0.0
    dy_sum = 0.0
    n = min(sample_count, len(crop_paths) - 1)

    for i in range(n):
        prev = cv2.imread(str(crop_paths[i]), cv2.IMREAD_GRAYSCALE)
        curr = cv2.imread(str(crop_paths[i + 1]), cv2.IMREAD_GRAYSCALE)
        if prev is None or curr is None:
            continue
        dx, dy, _ = estimate_displacement_phase(prev, curr)
        dx_sum += dx
        dy_sum += dy

    if abs(dx_sum) > abs(dy_sum):
        return "right" if dx_sum > 0 else "left"
    else:
        return "down" if dy_sum > 0 else "up"


def build_stitch(
    crop_paths: list[Path],
    scroll_direction: str = "left",
    invert: bool = False,
    threshold: str = "auto",
    max_shift: int = 200,
    confidence_threshold: float = 0.02,
    debug_dir: Optional[Path] = None,
    log_func=None,
) -> tuple[np.ndarray, list[dict]]:
    """Build a stitched long image from cropped frames.

    Returns (stitched_image, metadata_list).
    """
    if len(crop_paths) == 0:
        raise ValueError("No crop images to stitch")

    if scroll_direction == "auto":
        scroll_direction = estimate_scroll_direction(crop_paths)
        if log_func:
            log_func(f"Auto-detected scroll direction: {scroll_direction}")

    is_horizontal = scroll_direction in ("left", "right")

    # Read first frame
    img0 = cv2.imread(str(crop_paths[0]))
    if img0 is None:
        raise ValueError(f"Cannot read first crop image: {crop_paths[0]}")
    if len(img0.shape) == 3:
        img0 = cv2.cvtColor(img0, cv2.COLOR_BGR2GRAY)

    from app.services.image_preprocessor import preprocess_image
    img0_pp = preprocess_image(img0, do_invert=invert, threshold_method=threshold)

    h, w = img0_pp.shape

    # Initialise canvas (generous estimate: 10x scroll extent)
    total_length = w * len(crop_paths) if is_horizontal else h * len(crop_paths)
    if is_horizontal:
        canvas = np.zeros((h, total_length), dtype=np.uint8) + 255
        canvas[:, :w] = img0_pp
    else:
        canvas = np.zeros((total_length, w), dtype=np.uint8) + 255
        canvas[:h, :] = img0_pp

    cursor = w if is_horizontal else h
    prev_pp = img0_pp

    metadata: list[dict] = [
        {
            "frame_index": 0,
            "source": str(crop_paths[0].name),
            "displacement_px": 0.0,
            "confidence": 1.0,
            "canvas_position_px": 0,
            "flag": "first_frame",
        }
    ]

    for i in range(1, len(crop_paths)):
        curr = cv2.imread(str(crop_paths[i]))
        if curr is None:
            continue
        if len(curr.shape) == 3:
            curr = cv2.cvtColor(curr, cv2.COLOR_BGR2GRAY)
        curr_pp = preprocess_image(curr, do_invert=invert, threshold_method=threshold)

        dx, dy, confidence = estimate_displacement_phase(prev_pp, curr_pp, max_shift)

        if debug_dir:
            debug_frame = debug_dir / f"match_{i:06d}_conf_{confidence:.3f}.jpg"
            _save_debug_match(prev_pp, curr_pp, dx, dy, confidence, debug_frame)

        if confidence < confidence_threshold:
            meta_entry = {
                "frame_index": i,
                "source": str(crop_paths[i].name),
                "displacement_px": round(dx, 2),
                "confidence": round(confidence, 4),
                "canvas_position_px": cursor,
                "flag": "low_confidence_skipped",
            }
            metadata.append(meta_entry)
            if log_func:
                log_func(f"  Frame {i}: low confidence {confidence:.4f}, skipping")
            continue

        # Extract new content based on scroll direction
        if is_horizontal:
            abs_dx = abs(dx)
            append_w = max(0, int(round(abs_dx)))
            if append_w <= 0:
                meta_entry = {
                    "frame_index": i,
                    "source": str(crop_paths[i].name),
                    "displacement_px": round(dx, 2),
                    "confidence": round(confidence, 4),
                    "canvas_position_px": cursor,
                    "flag": "no_new_content",
                }
                metadata.append(meta_entry)
                continue

            if dx > 0:  # scrolling right, new content on left
                new_strip = curr_pp[:, :append_w]
            else:  # scrolling left, new content on right
                new_strip = curr_pp[:, -append_w:]

            # Extend canvas if needed
            if cursor + append_w > canvas.shape[1]:
                extend = max(canvas.shape[1] * 2, cursor + append_w + w)
                new_canvas = np.zeros((h, extend), dtype=np.uint8) + 255
                new_canvas[:, :cursor] = canvas[:, :cursor]
                canvas = new_canvas

            canvas[:, cursor:cursor + append_w] = new_strip
            cursor += append_w
        else:
            abs_dy = abs(dy)
            append_h = max(0, int(round(abs_dy)))
            if append_h <= 0:
                meta_entry = {
                    "frame_index": i,
                    "source": str(crop_paths[i].name),
                    "displacement_px": round(dy, 2),
                    "confidence": round(confidence, 4),
                    "canvas_position_px": cursor,
                    "flag": "no_new_content",
                }
                metadata.append(meta_entry)
                continue

            if dy > 0:  # scrolling down, new content at top
                new_strip = curr_pp[:append_h, :]
            else:  # scrolling up, new content at bottom
                new_strip = curr_pp[-append_h:, :]

            if cursor + append_h > canvas.shape[0]:
                extend = max(canvas.shape[0] * 2, cursor + append_h + h)
                new_canvas = np.zeros((extend, w), dtype=np.uint8) + 255
                new_canvas[:cursor, :] = canvas[:cursor, :]
                canvas = new_canvas

            canvas[cursor:cursor + append_h, :] = new_strip
            cursor += append_h

        meta_entry = {
            "frame_index": i,
            "source": str(crop_paths[i].name),
            "displacement_px": round((dx if is_horizontal else dy), 2),
            "confidence": round(confidence, 4),
            "canvas_position_px": cursor,
            "flag": "ok",
        }
        metadata.append(meta_entry)
        prev_pp = curr_pp

    # Trim canvas to actual content
    if is_horizontal:
        canvas = canvas[:, :cursor]
    else:
        canvas = canvas[:cursor, :]

    return (canvas, metadata)


def _save_debug_match(
    prev: np.ndarray,
    curr: np.ndarray,
    dx: float,
    dy: float,
    confidence: float,
    out_path: Path,
) -> None:
    """Save a debug visualisation showing overlap of two frames."""
    h, w = prev.shape
    debug = np.zeros((max(h, 128), w * 2 + 30, 3), dtype=np.uint8)

    prev_color = cv2.cvtColor(prev, cv2.COLOR_GRAY2BGR)
    curr_color = cv2.cvtColor(curr, cv2.COLOR_GRAY2BGR)

    debug[:h, :w] = prev_color
    debug[:h, w + 30:w + 30 + w] = curr_color
    cv2.putText(
        debug,
        f"dx={dx:.1f} dy={dy:.1f} conf={confidence:.3f}",
        (5, max(h, 128) - 5),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        (0, 0, 255),
        1,
    )
    cv2.imwrite(str(out_path), debug)


def save_stitch_result(
    canvas: np.ndarray,
    output_path: Path,
    metadata: list[dict],
    metadata_output_path: Optional[Path] = None,
) -> None:
    """Save the stitched image and optional metadata JSON."""
    cv2.imwrite(str(output_path), canvas)
    if metadata_output_path:
        with open(metadata_output_path, "w") as f:
            json.dump(metadata, f, indent=2)
