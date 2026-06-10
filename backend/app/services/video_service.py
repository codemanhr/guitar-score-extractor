from __future__ import annotations

import json as json_lib
import subprocess
from pathlib import Path

from app.models.schemas import VideoInfo


def get_video_info(video_path: str | Path) -> VideoInfo:
    """Read video metadata via ffprobe."""
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_streams",
        "-show_format",
        str(video_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    data = json_lib.loads(result.stdout)

    video_stream = None
    for s in data.get("streams", []):
        if s["codec_type"] == "video":
            video_stream = s
            break

    if video_stream is None:
        raise ValueError("No video stream found")

    width = int(video_stream.get("width", 0))
    height = int(video_stream.get("height", 0))
    fps_str = video_stream.get("r_frame_rate", "30/1")
    num, den = fps_str.split("/")
    fps = float(num) / float(den) if float(den) != 0 else 30.0
    duration = float(video_stream.get("duration", data.get("format", {}).get("duration", 0)))
    codec = video_stream.get("codec_name", "")

    frame_count = int(duration * fps)

    return VideoInfo(
        width=width,
        height=height,
        fps=round(fps, 3),
        duration=round(duration, 3),
        frame_count=frame_count,
        codec=codec,
    )
