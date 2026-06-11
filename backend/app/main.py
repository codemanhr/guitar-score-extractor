from __future__ import annotations

import shutil
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router


# ── Dependency check ──
def _check_dependencies():
    missing = []
    for cmd in ("ffmpeg", "ffprobe"):
        if shutil.which(cmd) is None:
            missing.append(cmd)
    if missing:
        print(
            f"❌ 缺少系统依赖: {', '.join(missing)}",
            file=sys.stderr,
        )
        print("   安装方法:", file=sys.stderr)
        print("   macOS:  brew install ffmpeg", file=sys.stderr)
        print("   Ubuntu: sudo apt install ffmpeg", file=sys.stderr)
        sys.exit(1)
    else:
        print("✅ 系统依赖检查通过 (ffmpeg / ffprobe)")


_check_dependencies()


app = FastAPI(title="Guitar Score Extraction API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
