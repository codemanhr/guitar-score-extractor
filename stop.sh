#!/bin/bash
echo "🛑 停止中..."
kill $(lsof -ti :8000) 2>/dev/null
kill $(lsof -ti :5173) 2>/dev/null
echo "✅ 已全部停止"
