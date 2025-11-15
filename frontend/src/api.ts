export type JobStatus = 'queued' | 'running' | 'succeeded' | 'failed'

const API_BASE = '/api'

export async function startAutoJob(payload: Record<string, any>): Promise<{ job_id: string }> {
  const res = await fetch(`${API_BASE}/jobs/auto`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) throw new Error('Failed to start job')
  return res.json()
}

export async function startCopyJob(payload: { template_id_or_url: string; new_title?: string }): Promise<{ job_id: string }> {
  const res = await fetch(`${API_BASE}/jobs/copy`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) throw new Error('Failed to start copy job')
  return res.json()
}

export async function getJob(jobId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/jobs/${jobId}`)
  if (!res.ok) throw new Error('Failed to fetch job')
  return res.json()
}

export async function getJobLogs(jobId: string): Promise<string[]> {
  const res = await fetch(`${API_BASE}/jobs/${jobId}/logs`)
  if (!res.ok) throw new Error('Failed to fetch logs')
  const data = await res.json()
  return data.logs || []
}

export async function startInteractiveJob(payload: Record<string, any>): Promise<{ job_id: string }> {
  const res = await fetch(`${API_BASE}/jobs/interactive`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) throw new Error('Failed to start interactive job')
  return res.json()
}


