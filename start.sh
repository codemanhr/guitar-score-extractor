#!/bin/bash
# Guitar Score Extractor — 一键启动
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "🚀 启动后端..."
cd "$ROOT_DIR/backend"
nohup "$ROOT_DIR/backend/.venv/bin/python" -m uvicorn app.main:app \
  --host 127.0.0.1 --port 8000 --reload \
  > /tmp/gse-backend.log 2>&1 &
echo "   PID $! → http://127.0.0.1:8000"

echo "🚀 启动前端..."
cd "$ROOT_DIR/frontend"
nohup npx vite --port 5173 \
  > /tmp/gse-frontend.log 2>&1 &
echo "   PID $! → http://localhost:5173"

sleep 3
echo ""
echo "✅ 全部启动完成"
echo "   前端: http://localhost:5173"
echo "   后端: http://127.0.0.1:8000"
echo "   日志: tail -f /tmp/gse-{backend,frontend}.log"
