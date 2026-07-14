import { useEffect, useState } from 'react'
import { store } from '../lib/storage'
import type { LearnedAnswer } from '../lib/types'
import { toast } from './toast'

export function Learned() {
  const [items, setItems] = useState<LearnedAnswer[]>([])
  const [editing, setEditing] = useState<string | null>(null)
  const [draft, setDraft] = useState('')

  useEffect(() => {
    store.getLearned().then(setItems)
  }, [])

  async function save(list: LearnedAnswer[]) {
    setItems(list)
    await store.setLearned(list)
  }

  async function remove(nq: string) {
    await save(items.filter((i) => i.normalizedQuestion !== nq))
    toast('Deleted')
  }

  async function commitEdit(nq: string) {
    await save(items.map((i) => (i.normalizedQuestion === nq ? { ...i, answer: draft } : i)))
    setEditing(null)
    toast('Answer updated')
  }

  if (items.length === 0) {
    return (
      <div className="empty">
        Nothing learned yet. When you accept or edit a generated answer while filling a form, it's
        saved here and reused automatically next time — even on other sites.
      </div>
    )
  }

  return (
    <div>
      <div className="hint" style={{ marginBottom: 10 }}>
        {items.length} remembered answer{items.length === 1 ? '' : 's'}. These are reused before ever
        calling the LLM.
      </div>
      {items
        .slice()
        .sort((a, b) => b.lastUsedISO.localeCompare(a.lastUsedISO))
        .map((it) => (
          <div className="card" key={it.normalizedQuestion}>
            <div className="q">{it.question}</div>
            {editing === it.normalizedQuestion ? (
              <>
                <textarea value={draft} onChange={(e) => setDraft(e.target.value)} />
                <div className="row" style={{ marginTop: 8 }}>
                  <button className="btn" onClick={() => commitEdit(it.normalizedQuestion)}>
                    Save
                  </button>
                  <button className="btn secondary" onClick={() => setEditing(null)}>
                    Cancel
                  </button>
                </div>
              </>
            ) : (
              <>
                <div className="a">{it.answer}</div>
                <div className="row" style={{ marginTop: 8 }}>
                  <button
                    className="btn secondary"
                    onClick={() => {
                      setEditing(it.normalizedQuestion)
                      setDraft(it.answer)
                    }}
                  >
                    Edit
                  </button>
                  <button
                    className="btn danger"
                    style={{ flex: '0 0 auto' }}
                    onClick={() => remove(it.normalizedQuestion)}
                  >
                    Delete
                  </button>
                </div>
                <div className="hint" style={{ marginTop: 6 }}>
                  used {it.timesUsed}×
                </div>
              </>
            )}
          </div>
        ))}
    </div>
  )
}
