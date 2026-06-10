from __future__ import annotations
import numpy as np

import io
import tempfile
from pathlib import Path

import cv2
import img2pdf
from PIL import Image as PILImage

from app.models.schemas import PageSize, PageOrientation


# Page dimensions in mm
PAGE_SIZES = {
    "A4": (210, 297),
    "letter": (215.9, 279.4),
}


def _mm_to_pt(mm: float) -> float:
    return mm * 72.0 / 25.4


def _mm_to_px(mm: float, dpi: int = 150) -> int:
    """Convert mm to pixels at given DPI."""
    return int(mm * dpi / 25.4)


def _split_vertical(
    img: np.ndarray,
    page_w_px: int,
    page_h_px: int,
    scale_factor: float,
    output_dir: Path,
) -> list[Path]:
    """Split a tall image (vertical scroll) into page-height chunks, top to bottom."""
    img_h, img_w = img.shape
    scaled_w = int(img_w * scale_factor)
    scaled_h = int(img_h * scale_factor)
    scaled = cv2.resize(img, (scaled_w, scaled_h), interpolation=cv2.INTER_LANCZOS4)

    pages: list[Path] = []
    y = 0
    page_num = 0
    while y < scaled_h:
        h_remaining = scaled_h - y
        h_this = min(page_h_px, h_remaining)

        page_img = 255 * np.ones((int(page_h_px), int(page_w_px)), dtype=np.uint8)
        content = scaled[y:y + int(h_this), :]
        content_h, content_w = content.shape
        x_offset = (int(page_w_px) - content_w) // 2
        page_img[:content_h, x_offset:x_offset + content_w] = content

        page_path = output_dir / f"page_{page_num:04d}.png"
        cv2.imwrite(str(page_path), page_img)
        pages.append(page_path)
        y += int(h_this)
        page_num += 1

    return pages


def _split_horizontal(
    img: np.ndarray,
    page_w_px: int,
    page_h_px: int,
    scale_factor: float,
    output_dir: Path,
) -> list[Path]:
    """Split a wide image (horizontal scroll) into page-width chunks, left to right."""
    img_h, img_w = img.shape
    scaled_w = int(img_w * scale_factor)
    scaled_h = int(img_h * scale_factor)
    scaled = cv2.resize(img, (scaled_w, scaled_h), interpolation=cv2.INTER_LANCZOS4)

    # Trim leading blank columns (white/empty space before content starts)
    col_mean = scaled.mean(axis=0)  # average brightness per column
    threshold = 250  # columns brighter than this (out of 255) are blank
    non_blank = np.where(col_mean < threshold)[0]
    start_x = int(non_blank[0]) if len(non_blank) > 0 else 0


    pages: list[Path] = []
    x = 0
    x = start_x
    page_num = 0
    while x < scaled_w:
        w_remaining = scaled_w - x
        w_this = min(page_w_px, w_remaining)

        page_img = 255 * np.ones((int(page_h_px), int(page_w_px)), dtype=np.uint8)
        content = scaled[:, x:x + int(w_this)]
        content_h, content_w = content.shape
        y_offset = (int(page_h_px) - content_h) // 2
        page_img[y_offset:y_offset + content_h, :content_w] = content

        page_path = output_dir / f"page_{page_num:04d}.png"
        cv2.imwrite(str(page_path), page_img)
        pages.append(page_path)
        x += int(w_this)
        page_num += 1

    return pages


def export_pdf_grid(
    frame_paths: list[Path],
    output_path: str | Path,
    page_size: str = "A4",
    orientation: str = "portrait",
    margin_mm: float = 10.0,
    dpi: int = 150,
) -> Path:
    """Place preprocessed frame images onto A4 pages in rows, wrapping naturally.

    Each frame is scaled to fit the page width and placed as a row.
    Rows stack vertically; when a page fills up, a new page starts.
    """
    pw_mm, ph_mm = PAGE_SIZES.get(page_size, PAGE_SIZES["A4"])
    if orientation == "landscape":
        pw_mm, ph_mm = ph_mm, pw_mm

    margin_px = _mm_to_px(margin_mm, dpi)
    page_w_px = _mm_to_px(pw_mm) - 2 * margin_px
    page_h_px = _mm_to_px(ph_mm) - 2 * margin_px

    gap = 4  # pixels between rows

    pages: list[np.ndarray] = []
    current_page = 255 * np.ones((page_h_px, page_w_px, 3), dtype=np.uint8)
    y = 0

    for frame_path in frame_paths:
        img = cv2.imread(str(frame_path))
        if img is None:
            continue

        h, w = img.shape[:2]

        # Scale to fit page width
        scale_ratio = page_w_px / w
        new_w = int(w * scale_ratio)
        new_h = int(h * scale_ratio)
        scaled = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)

        # Check if we need a new page
        if y + new_h + gap > page_h_px:
            pages.append(current_page)
            current_page = 255 * np.ones((page_h_px, page_w_px, 3), dtype=np.uint8)
            y = 0

        # Place the image
        current_page[y:y+new_h, :new_w] = scaled
        y += new_h + gap

    # Add remaining page
    if y > 0:
        pages.append(current_page)

    # Save pages as images
    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)

    page_paths = []
    for i, page in enumerate(pages):
        page_path = output_dir / f"page_{i:04d}.png"
        cv2.imwrite(str(page_path), page)
        page_paths.append(page_path)

    # Convert to PDF
    layout = img2pdf.get_layout_fun((pw_mm, ph_mm))
    with open(output_path, "wb") as f:
        f.write(
            img2pdf.convert(
                [str(p) for p in page_paths],
                layout_fun=layout,
            )
        )

    return Path(output_path)



