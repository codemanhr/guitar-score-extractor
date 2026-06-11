# Guitar Score Extractor

从吉他演奏视频中自动提取滚动曲谱并生成 PDF 的工具。

上传一段吉他谱演奏视频（如 YouTube 上的 Guitar Boogie 类视频），它会自动提取视频帧、裁剪到乐谱区域、去重相似帧、并将曲谱排布到 A4 页面上，最终生成一个可直接打印的 PDF 文件。

## 功能

- **视频帧提取** — 以可调帧率提取视频中的曲谱画面
- **ROI 选择** — 在预览图上拖拽选择乐谱区域
- **智能去重** — 自动识别并跳过近乎相同的帧，消除演奏进度光标的干扰
- **PDF 导出** — 去重后的帧自动排布到 A4 页面，自适应宽度
- **实时进度** — 前端实时显示处理进度和日志

## 技术栈

| 层 | 技术 |
|---|------|
| 前端 | React 18 + TypeScript + Vite |
| 后端 | Python 3.9+ + FastAPI + OpenCV |
| 依赖 | ffmpeg(视频处理) + img2pdf(PDF生成) |

## 快速开始

### 环境要求

- Python 3.9+
- Node.js 18+
- ffmpeg（需要安装并在 PATH 中可用）

### 安装

```bash
# 1. 克隆仓库
git clone <your-repo-url>
cd <repo-folder>  # 替换为你克隆后的目录名

# 2. 安装后端
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. 安装前端
cd ../frontend
# 建议在 CI/可重复环境中使用 `npm ci`
npm ci

# macOS 安装 ffmpeg（如需）
# brew install ffmpeg

# Ubuntu / Debian:
# sudo apt update && sudo apt install -y ffmpeg
```

### 运行

**方式一：分终端运行**

```bash
# 终端 1：启动后端
cd backend
source .venv/bin/activate
python3 -m app.main
# 后端运行在 http://127.0.0.1:8000

# 终端 2：启动前端
cd frontend
npm run dev
# 前端运行在 http://localhost:5173
```

**方式二：后端前台运行（带热重载）**

```bash
cd backend && source .venv/bin/activate && python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

打开浏览器访问 `http://localhost:5173`。

### 一键快速运行（复制粘贴）

下面的命令在 macOS / Linux 上可用于快速在两个终端启动项目：

```bash
# 终端 A（后端）
cd <repo-folder>/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 -m app.main

# 终端 B（前端）
cd <repo-folder>/frontend
npm ci
npm run dev
```

将 `<repo-folder>` 替换为你实际的仓库目录名（`git clone` 后生成的目录）。

## 使用指南

1. **上传视频** — 点击页面上方的"导入视频"按钮选择 mp4 文件
2. **选择 ROI** — 上传后在预览图上拖拽，框选乐谱区域
3. **调整参数** — 右侧面板可调整采样帧率等参数
4. **开始处理** — 点击"开始处理"，进度面板会实时显示进展
5. **下载 PDF** — 处理完成后点击"下载 PDF"获取结果

### 参数说明

| 参数 | 默认值 | 说明 |
|------|--------|------|
| 采样帧率 | 1 fps | 每秒提取的帧数，越大帧越多 |
| 开始时间 | 0s | 从视频的哪一秒开始提取 |
| 结束时间 | 0(结束) | 在视频的第几秒停止 |
| 纸张大小 | A4 | PDF 纸张大小 |
| 方向 | 纵向 | A4 纵向或横向 |
| 边距 | 10mm | PDF 页边距 |

## 项目结构

```
guitar-score-extractor/
├── backend/
│   ├── app/
│   │   ├── api/routes.py    # FastAPI 路由和流水线
│   │   ├── models/schemas.py # 数据模型
│   │   ├── services/
│   │   │   ├── frame_extractor.py   # ffmpeg 帧提取
│   │   │   ├── roi_cropper.py       # ROI 裁剪
│   │   │   ├── image_preprocessor.py # 预处理 + 去重
│   │   │   ├── pdf_exporter.py      # PDF 导出(帧排布 + img2pdf)
│   │   │   └── video_service.py     # 视频元信息读取
│   │   └── storage/manager.py       # 文件存储管理
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/         # React 组件
│   │   ├── pages/              # 页面
│   │   ├── services/api.ts     # 后端 API 调用
│   │   └── types/index.ts      # TypeScript 类型
│   └── package.json
└── README.md
```

## 处理流水线

```
视频 → ffmpeg 帧提取 → ROI 裁剪 → 智能去重 → A4 排布 → PDF
```

去重步骤使用 **Otsu 二值化 + 形态学膨胀 + 内容区域裁剪 + 像素差异检测**，能有效消除演奏进度光标和静态标题区域的干扰。

## 许可

MIT
