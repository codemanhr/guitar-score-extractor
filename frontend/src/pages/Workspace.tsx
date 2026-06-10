import { useCallback, useEffect, useRef, useState } from 'react'
import ParameterPanel from '../components/ParameterPanel'
import ProgressPanel from '../components/ProgressPanel'
import ResultPreview from '../components/ResultPreview'
import ROISelector from '../components/ROISelector'
import VideoPreview from '../components/VideoPreview'
import VideoUploader from '../components/VideoUploader'
import * as api from '../services/api'
import type { ProcessingConfig, PDFConfig, ROI, TaskProgress, VideoInfo } from '../types'

const DEFAULT_PROCESSING: ProcessingConfig = {
  sample_fps: 1,
  start_time: 0,
  end_time: null,
  max_frames: null,
  scroll_direction: 'auto',
  invert: false,
  threshold: 'auto',
}

const DEFAULT_PDF: PDFConfig = {
  page_size: 'A4',
  orientation: 'portrait',
  margin_mm: 10,
}

export default function Workspace() {
  const [projectId, setProjectId] = useState<string | null>(null)
  const [videoInfo, setVideoInfo] = useState<VideoInfo | null>(null)
  const [roi, setROI] = useState<ROI | null>(null)
  const [processing, setProcessing] = useState<ProcessingConfig>(DEFAULT_PROCESSING)
  const [pdf, setPDF] = useState<PDFConfig>(DEFAULT_PDF)
  const [progress, setProgress] = useState<TaskProgress | null>(null)
  const [running, setRunning] = useState(false)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const [hasVideo, setHasVideo] = useState(false)
  const [previewTime, setPreviewTime] = useState(0)
  const previewWidth = 800

  // ── Init project ──
  useEffect(() => {
    api.createProject().then((p) => setProjectId(p.id))
  }, [])

  const handleUploaded = useCallback(async () => {
    if (!projectId) return
    setHasVideo(true)
    const res = await api.getVideoInfo(projectId)
    setVideoInfo(res.video_info)
  }, [projectId])

  const handleROIChange = useCallback(
    async (newROI: ROI) => {
      if (!projectId) return
      setROI(newROI)
      await api.setROI(projectId, newROI)
    },
    [projectId]
  )

  const handleProcessingChange = useCallback(
    async (c: ProcessingConfig) => {
      setProcessing(c)
      if (projectId) await api.setProcessingConfig(projectId, c)
    },
    [projectId]
  )

  const handlePDFChange = useCallback(
    async (c: PDFConfig) => {
      setPDF(c)
      if (projectId) await api.setPDFConfig(projectId, c)
    },
    [projectId]
  )

  // ── Start processing ──
  const handleStart = useCallback(async () => {
    if (!projectId) return
    if (!roi) {
      alert('请先选择乐谱区域（ROI）')
      return
    }
    setRunning(true)
    setProgress(null)
    try {
      const result = await api.startProcessing(projectId)
      setProgress(result)
      // Poll progress
      pollRef.current = setInterval(async () => {
        try {
          const p = await api.getProgress(projectId)
          setProgress(p)
          if (p.status === 'completed' || p.status === 'failed' || p.status === 'cancelled') {
            if (pollRef.current) clearInterval(pollRef.current)
            setRunning(false)
            pollRef.current = null
          }
        } catch {
          if (pollRef.current) clearInterval(pollRef.current)
          setRunning(false)
          pollRef.current = null
        }
      }, 1000)
    } catch (err: any) {
      alert(`处理失败: ${err.message}`)
      setRunning(false)
    }
  }, [projectId, roi])

  // Cleanup poll on unmount
  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [])

  const previewUrl =
    projectId && videoInfo ? api.getPreviewUrl(projectId, previewTime, previewWidth) : ''

  return (
    <div className="workspace">
      <header className="workspace-header">
        <h1>吉他谱提取器</h1>
        {projectId && <VideoUploader projectId={projectId} onUploaded={handleUploaded} />}
      </header>

      <main className="workspace-main">
        {/* Left: video preview + ROI */}
        <section className="workspace-left">
          <VideoPreview
            projectId={projectId ?? ''}
            videoInfo={videoInfo}
            timeSec={previewTime}
            onTimeChange={setPreviewTime}
          />
          {hasVideo && videoInfo && (
            <ROISelector
              imageUrl={previewUrl}
              videoWidth={videoInfo.width}
              videoHeight={videoInfo.height}
              displayWidth={previewWidth}
              onROIChange={handleROIChange}
              initialROI={roi}
            />
          )}
        </section>

        {/* Right: parameters + progress + results */}
        <section className="workspace-right">
          <ParameterPanel
            processing={processing}
            pdf={pdf}
            onProcessingChange={handleProcessingChange}
            onPDFChange={handlePDFChange}
          />
          <div className="action-bar">
            <button className="btn btn-primary" onClick={handleStart} disabled={running || !projectId}>
              {running ? '处理中...' : '开始处理'}
            </button>
          </div>
          <ProgressPanel progress={progress} running={running} />
          {projectId && <ResultPreview projectId={projectId} progress={progress} />}
        </section>
      </main>
    </div>
  )
}
