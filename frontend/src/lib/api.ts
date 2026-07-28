const BASE = 'http://localhost:8000'

export interface KnowledgeBase {
  id: string
  name: string
  description?: string
  created_at: string
}

export interface Citation {
  source: string
  page?: number
  chunk: string
}

export interface ChatMessage {
  role: 'human' | 'ai'
  content: string
  citations?: Citation[]
}

// ── Knowledge bases ────────────────────────────────────────────

export async function listKBs(): Promise<KnowledgeBase[]> {
  const res = await fetch(`${BASE}/kb`)
  if (!res.ok) throw new Error('Failed to fetch knowledge bases')
  return res.json()
}

export async function createKB(name: string, description?: string): Promise<KnowledgeBase> {
  const res = await fetch(`${BASE}/kb`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, description }),
  })
  if (!res.ok) throw new Error('Failed to create knowledge base')
  return res.json()
}

export async function deleteKB(id: string): Promise<void> {
  const res = await fetch(`${BASE}/kb/${id}`, { method: 'DELETE' })
  if (!res.ok) throw new Error('Failed to delete knowledge base')
}

// ── Ingestion ──────────────────────────────────────────────────

export async function ingestFile(kbId: string, file: File): Promise<{ chunks_stored: number }> {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${BASE}/kb/${kbId}/ingest`, { method: 'POST', body: form })
  if (!res.ok) throw new Error('Failed to ingest file')
  return res.json()
}

// ── Streaming query ────────────────────────────────────────────

export async function* streamQuery(
  kbId: string,
  question: string,
  chatHistory: { role: string; content: string }[]
): AsyncGenerator<{ type: 'token'; text: string } | { type: 'citations'; data: Citation[] }> {
  const res = await fetch(`${BASE}/kb/${kbId}/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, chat_history: chatHistory }),
  })

  if (!res.ok) throw new Error('Query failed')

  const reader = res.body!.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() ?? ''

    for (const line of lines) {
      if (!line.startsWith('data: ')) continue
      const payload = line.slice(6)
      if (payload === '[DONE]') return
      if (payload.startsWith('[CITATIONS]')) {
        const data = JSON.parse(payload.slice(11))
        yield { type: 'citations', data: data.citations }
      } else {
        // unescape newlines encoded by the SSE route
        yield { type: 'token', text: payload.replace(/\\n/g, '\n') }
      }
    }
  }
}

// Single file, all API calls in one place. BASE switches to an env var before prod.
// streamQuery is an async generator — the caller iterates it with for-await-of,
// receiving either token chunks (appended to the chat bubble live) or the final
// citations payload (rendered in the sources panel below the answer).