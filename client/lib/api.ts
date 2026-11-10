// Typed client for the CADIS V2 API (ARCHITECTURE_V2 §9).
// One place for the base URL; every V2 page goes through these functions.

export const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "")

export type JobStatus = "PENDING" | "PROCESSING" | "COMPLETED" | "FAILED"
export type DocumentStatus = "PENDING" | "PROCESSING" | "READY" | "FAILED"

export interface Collection {
  id: string
  name: string
  created_at: string
  document_count: number
}

export interface Job {
  id: string
  type: string
  document_id: string | null
  status: JobStatus
  stage: string | null
  progress: number
  attempts: number
  max_attempts: number
  error: string | null
  created_at: string
  updated_at: string
}

export interface DocumentInfo {
  id: string
  collection_id: string
  filename: string
  title: string | null
  size_bytes: number
  sha256: string
  status: DocumentStatus
  current_version: number
  pages: number | null
  error: string | null
  created_at: string
  updated_at: string
  latest_job: Job | null
}

export interface UploadResult {
  filename: string
  document_id: string
  job_id: string | null
  duplicate: boolean
}

export interface Section {
  id: string
  parent_id: string | null
  title: string
  path: string
  level: number
  ordinal: number
  page: number | null
  char_start: number
  char_end: number
  chunk_count: number
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response
  try {
    res = await fetch(`${API_URL}${path}`, init)
  } catch {
    throw new ApiError(0, `Cannot reach the CADIS API at ${API_URL}. Is the backend running?`)
  }
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail)
    } catch {
      /* not JSON */
    }
    throw new ApiError(res.status, detail || `Request failed (${res.status})`)
  }
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

const json = (body: unknown): RequestInit => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
})

export const api = {
  listCollections: () => request<Collection[]>("/collections"),
  createCollection: (name: string) => request<Collection>("/collections", json({ name })),
  listDocuments: (collectionId: string) =>
    request<DocumentInfo[]>(`/collections/${collectionId}/documents`),

  uploadDocuments: (collectionId: string, files: File[]) => {
    const form = new FormData()
    files.forEach((f) => form.append("files", f))
    return request<UploadResult[]>(`/collections/${collectionId}/documents`, { method: "POST", body: form })
  },

  getDocument: (id: string) => request<DocumentInfo>(`/documents/${id}`),
  getSections: (id: string) => request<Section[]>(`/documents/${id}/sections`),
  reingestDocument: (id: string) =>
    request<{ document_id: string; job_id: string }>(`/documents/${id}/reingest`, { method: "POST" }),
  deleteDocument: (id: string) => request<void>(`/documents/${id}`, { method: "DELETE" }),

  getJob: (id: string) => request<Job>(`/jobs/${id}`),
  retryJob: (id: string) => request<Job>(`/jobs/${id}/retry`, { method: "POST" }),

  /** Follow a job over Server-Sent Events. Returns a function that stops listening. */
  watchJob(id: string, onUpdate: (job: Job) => void, onEnd?: () => void): () => void {
    const source = new EventSource(`${API_URL}/jobs/${id}/events`)
    source.onmessage = (e) => {
      const job = JSON.parse(e.data) as Job
      onUpdate(job)
      if (job.status === "COMPLETED" || job.status === "FAILED") {
        source.close()
        onEnd?.()
      }
    }
    source.addEventListener("gone", () => {
      source.close()
      onEnd?.()
    })
    return () => source.close()
  },
}

export const isActive = (job: Job | null | undefined) =>
  !!job && (job.status === "PENDING" || job.status === "PROCESSING")
