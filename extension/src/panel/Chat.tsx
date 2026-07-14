import { useEffect, useRef, useState } from 'react'
import type { ChatMessage } from '../lib/messaging'
import { streamChat } from './chatStream'
import { Logo } from './Logo'

const SUGGESTIONS = [
  "Draft a strong “Why do you want to work here?” answer",
  'Summarize my background in 3 sentences',
  'What could I improve about my profile?',
  'Help me describe my most impressive project',
]

export function Chat() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, busy])

  async function send(text: string) {
    const content = text.trim()
    if (!content || busy) return
    const next: ChatMessage[] = [...messages, { role: 'user', content }]
    setMessages([...next, { role: 'assistant', content: '' }])
    setInput('')
    setBusy(true)

    let acc = ''
    try {
      await streamChat(next, (chunk) => {
        acc += chunk
        setMessages((m) => {
          const copy = [...m]
          copy[copy.length - 1] = { role: 'assistant', content: acc }
          return copy
        })
      })
      if (!acc) {
        setMessages((m) => {
          const copy = [...m]
          copy[copy.length - 1] = { role: 'assistant', content: '(no response)' }
          return copy
        })
      }
    } catch (e) {
      setMessages((m) => {
        const copy = [...m]
        copy[copy.length - 1] = {
          role: 'assistant',
          content: `⚠️ ${e instanceof Error ? e.message : String(e)}`,
        }
        return copy
      })
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="chat">
      <div className="messages">
        {messages.length === 0 ? (
          <div className="welcome">
            <div className="mark">
              <Logo size={40} />
            </div>
            <h3>Hi — I know your profile</h3>
            <p>
              Ask me to draft or refine application answers, tailor a pitch, or explain a role. I
              can also save new facts about you to your profile.
            </p>
            <div className="suggestions">
              {SUGGESTIONS.map((s) => (
                <button key={s} className="suggestion" onClick={() => send(s)}>
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((m, i) => {
            const isLast = i === messages.length - 1
            if (m.role === 'assistant' && m.content === '' && busy && isLast) {
              return (
                <div key={i} className="msg assistant typing">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              )
            }
            return (
              <div key={i} className={`msg ${m.role}`}>
                {m.content}
              </div>
            )
          })
        )}
        <div ref={endRef} />
      </div>
      <div className="composer">
        <textarea
          value={input}
          placeholder="Ask anything…"
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              send(input)
            }
          }}
        />
        <button className="btn" onClick={() => send(input)} disabled={busy || !input.trim()}>
          Send
        </button>
      </div>
    </div>
  )
}