def split_long_image(
    image_path: str | Path,
    page_size: str = "A4",
    orientation: str = "portrait",
    margin_mm: float = 10.0,
    scale: float = 1.0,
    dpi: int = 150,
    output_dir: str | Path | None = None,
) -> list[Path]:
    """Split a long stitched image into page-sized chunks.

    For horizontal scroll (wide image): scale to fill page height, split left-to-right.
    For vertical scroll (tall image):   scale to fill page width,  split top-to-bottom.
    The `scale` parameter is a multiplier on the fill-to-page baseline.
    """
    img = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValueError(f"Cannot read image: {image_path}")

    img_h, img_w = img.shape

    pw_mm, ph_mm = PAGE_SIZES.get(page_size, PAGE_SIZES["A4"])
    if orientation == "landscape":
        pw_mm, ph_mm = ph_mm, pw_mm

    margin_px = _mm_to_px(margin_mm, dpi)
    page_w_px = _mm_to_px(pw_mm) - 2 * margin_px
    page_h_px = _mm_to_px(ph_mm) - 2 * margin_px

    out_dir = Path(output_dir) if output_dir else Path(image_path).parent
    out_dir.mkdir(parents=True, exist_ok=True)

    if img_w > img_h:
        # Horizontal scroll — scale to fill page height, split left-to-right
        scale_factor = scale
        return _split_horizontal(img, page_w_px, page_h_px, scale_factor, out_dir)
    else:
        # Vertical scroll — scale to fill page width, split top-to-bottom
        scale_factor = scale
        return _split_vertical(img, page_w_px, page_h_px, scale_factor, out_dir)


def export_pdf(
    image_path: str | Path,
    output_path: str | Path,
    page_size: str = "A4",
    orientation: str = "portrait",
    margin_mm: float = 10.0,
    scale: float = 1.0,
    dpi: int = 150,
) -> Path:
    """Export a stitched image to PDF using img2pdf."""
    pages = split_long_image(
        image_path=image_path,
        page_size=page_size,
        orientation=orientation,
        margin_mm=margin_mm,
        scale=scale,
        dpi=dpi,
    )

    pw_mm, ph_mm = PAGE_SIZES.get(page_size, PAGE_SIZES["A4"])
    if orientation == "landscape":
        pw_mm, ph_mm = ph_mm, pw_mm

    layout = img2pdf.get_layout_fun((pw_mm, ph_mm))

    with open(output_path, "wb") as f:
        f.write(
            img2pdf.convert(
                [str(p) for p in pages],
                layout_fun=layout,
            )
        )

    return Path(output_path)


def export_pdf_pil(
    image_path: str | Path,
    output_path: str | Path,
    page_size: str = "A4",
    orientation: str = "portrait",
    margin_mm: float = 10.0,
    scale: float = 1.0,
) -> Path:
    """Alternative PDF export using Pillow (no external deps beyond PIL)."""
    pages = split_long_image(
        image_path=image_path,
        page_size=page_size,
        orientation=orientation,
        margin_mm=margin_mm,
        scale=scale,
        dpi=150,
    )

    pil_images = []
    for p in pages:
        pil_img = PILImage.open(p).convert("L")
        pil_images.append(pil_img)

    first = pil_images[0]
    rest = pil_images[1:] if len(pil_images) > 1 else None
    first.save(
        output_path,
        save_all=True,
        append_images=rest,
        quality=95,
    )

    return Path(output_path)
