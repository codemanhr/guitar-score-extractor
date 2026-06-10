 import { useCallback, useEffect, useRef, useState } from 'react'
 import type { ROI } from '../types'
 
 interface Props {
   imageUrl: string
   videoWidth: number
   videoHeight: number
   displayWidth: number
   onROIChange: (roi: ROI) => void
   initialROI?: ROI | null
 }
 
 interface DragState {
   active: boolean
   startX: number
   startY: number
   endX: number
   endY: number
 }
 
 export default function ROISelector({
   imageUrl,
   videoWidth,
   videoHeight,
   displayWidth,
   onROIChange,
   initialROI,
 }: Props) {
   const [drag, setDrag] = useState<DragState>({
     active: false,
     startX: 0,
     startY: 0,
     endX: 0,
     endY: 0,
   })
   const [roi, setROI] = useState<ROI | null>(initialROI || null)
   const containerRef = useRef<HTMLDivElement>(null)
 
   const scale = displayWidth / videoWidth
   const displayHeight = videoHeight * scale
 
   const handleMouseDown = useCallback(
     (e: React.MouseEvent<HTMLDivElement>) => {
       if (!containerRef.current) return
       const rect = containerRef.current.getBoundingClientRect()
       const x = (e.clientX - rect.left) / scale
       const y = (e.clientY - rect.top) / scale
       setDrag({
         active: true,
         startX: x,
         startY: y,
         endX: x,
         endY: y,
       })
     },
     [scale]
   )
 
   const handleMouseMove = useCallback(
     (e: React.MouseEvent<HTMLDivElement>) => {
       if (!drag.active || !containerRef.current) return
       const rect = containerRef.current.getBoundingClientRect()
       const x = Math.max(0, Math.min((e.clientX - rect.left) / scale, videoWidth))
       const y = Math.max(0, Math.min((e.clientY - rect.top) / scale, videoHeight))
       setDrag((d) => ({ ...d, endX: x, endY: y }))
     },
     [drag.active, scale, videoWidth, videoHeight]
   )
 
   const handleMouseUp = useCallback(() => {
     if (!drag.active) return
     const x1 = Math.min(drag.startX, drag.endX)
     const y1 = Math.min(drag.startY, drag.endY)
     const x2 = Math.max(drag.startX, drag.endX)
     const y2 = Math.max(drag.startY, drag.endY)
     const w = Math.max(10, x2 - x1)
     const h = Math.max(10, y2 - y1)
     const newROI: ROI = { x: Math.round(x1), y: Math.round(y1), width: Math.round(w), height: Math.round(h) }
     setROI(newROI)
     onROIChange(newROI)
     setDrag((d) => ({ ...d, active: false }))
   }, [drag, onROIChange])
 
   const selectionBox = (() => {
     if (roi) {
       return {
         left: roi.x * scale,
         top: roi.y * scale,
         width: roi.width * scale,
         height: roi.height * scale,
       }
     }
     if (drag.active || drag.startX !== drag.endX) {
       const x1 = Math.min(drag.startX, drag.endX) * scale
       const y1 = Math.min(drag.startY, drag.endY) * scale
       const w = Math.abs(drag.endX - drag.startX) * scale
       const h = Math.abs(drag.endY - drag.startY) * scale
       return { left: x1, top: y1, width: w, height: h }
     }
     return null
   })()
 
   return (
     <div className="roi-selector">
       <div className="roi-label">拖拽选择乐谱区域（ROI）</div>
       <div
         ref={containerRef}
         className="roi-container"
         style={{ width: displayWidth, height: displayHeight, position: 'relative' }}
         onMouseDown={handleMouseDown}
         onMouseMove={handleMouseMove}
         onMouseUp={handleMouseUp}
         onMouseLeave={handleMouseUp}
       >
         <img
           src={imageUrl}
           alt="ROI 选区预览"
           draggable={false}
           style={{ width: '100%', height: '100%', display: 'block', userSelect: 'none' }}
         />
         {selectionBox && (
           <div
             className="roi-box"
             style={{
               position: 'absolute',
               border: '2px solid #00e5ff',
               backgroundColor: 'rgba(0, 229, 255, 0.15)',
               pointerEvents: 'none',
               ...selectionBox,
             }}
           />
         )}
       </div>
       {roi && (
         <div className="roi-coords">
           ROI: x={roi.x}, y={roi.y}, 宽={roi.width}, 高={roi.height}
         </div>
       )}
     </div>
   )
 }
