import { useEffect, useState } from 'react'
import * as api from '../services/api'
import type { TaskProgress } from '../types'

interface Props {
  projectId: string
  progress: TaskProgress | null
}

export default function ResultPreview({ projectId, progress }: Props) {
  const [pdfReady, setPdfReady] = useState(false)

  useEffect(() => {
    if (progress?.status === 'completed') {
      setPdfReady(true)
    }
  }, [progress?.status])

  const pdfUrl = api.getDownloadPDFUrl(projectId)

  return (
    <div className="result-preview">
      <h3>结果</h3>

      <div className="result-actions">
        <a
          href={pdfUrl}
          download="score.pdf"
          className={`btn ${pdfReady ? '' : 'disabled'}`}
          style={{ pointerEvents: pdfReady ? 'auto' : 'none' }}
        >
          下载 PDF
        </a>
      </div>

      {!pdfReady && progress?.status !== 'completed' && progress?.status !== 'failed' && (
        <div className="result-placeholder">
          处理完成后将显示结果。
        </div>
      )}
    </div>
  )
}
