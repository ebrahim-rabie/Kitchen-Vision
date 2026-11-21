export interface Camera {
  id: string
  site_id: number
  name: string
  active: boolean
  resolution: string | null
  fps: number | null
  sampling_profile: string | null
}

export interface ComplianceEvent {
  id: string
  camera_id: string
  occurred_at: string
  track_id: string
  item: string
  status: string
  confidence: number
  model_version: string
  config_version: string
  review_state: string
}

export interface CountSummary {
  camera_id: string
  class_name: string
  bucket_start: string
  count: number
  uncertain_count: number
  mode: string
}

export interface HealthStatus {
  status: string
}

export interface Page<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

const baseUrl = import.meta.env.VITE_API_BASE_URL ?? ""
const apiKey = import.meta.env.VITE_API_KEY ?? "dev-key"

async function request<T>(path: string): Promise<T> {
  const response = await fetch(`${baseUrl}${path}`, {
    headers: { "X-API-Key": apiKey },
  })
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`)
  }
  return response.json() as Promise<T>
}

export const api = {
  live: () => request<HealthStatus>("/health/live"),
  ready: () => request<HealthStatus>("/health/ready"),
  cameras: () => request<Page<Camera>>("/api/v1/cameras"),
  events: () => request<Page<ComplianceEvent>>("/api/v1/events?page_size=100"),
  counts: () => request<CountSummary[]>("/api/v1/counts/summary"),
}
