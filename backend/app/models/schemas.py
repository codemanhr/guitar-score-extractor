from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ScrollDirection(str, Enum):
    auto = "auto"
    left = "left"
    right = "right"
    up = "up"
    down = "down"


class TaskStatus(str, Enum):
    pending = "pending"
    extracting_frames = "extracting_frames"
    cropping = "cropping"
    preprocessing = "preprocessing"
    stitching = "stitching"
    rendering_pdf = "rendering_pdf"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class PageSize(str, Enum):
    A4 = "A4"
    letter = "letter"


class PageOrientation(str, Enum):
    portrait = "portrait"
    landscape = "landscape"


class VideoInfo(BaseModel):
    width: int
    height: int
    fps: float
    duration: float
    frame_count: int
    codec: str = ""


class ROI(BaseModel):
    x: int
    y: int
    width: int
    height: int


class ProcessingConfig(BaseModel):
    sample_fps: float = 1.0
    start_time: float = 0.0
    end_time: Optional[float] = None
    max_frames: Optional[int] = None
    scroll_direction: ScrollDirection = ScrollDirection.left
    invert: bool = False
    threshold: str = "auto"


class PDFConfig(BaseModel):
    page_size: PageSize = PageSize.A4
    orientation: PageOrientation = PageOrientation.portrait
    margin_mm: float = 10.0


class ProjectConfig(BaseModel):
    source_video: str
    video: Optional[VideoInfo] = None
    roi: Optional[ROI] = None
    processing: ProcessingConfig = Field(default_factory=ProcessingConfig)
    pdf: PDFConfig = Field(default_factory=PDFConfig)


class TaskProgress(BaseModel):
    project_id: str
    status: TaskStatus
    progress_pct: float = 0.0
    current_frame: int = 0
    total_frames: int = 0
    current_stage: str = ""
    log: list[str] = []
    output_files: list[str] = []


class ProjectInfo(BaseModel):
    id: str
    config: ProjectConfig
    created_at: str = ""
    updated_at: str = ""


class ImageResponse(BaseModel):
    filename: str
    url: str
