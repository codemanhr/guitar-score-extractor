from __future__ import annotations

import json
import shutil
import time
import uuid
from pathlib import Path
from typing import Optional

from app.models.schemas import ProjectConfig, ProjectInfo


STORAGE_ROOT = Path(__file__).resolve().parent.parent.parent.parent / "storage" / "projects"


def _project_dir(project_id: str) -> Path:
    return STORAGE_ROOT / project_id


def _ensure_dirs(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def create_project() -> str:
    project_id = uuid.uuid4().hex[:12]
    d = _project_dir(project_id)
    _ensure_dirs(d / "source")
    _ensure_dirs(d / "frames")
    _ensure_dirs(d / "crops")
    _ensure_dirs(d / "debug")
    config = ProjectConfig(source_video="")
    _write_config(project_id, config)
    return project_id


def _config_path(project_id: str) -> Path:
    return _project_dir(project_id) / "project.json"


def _write_config(project_id: str, config: ProjectConfig) -> None:
    data = config.model_dump(mode="json")
    data["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with open(_config_path(project_id), "w") as f:
        json.dump(data, f, indent=2)


def read_config(project_id: str) -> Optional[ProjectConfig]:
    p = _config_path(project_id)
    if not p.exists():
        return None
    with open(p) as f:
        return ProjectConfig(**json.load(f))


def update_config(project_id: str, config: ProjectConfig) -> None:
    _write_config(project_id, config)


def list_projects() -> list[ProjectInfo]:
    results = []
    if not STORAGE_ROOT.exists():
        return results
    for d in STORAGE_ROOT.iterdir():
        if d.is_dir():
            cfg = read_config(d.name)
            if cfg is not None:
                created = d.stat().st_ctime
                results.append(
                    ProjectInfo(
                        id=d.name,
                        config=cfg,
                        created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(created)),
                    )
                )
    return results


def delete_project(project_id: str) -> bool:
    d = _project_dir(project_id)
    if d.exists():
        shutil.rmtree(d)
        return True
    return False


def source_path(project_id: str) -> Path:
    d = _project_dir(project_id)
    # Find the first video file in source/
    for ext in (".mp4", ".mov", ".avi", ".mkv", ".webm"):
        candidates = list(d.glob(f"source/*{ext}"))
        if candidates:
            return candidates[0]
    return d / "source" / "video.mp4"


def frames_dir(project_id: str) -> Path:
    return _project_dir(project_id) / "frames"


def crops_dir(project_id: str) -> Path:
    return _project_dir(project_id) / "crops"


def debug_dir(project_id: str) -> Path:
    return _project_dir(project_id) / "debug"


def output_path(project_id: str, filename: str) -> Path:
    return _project_dir(project_id) / filename


def source_store_path(project_id: str, filename: str) -> Path:
    d = _project_dir(project_id) / "source"
    _ensure_dirs(d)
    return d / filename
