from __future__ import annotations

import subprocess
from pathlib import Path


def extract_preview_frame(
    video_path: str | Path,
    output_path: str | Path,
    time_sec: float = 0.0,
    width: int | None = None,
) -> None:
    """Extract a single frame from the video at the specified time."""
    cmd = [
        "ffmpeg",
        "-y",
        "-ss", str(time_sec),
        "-i", str(video_path),
        "-vframes", "1",
    ]
    if width is not None:
        cmd += ["-vf", f"scale={width}:-1"]
    cmd.append(str(output_path))
    subprocess.run(cmd, capture_output=True, check=True)


def extract_frames(
    video_path: str | Path,
    output_dir: str | Path,
    sample_fps: float = 3.0,
    start_time: float = 0.0,
    end_time: float | None = None,
    max_frames: int | None = None,
) -> list[Path]:
    """Extract frames at the specified sample rate. Returns sorted list of frame paths."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg",
        "-y",
        "-ss", str(start_time),
        "-i", str(video_path),
        "-vf", f"fps={sample_fps}",
        "-frame_pts", "1",
        "-qscale:v", "2",
    ]
    if end_time is not None:
        cmd += ["-to", str(end_time)]
    if max_frames is not None:
        cmd += ["-vframes", str(max_frames)]
    cmd.append(str(output_dir / "frame_%010d.jpg"))

    subprocess.run(cmd, capture_output=True, check=True)

    frames = sorted(output_dir.glob("frame_*.jpg"), key=lambda p: p.name)
    return frames


def clear_frames(output_dir: str | Path) -> None:
    output_dir = Path(output_dir)
    for f in output_dir.iterdir():
        if f.is_file():
            f.unlink()
