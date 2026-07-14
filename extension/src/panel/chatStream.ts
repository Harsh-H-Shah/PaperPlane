// Streaming chat — the side panel is an extension page, so it can fetch the LLM
// directly (host permission bypasses CORS) and stream tokens for a fast feel.

import { store } from '../lib/storage'
import { chatSystemPrompt } from '../lib/prompts'
import type { ChatMessage } from '../lib/messaging'

export async function streamChat(
  messages: ChatMessage[],
  onChunk: (text: string) => void,
): Promise<void> {
  const [profile, settings] = await Promise.all([store.getProfile(), store.getSettings()])
  const system = chatSystemPrompt(profile)
  const transcript = messages
    .map((m) => `${m.role === 'user' ? 'User' : 'Assistant'}: ${m.content}`)
    .join('\n')
  const prompt = `${transcript}\n\nAssistant:`

  if (settings.provider === 'ollama') {
    if (!settings.ollamaBaseUrl) throw new Error('Set your Ollama URL in Settings.')
    const res = await fetch(`${settings.ollamaBaseUrl.replace(/\/$/, '')}/api/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model: settings.ollamaModel, prompt: `${system}\n\n${prompt}`, stream: true }),
    })
    if (!res.ok || !res.body) throw new Error(`Ollama ${res.status}`)
    await readLines(res.body, (line) => {
      try {
        const d = JSON.parse(line)
        if (d.response) onChunk(d.response as string)
      } catch {
        /* skip partial line */
      }
    })
    return
  }

  if (!settings.geminiApiKey) throw new Error('Add your Gemini API key in Settings.')
  const url = `https://generativelanguage.googleapis.com/v1beta/models/${encodeURIComponent(
    settings.model,
  )}:streamGenerateContent?alt=sse&key=${encodeURIComponent(settings.geminiApiKey)}`
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      systemInstruction: { parts: [{ text: system }] },
      contents: [{ role: 'user', parts: [{ text: prompt }] }],
      generationConfig: { temperature: 0.7, maxOutputTokens: 1024 },
    }),
  })
  if (!res.ok || !res.body) {
    const t = await res.text().catch(() => '')
    throw new Error(`Gemini ${res.status}: ${t.slice(0, 200)}`)
  }
  await readLines(res.body, (line) => {
    if (!line.startsWith('data:')) return
    const js = line.slice(5).trim()
    if (!js || js === '[DONE]') return
    try {
      const d = JSON.parse(js)
      const parts: { text?: string }[] = d?.candidates?.[0]?.content?.parts ?? []
      const t = parts.map((p) => p.text ?? '').join('')
      if (t) onChunk(t)
    } catch {
      /* skip partial chunk */
    }
  })
}

async function readLines(body: ReadableStream<Uint8Array>, onLine: (line: string) => void) {
  const reader = body.getReader()
  const dec = new TextDecoder()
  let buf = ''
  for (;;) {
    const { value, done } = await reader.read()
    if (done) break
    buf += dec.decode(value, { stream: true })
    let i: number
    while ((i = buf.indexOf('\n')) >= 0) {
      const line = buf.slice(0, i).trim()
      buf = buf.slice(i + 1)
      if (line) onLine(line)
    }
  }
  if (buf.trim()) onLine(buf.trim())
}
