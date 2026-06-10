 import type { TaskProgress } from '../types'
 
 interface Props {
   progress: TaskProgress | null
   running: boolean
 }
 
 const STATUS_LABELS: Record<string, string> = {
   pending: '等待中',
   extracting_frames: '提取帧中',
   cropping: '裁剪 ROI',
   preprocessing: '预处理中',
   stitching: '拼接中',
   rendering_pdf: '生成 PDF',
   completed: '已完成',
   failed: '失败',
   cancelled: '已取消',
 }
 
 export default function ProgressPanel({ progress, running }: Props) {
   if (!progress) {
     return (
       <div className="progress-panel">
         <div className="progress-idle">配置参数后点击开始处理</div>
       </div>
     )
   }
 
   const pct = progress.progress_pct
   const statusLabel = STATUS_LABELS[progress.status] || progress.status
   const isError = progress.status === 'failed'
   const isDone = progress.status === 'completed'
 
   return (
     <div className={`progress-panel ${isError ? 'error' : ''} ${isDone ? 'done' : ''}`}>
       <div className="progress-header">
         <span className="progress-status">{statusLabel}</span>
         <span className="progress-pct">{pct.toFixed(0)}%</span>
       </div>
       <div className="progress-bar-bg">
         <div
           className="progress-bar-fill"
           style={{ width: `${pct}%` }}
         />
       </div>
       {progress.current_frame > 0 && progress.total_frames > 0 && (
         <div className="progress-detail">
           帧 {progress.current_frame} / {progress.total_frames}
         </div>
       )}
       <div className="progress-log">
         {progress.log.map((line, i) => (
           <div key={i} className="log-line">
             {line}
           </div>
         ))}
       </div>
     </div>
   )
 }
