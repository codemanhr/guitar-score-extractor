import { useEffect, useRef, useState } from 'react'
import * as api from '../services/api'
import type { VideoInfo } from '../types'

interface Props {
  projectId: string
  videoInfo: VideoInfo | null
  timeSec: number
  onTimeChange: (t: number) => void
}

export default function VideoPreview({ projectId, videoInfo, timeSec, onTimeChange }: Props) {
  const imgRef = useRef<HTMLImageElement>(null)
  const [srcKey, setSrcKey] = useState(0)

  useEffect(() => {
    setSrcKey((k) => k + 1)
  }, [projectId, timeSec])

  const maxTime = videoInfo ? Math.max(videoInfo.duration - 1, 0) : 0

  return (
    <div className="video-preview">
      <div className="preview-controls">
        <label>
          预览时间：
          <input
            type="range"
            min={0}
            max={maxTime}
            step={0.5}
            value={timeSec}
            onChange={(e) => onTimeChange(Number(e.target.value))}
          />
          <span className="time-label">{timeSec.toFixed(1)}秒</span>
        </label>
      </div>
      <div className="preview-frame-container">
        {videoInfo ? (
          <img
            key={srcKey}
            ref={imgRef}
            src={api.getPreviewUrl(projectId, timeSec, 800)}
            alt="预览帧"
            className="preview-frame"
            draggable={false}
          />
        ) : (
          <div className="preview-placeholder">导入视频以查看预览</div>
        )}
        {videoInfo && (
          <div className="video-info-badge">
            {videoInfo.width}x{videoInfo.height} @ {videoInfo.fps}fps |{' '}
            {videoInfo.duration.toFixed(0)}秒
          </div>
        )}
      </div>
    </div>
  )
}
