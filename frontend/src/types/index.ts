 export interface VideoInfo {
   width: number
   height: number
   fps: number
   duration: number
   frame_count: number
   codec: string
 }
 
 export interface ROI {
   x: number
   y: number
   width: number
   height: number
 }
 
 export type ScrollDirection = 'auto' | 'left' | 'right' | 'up' | 'down'
 export type PageSize = 'A4' | 'letter'
 export type PageOrientation = 'portrait' | 'landscape'
 export type TaskStatus =
   | 'pending'
   | 'extracting_frames'
   | 'cropping'
   | 'preprocessing'
   | 'stitching'
   | 'rendering_pdf'
   | 'completed'
   | 'failed'
   | 'cancelled'
 
 export interface ProcessingConfig {
   sample_fps: number
   start_time: number
   end_time: number | null
   max_frames: number | null
   scroll_direction: ScrollDirection
   invert: boolean
   threshold: string
 }
 
 export interface PDFConfig {
   page_size: PageSize
   orientation: PageOrientation
   margin_mm: number
 }
 
 export interface ProjectConfig {
   source_video: string
   video: VideoInfo | null
   roi: ROI | null
   processing: ProcessingConfig
   pdf: PDFConfig
 }
 
 export interface ProjectInfo {
   id: string
   config: ProjectConfig
   created_at: string
   updated_at: string
 }
 
 export interface TaskProgress {
   project_id: string
   status: TaskStatus
   progress_pct: number
   current_frame: number
   total_frames: number
   current_stage: string
   log: string[]
   output_files: string[]
 }
