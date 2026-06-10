import { useState } from 'react'
import * as api from '../services/api'

interface Props {
  projectId: string
  onUploaded: () => void
}

export default function VideoUploader({ projectId, onUploaded }: Props) {
  const [uploading, setUploading] = useState(false)

  async function handleFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    try {
      await api.uploadVideo(projectId, file)
      onUploaded()
    } catch (err: any) {
      alert(`上传失败: ${err.message}`)
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="video-uploader">
      <label className="upload-btn">
        {uploading ? '上传中...' : '导入视频'}
        <input
          type="file"
          accept="video/mp4,video/quicktime,video/x-msvideo,video/x-matroska"
          onChange={handleFile}
          hidden
        />
      </label>
    </div>
  )
}
