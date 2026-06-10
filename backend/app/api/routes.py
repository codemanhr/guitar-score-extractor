from __future__ import annotations

import time
from pathlib import Path
import threading

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.models.schemas import (
    ImageResponse,
    PDFConfig,
    ProcessingConfig,
    ProjectConfig,
    ProjectInfo,
    ROI,
    TaskProgress,
    TaskStatus,
    VideoInfo,
)
from app.services.frame_extractor import extract_preview_frame, extract_frames, clear_frames
from app.services.image_preprocessor import batch_preprocess, deduplicate_frames
from app.services.pdf_exporter import export_pdf, export_pdf_grid
from app.services.roi_cropper import batch_crop
from app.services.video_service import get_video_info
from app.storage import manager as storage


router = APIRouter()

# ── In-memory task progress store ────────────────────
_tasks: dict[str, TaskProgress] = {}
_processing_lock: set[str] = set()


def _log(project_id: str, msg: str) -> None:
    if project_id in _tasks:
        _tasks[project_id].log.append(msg)


# ── Health ────────────────────────────────────────────

@router.get("/health")
def health():
    return {"status": "ok"}


# ── Projects ──────────────────────────────────────────

@router.get("/projects")
def list_projects():
    return storage.list_projects()


@router.post("/projects")
def create_project():
    project_id = storage.create_project()
    config = storage.read_config(project_id)
    return {"id": project_id, "config": config}


@router.get("/projects/{project_id}")
def get_project(project_id: str):
    config = storage.read_config(project_id)
    if config is None:
        raise HTTPException(404, "Project not found")
    return {"id": project_id, "config": config}


@router.delete("/projects/{project_id}")
def delete_project(project_id: str):
    if not storage.delete_project(project_id):
        raise HTTPException(404, "Project not found")
    return {"status": "deleted"}


# ── Video upload ──────────────────────────────────────

@router.post("/projects/{project_id}/upload")
async def upload_video(project_id: str, file: UploadFile = File(...)):
    config = storage.read_config(project_id)
    if config is None:
        raise HTTPException(404, "Project not found")

    dest = storage.source_store_path(project_id, file.filename or "video.mp4")
    content = await file.read()
    with open(dest, "wb") as f:
        f.write(content)

    # Read video info
    info = get_video_info(dest)
    config.source_video = str(dest)
    config.video = info
    storage.update_config(project_id, config)

    return {"video_info": info}


# ── Video info ────────────────────────────────────────

@router.get("/projects/{project_id}/video-info")
def video_info(project_id: str):
    config = storage.read_config(project_id)
    if config is None:
        raise HTTPException(404, "Project not found")
    if not config.source_video or not Path(config.source_video).exists():
        raise HTTPException(400, "No video uploaded")
    info = get_video_info(config.source_video)
    config.video = info
    storage.update_config(project_id, config)
    return {"video_info": info}


# ── Preview frame ─────────────────────────────────────

@router.get("/projects/{project_id}/preview")
def get_preview_frame(project_id: str, time_sec: float = 0.0, width: int = 800):
    config = storage.read_config(project_id)
    if config is None:
        raise HTTPException(404, "Project not found")
    if not config.source_video or not Path(config.source_video).exists():
        raise HTTPException(400, "No video uploaded")

    out = storage.output_path(project_id, "preview.jpg")
    extract_preview_frame(config.source_video, out, time_sec=time_sec, width=width)
    return FileResponse(str(out), media_type="image/jpeg")


# ── ROI ────────────────────────────────────────────────

@router.post("/projects/{project_id}/roi")
def set_roi(project_id: str, roi: ROI):
    config = storage.read_config(project_id)
    if config is None:
        raise HTTPException(404, "Project not found")
    config.roi = roi
    storage.update_config(project_id, config)
    return {"roi": roi}


@router.get("/projects/{project_id}/roi")
def get_roi(project_id: str):
    config = storage.read_config(project_id)
    if config is None:
        raise HTTPException(404, "Project not found")
    if config.roi is None:
        raise HTTPException(404, "ROI not set")
    return {"roi": config.roi}


# ── Processing Config ─────────────────────────────────

@router.post("/projects/{project_id}/config")
def set_processing_config(project_id: str, processing: ProcessingConfig):
    config = storage.read_config(project_id)
    if config is None:
        raise HTTPException(404, "Project not found")
    config.processing = processing
    storage.update_config(project_id, config)
    return {"processing": processing}


@router.post("/projects/{project_id}/pdf-config")
def set_pdf_config(project_id: str, pdf: PDFConfig):
    config = storage.read_config(project_id)
    if config is None:
        raise HTTPException(404, "Project not found")
    config.pdf = pdf
    storage.update_config(project_id, config)
    return {"pdf": pdf}


