const BASE = '/api/v1'

export interface HarnessConfig {
  max_turns: number
  total_token_budget: number
  llm_provider: string
  model: string
  enabled_tools: string[]
}
export interface TaskCreate {
  description: string
  config: HarnessConfig
  uploaded_file_paths?: string[]
}
export interface AgentEvent {
  event_type: 'thought' | 'tool_call' | 'tool_result' | 'error' | 'done'
  turn: number
  content: string
  tool_name: string | null
  tool_args: Record<string, unknown> | null
  tool_result: string | null
  duration_ms: number
  token_usage: Record<string, number>
}
export interface TaskStatus {
  id: string; description: string; status: string
  turn_count: number; total_tokens: number
  duration_seconds: number | null
  created_at: string; completed_at: string | null
  final_answer: string | null; error_message: string | null
}
export interface TaskHistoryItem {
  id: string; description: string; status: string
  turn_count: number; duration_seconds: number | null
  created_at: string; completed_at: string | null
}
export interface Turn {
  id: string; turn_number: number
  thought: string | null; tool_name: string | null
  tool_args: Record<string, unknown> | null
  tool_result: string | null
  duration_ms: number | null; tokens_used: number | null
  created_at: string
}
export interface OutputFile {
  id: string; filename: string
  content_type: string | null; size_bytes: number | null
  download_url: string; created_at: string
}

async function api<T>(path: string, opts?: RequestInit): Promise<T> {
  let res: Response
  try {
    res = await fetch(`${BASE}${path}`, {
      headers: { 'Content-Type': 'application/json', ...opts?.headers },
      ...opts,
    })
  } catch (err) {
    throw new Error(`Network error — is uvicorn running on port 8000? (${err})`)
  }
  if (!res.ok) {
    let msg = `HTTP ${res.status}`
    try { const b = await res.json(); msg = b.detail ?? msg } catch {}
    throw new Error(msg)
  }
  return res.json()
}

export const Api = {
  startTask:    (p: TaskCreate) => api<{ task_id: string }>('/tasks/start', { method: 'POST', body: JSON.stringify(p) }),
  getTaskStatus:(id: string)    => api<TaskStatus>(`/tasks/${id}/status`),
  getTaskTurns: (id: string)    => api<Turn[]>(`/tasks/${id}/turns`),
  getTaskFiles: (id: string)    => api<OutputFile[]>(`/tasks/${id}/files`),
  cancelTask:   (id: string)    => api<{ status: string }>(`/tasks/${id}/cancel`, { method: 'POST' }),
  resumeTask:   (id: string)    => api<{ task_id: string }>(`/tasks/${id}/resume`, { method: 'POST' }),
  getHistory: (params?: { status?: string; search?: string; page?: number }) => {
    const q = new URLSearchParams()
    if (params?.status) q.set('status', params.status)
    if (params?.search) q.set('search', params.search)
    if (params?.page)   q.set('page', String(params.page))
    return api<{ items: TaskHistoryItem[]; page: number; page_size: number }>(`/tasks/history?${q}`)
  },
  uploadFile: async (file: File, sessionId: string) => {
    const form = new FormData()
    form.append('file', file)
    const res = await fetch(`${BASE}/files/upload?session_id=${sessionId}`, { method: 'POST', body: form })
    if (!res.ok) throw new Error(`Upload failed: ${res.status}`)
    return res.json()
  },
}