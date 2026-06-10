 const BASE = '/api'
 
 async function request<T>(url: string, options?: RequestInit): Promise<T> {
   const res = await fetch(`${BASE}${url}`, {
     headers: { 'Content-Type': 'application/json' },
     ...options,
   })
   if (!res.ok) {
     const text = await res.text()
     throw new Error(`[${res.status}] ${text.slice(0, 200)}`)
   }
   const contentType = res.headers.get('content-type') || ''
   if (contentType.includes('application/json')) {
     return res.json()
   }
   return res as unknown as T
 }
 
 // ── Health ──
 export async function healthCheck() {
   return request<{ status: string }>('/health')
 }
 
 // ── Projects ──
 export async function createProject() {
   return request<{ id: string; config: import('../types').ProjectConfig }>(
     '/projects',
     { method: 'POST' }
   )
 }
 
 export async function listProjects() {
   return request<import('../types').ProjectInfo[]>('/projects')
 }
 
 export async function getProject(projectId: string) {
   return request<{ id: string; config: import('../types').ProjectConfig }>(
     `/projects/${projectId}`
   )
 }
 
 // ── Video ──
 export async function uploadVideo(projectId: string, file: File) {
   const form = new FormData()
   form.append('file', file)
   const res = await fetch(`${BASE}/projects/${projectId}/upload`, {
     method: 'POST',
     body: form,
   })
   if (!res.ok) {
     const text = await res.text()
     throw new Error(`[${res.status}] ${text.slice(0, 200)}`)
   }
   return res.json()
 }
 
 export async function getVideoInfo(projectId: string) {
   return request<{ video_info: import('../types').VideoInfo }>(
     `/projects/${projectId}/video-info`
   )
 }
 
 export function getPreviewUrl(projectId: string, timeSec = 0, width = 800) {
   return `${BASE}/projects/${projectId}/preview?time_sec=${timeSec}&width=${width}`
 }
 
 // ── ROI ──
 export async function setROI(projectId: string, roi: import('../types').ROI) {
   return request(`/projects/${projectId}/roi`, {
     method: 'POST',
     body: JSON.stringify(roi),
   })
 }
 
 // ── Config ──
 export async function setProcessingConfig(
   projectId: string,
   config: import('../types').ProcessingConfig
 ) {
   return request(`/projects/${projectId}/config`, {
     method: 'POST',
     body: JSON.stringify(config),
   })
 }
 
 export async function setPDFConfig(projectId: string, config: import('../types').PDFConfig) {
   return request(`/projects/${projectId}/pdf-config`, {
     method: 'POST',
     body: JSON.stringify(config),
   })
 }
 
 // ── Processing ──
 export async function startProcessing(projectId: string) {
   return request<import('../types').TaskProgress>(
     `/projects/${projectId}/process`,
     { method: 'POST' }
   )
 }
 
 export async function getProgress(projectId: string) {
   return request<import('../types').TaskProgress>(
     `/projects/${projectId}/progress`
   )
 }
 
 // ── Results ──
 export function getStitchedUrl(projectId: string) {
   return `${BASE}/projects/${projectId}/stitched-preview`
 }
 
 export function getDownloadPDFUrl(projectId: string) {
   return `${BASE}/projects/${projectId}/download-pdf`
 }
