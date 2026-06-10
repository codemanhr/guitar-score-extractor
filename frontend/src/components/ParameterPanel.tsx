 import { useState } from 'react'
 import type { PageOrientation, PageSize, ProcessingConfig, PDFConfig, ScrollDirection } from '../types'
 
 interface Props {
   processing: ProcessingConfig
   pdf: PDFConfig
   onProcessingChange: (c: ProcessingConfig) => void
   onPDFChange: (c: PDFConfig) => void
 }
 
 export default function ParameterPanel({
   processing,
   pdf,
   onProcessingChange,
   onPDFChange,
 }: Props) {
   return (
     <div className="parameter-panel">
       <h3>处理参数</h3>
 
       <div className="param-group">
         <label>采样帧率</label>
         <input
           type="number"
           min={0.5}
           max={30}
           step={0.5}
           value={processing.sample_fps}
           onChange={(e) =>
             onProcessingChange({ ...processing, sample_fps: Number(e.target.value) })
           }
         />
       </div>
 
       <div className="param-group">
         <label>开始时间（秒）</label>
         <input
           type="number"
           min={0}
           step={1}
           value={processing.start_time}
           onChange={(e) =>
             onProcessingChange({ ...processing, start_time: Number(e.target.value) })
           }
         />
       </div>
 
       <div className="param-group">
         <label>结束时间（秒，0=结束）</label>
         <input
           type="number"
           min={0}
           step={1}
           value={processing.end_time ?? 0}
           onChange={(e) => {
             const v = Number(e.target.value)
             onProcessingChange({
               ...processing,
               end_time: v > 0 ? v : null,
             })
           }}
         />
       </div>
 
       <div className="param-group">
         <label>滚动方向</label>
         <select
           value={processing.scroll_direction}
           onChange={(e) =>
             onProcessingChange({
               ...processing,
               scroll_direction: e.target.value as ScrollDirection,
             })
           }
         >
           <option value="auto">自动检测</option>
           <option value="left">向左</option>
           <option value="right">向右</option>
           <option value="up">向上</option>
           <option value="down">向下</option>
         </select>
       </div>
 
       <div className="param-group checklist">
         <label>
           <input
             type="checkbox"
             checked={processing.invert}
             onChange={(e) =>
               onProcessingChange({ ...processing, invert: e.target.checked })
             }
           />
           反色（黑白）
         </label>
       </div>
 
       <div className="param-group">
         <label>二值化方法</label>
         <select
           value={processing.threshold}
           onChange={(e) =>
             onProcessingChange({ ...processing, threshold: e.target.value })
           }
         >
           <option value="auto">自适应</option>
           <option value="otsu">大津法</option>
           <option value="128">固定值 128</option>
         </select>
       </div>
 
       <h3>PDF 设置</h3>
 
       <div className="param-group">
         <label>纸张大小</label>
         <select
           value={pdf.page_size}
           onChange={(e) => onPDFChange({ ...pdf, page_size: e.target.value as PageSize })}
         >
           <option value="A4">A4</option>
           <option value="letter">Letter</option>
         </select>
       </div>
 
       <div className="param-group">
         <label>方向</label>
         <select
           value={pdf.orientation}
           onChange={(e) =>
             onPDFChange({ ...pdf, orientation: e.target.value as PageOrientation })
           }
         >
           <option value="portrait">纵向</option>
           <option value="landscape">横向</option>
         </select>
       </div>
 
       <div className="param-group">
         <label>边距（毫米）</label>
         <input
           type="number"
           min={0}
           max={50}
           step={1}
           value={pdf.margin_mm}
           onChange={(e) => onPDFChange({ ...pdf, margin_mm: Number(e.target.value) })}
         />
       </div>
 
     </div>
   )
 }