# ── Process pipeline ──────────────────────────────────

@router.post("/projects/{project_id}/process")
def start_processing(project_id: str):
    config = storage.read_config(project_id)
    if config is None:
        raise HTTPException(404, "Project not found")
    if config.roi is None:
        raise HTTPException(400, "ROI not set")
    if not config.source_video or not Path(config.source_video).exists():
        raise HTTPException(400, "No video uploaded")
    if project_id in _processing_lock:
        raise HTTPException(409, "Processing already in progress")

    _processing_lock.add(project_id)
    _tasks[project_id] = TaskProgress(
        project_id=project_id,
        status=TaskStatus.pending,
        log=["Processing started"],
    )

    # Run pipeline in background thread so server stays responsive
    thread = threading.Thread(
        target=_run_pipeline_wrapper,
        args=(project_id, config),
        daemon=True,
    )
    thread.start()

    return _tasks[project_id]


def _run_pipeline_wrapper(project_id: str, config: ProjectConfig) -> None:
    """Wrapper that runs the pipeline and handles cleanup."""
    try:
        _run_pipeline(project_id, config)
    except Exception as e:
        _tasks[project_id].status = TaskStatus.failed
        _tasks[project_id].log.append(f"ERROR: {e}")
        _tasks[project_id].output_files = []
    finally:
        _processing_lock.discard(project_id)

def _run_pipeline(project_id: str, config: ProjectConfig) -> None:
    task = _tasks[project_id]
    source = config.source_video
    proc = config.processing

    # Extract frames
    task.status = TaskStatus.extracting_frames
    task.current_stage = "Extracting frames"
    frame_dir = storage.frames_dir(project_id)
    clear_frames(frame_dir)
    frame_paths = extract_frames(
        source, frame_dir,
        sample_fps=proc.sample_fps,
        start_time=proc.start_time,
        end_time=proc.end_time,
        max_frames=proc.max_frames,
    )
    task.total_frames = len(frame_paths)
    task.log.append(f"Extracted {len(frame_paths)} frames")

    if len(frame_paths) == 0:
        raise ValueError("No frames extracted")

    # Crop ROI
    task.status = TaskStatus.cropping
    task.current_stage = "Cropping ROI"
    crop_dir = storage.crops_dir(project_id)
    crop_paths = batch_crop(frame_paths, config.roi, crop_dir, save_debug=True)
    task.current_frame = len(crop_paths)
    task.progress_pct = 20.0
    task.log.append(f"Cropped {len(crop_paths)} frames")

    if len(crop_paths) == 0:
        raise ValueError("No crops generated")

    # Deduplicate near-identical frames
    task.current_stage = "去重"
    unique_count = len(crop_paths)
    crop_paths = deduplicate_frames(crop_paths)
    task.log.append(f"After dedup: {len(crop_paths)} / {unique_count} unique frames")


    # Generate PDF from frames (grid layout)
    task.status = TaskStatus.rendering_pdf
    task.current_stage = "排布页面"
    pdf_path = storage.output_path(project_id, "output.pdf")
    export_pdf_grid(
        crop_paths, pdf_path,
        page_size=config.pdf.page_size.value,
        orientation=config.pdf.orientation.value,
        margin_mm=config.pdf.margin_mm,
    )
    task.progress_pct = 100.0
    task.output_files = [str(pdf_path)]
    task.status = TaskStatus.completed
    task.current_stage = "已完成"
    task.log.append("PDF exported successfully")
    task.current_stage = "Completed"
    task.log.append("PDF exported successfully")
    task.log.append(f"Output files: {', '.join(str(p) for p in task.output_files)}")


# ── Task progress ─────────────────────────────────────

@router.get("/projects/{project_id}/progress")
def get_progress(project_id: str):
    if project_id not in _tasks:
        raise HTTPException(404, "No task found for this project")
    return _tasks[project_id]


# ── Download output files ─────────────────────────────

@router.get("/projects/{project_id}/output/{filename}")
def download_output(project_id: str, filename: str):
    fpath = storage.output_path(project_id, filename)
    if not fpath.exists():
        raise HTTPException(404, "File not found")
    return FileResponse(str(fpath))




@router.get("/projects/{project_id}/download-pdf")
def download_pdf(project_id: str):
    fpath = storage.output_path(project_id, "output.pdf")
    if not fpath.exists():
        raise HTTPException(404, "PDF not found; run processing first")
    return FileResponse(str(fpath), media_type="application/pdf", filename="score.pdf")
