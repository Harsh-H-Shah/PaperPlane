import { useEffect, useState } from 'react'
import { store, defaultSettings } from '../lib/storage'
import type { Settings as SettingsT } from '../lib/types'
import { toast } from './toast'

export function Settings() {
  const [s, setS] = useState<SettingsT>(defaultSettings())
  const [loaded, setLoaded] = useState(false)
  const [saved, setSaved] = useState(false)
  const [kw, setKw] = useState('')

  useEffect(() => {
    store.getSettings().then((v) => {
      setS(v)
      setLoaded(true)
    })
  }, [])

  function update<K extends keyof SettingsT>(key: K, value: SettingsT[K]) {
    setS((prev) => ({ ...prev, [key]: value }))
    setSaved(false)
  }

  async function save() {
    await store.setSettings(s)
    setSaved(true)
    toast('Settings saved')
    setTimeout(() => setSaved(false), 1500)
  }

  function addKeyword() {
    const v = kw.trim().toLowerCase()
    if (v && !s.alwaysReviewKeywords.includes(v)) {
      update('alwaysReviewKeywords', [...s.alwaysReviewKeywords, v])
    }
    setKw('')
  }

  if (!loaded) return <div className="empty">Loading…</div>

  return (
    <div>
      <div className="section">
        <h2>LLM engine</h2>
        <label className="field">
          <span>Provider</span>
          <select value={s.provider} onChange={(e) => update('provider', e.target.value as SettingsT['provider'])}>
            <option value="gemini">Gemini (cloud)</option>
            <option value="ollama">Ollama (local)</option>
          </select>
        </label>

        {s.provider === 'gemini' && (
          <>
            <label className="field">
              <span>Gemini API key</span>
              <input
                type="password"
                value={s.geminiApiKey}
                placeholder="AIza…"
                onChange={(e) => update('geminiApiKey', e.target.value)}
              />
              <div className="hint">
                Stored only in this browser. Get one at aistudio.google.com/apikey.
              </div>
            </label>
            <label className="field">
              <span>Model</span>
              <input
                type="text"
                value={s.model}
                list="pp-models"
                onChange={(e) => update('model', e.target.value)}
              />
              <datalist id="pp-models">
                <option value="gemini-2.5-flash" />
                <option value="gemini-2.5-flash-lite" />
                <option value="gemini-2.5-pro" />
                <option value="gemini-flash-latest" />
              </datalist>
              <div className="hint">
                Recommended: <code>gemini-2.5-flash</code> (fast + cheap). Use{' '}
                <code>gemini-2.5-flash-lite</code> for lowest cost, <code>gemini-2.5-pro</code> for
                best quality.
              </div>
            </label>
          </>
        )}

        {s.provider === 'ollama' && (
          <>
            <label className="field">
              <span>Ollama base URL</span>
              <input
                type="text"
                value={s.ollamaBaseUrl}
                onChange={(e) => update('ollamaBaseUrl', e.target.value)}
              />
            </label>
            <label className="field">
              <span>Ollama model</span>
              <input
                type="text"
                value={s.ollamaModel}
                onChange={(e) => update('ollamaModel', e.target.value)}
              />
            </label>
          </>
        )}
      </div>

      <div className="section">
        <h2>Answering</h2>
        <label className="field">
          <span>Answer strategy</span>
          <select
            value={s.answerStrategy}
            onChange={(e) => update('answerStrategy', e.target.value as SettingsT['answerStrategy'])}
          >
            <option value="yesman">Aggressive — maximize interview chances</option>
            <option value="balanced">Balanced — truthful to profile</option>
          </select>
        </label>
        <label className="field">
          <span>Essay tone</span>
          <input type="text" value={s.essayTone} onChange={(e) => update('essayTone', e.target.value)} />
        </label>
        <label className="field">
          <span>Max essay length (characters)</span>
          <input
            type="number"
            value={s.essayMaxLength}
            onChange={(e) => update('essayMaxLength', Number(e.target.value) || 0)}
          />
        </label>
      </div>

      <div className="section">
        <h2>Always review these topics</h2>
        <div>
          {s.alwaysReviewKeywords.map((k) => (
            <span className="pill" key={k}>
              {k}
              <button
                onClick={() =>
                  update(
                    'alwaysReviewKeywords',
                    s.alwaysReviewKeywords.filter((x) => x !== k),
                  )
                }
              >
                ×
              </button>
            </span>
          ))}
        </div>
        <div className="row" style={{ marginTop: 6 }}>
          <input
            type="text"
            value={kw}
            placeholder="add keyword…"
            onChange={(e) => setKw(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && addKeyword()}
          />
          <button className="btn secondary" style={{ flex: '0 0 auto' }} onClick={addKeyword}>
            Add
          </button>
        </div>
        <div className="hint">Fields matching these are never auto-filled — always shown for review.</div>
      </div>

      <div className="section">
        <h2>Behavior</h2>
        <label className="toggle">
          <input
            type="checkbox"
            checked={s.enabled}
            onChange={(e) => update('enabled', e.target.checked)}
          />
          <span>Show the in-page badge on application forms</span>
        </label>
        <label className="toggle">
          <input
            type="checkbox"
            checked={s.autoFillOnDetect}
            onChange={(e) => update('autoFillOnDetect', e.target.checked)}
          />
          <span>Auto-fill immediately when a form is detected (skip the button)</span>
        </label>
      </div>

      <div className="row">
        <button className="btn" onClick={save}>
          {saved ? 'Saved ✓' : 'Save settings'}
        </button>
      </div>
    </div>
  )
}
