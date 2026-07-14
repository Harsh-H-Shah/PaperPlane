import { useEffect, useRef, useState } from 'react'
import { store, resumeStore } from '../lib/storage'
import { importFromProfileJson, normalizeProfile } from '../lib/profile'
import type { Profile } from '../lib/types'
import { toast } from './toast'

export function ProfilePanel() {
  const [p, setP] = useState<Profile | null>(null)
  const [raw, setRaw] = useState('')
  const [resumeName, setResumeName] = useState<string>('')
  const [showRaw, setShowRaw] = useState(false)
  const importFile = useRef<HTMLInputElement>(null)
  const resumeFile = useRef<HTMLInputElement>(null)

  useEffect(() => {
    store.getProfile().then((v) => {
      setP(v)
      setRaw(JSON.stringify(v, null, 2))
    })
    resumeStore.load().then((r) => r && setResumeName(r.name))
  }, [])

  function flash(kind: 'ok' | 'err', text: string) {
    toast(text, kind)
  }

  async function persist(next: Profile) {
    const norm = normalizeProfile(next)
    await store.setProfile(norm)
    setP(norm)
    setRaw(JSON.stringify(norm, null, 2))
  }

  async function importText(text: string) {
    try {
      const parsed = JSON.parse(text)
      const profile = normalizeProfile(importFromProfileJson(parsed))
      await persist(profile)
      flash('ok', `Imported profile for ${profile.full_name || 'you'}.`)
    } catch (e) {
      flash('err', `Import failed: ${e instanceof Error ? e.message : String(e)}`)
    }
  }

  async function onImportFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    await importText(await file.text())
    e.target.value = ''
  }

  async function onResumeFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file || !p) return
    const bytes = await file.arrayBuffer()
    await resumeStore.save(bytes, file.name, file.type || 'application/pdf')
    setResumeName(file.name)
    await persist({
      ...p,
      resume: {
        file_name: file.name,
        last_updated: new Date().toISOString().slice(0, 10),
        mime_type: file.type || 'application/pdf',
        size: file.size,
      },
    })
    flash('ok', `Resume saved: ${file.name}`)
    e.target.value = ''
  }

  async function clearResume() {
    await resumeStore.clear()
    setResumeName('')
    flash('ok', 'Resume removed.')
  }

  async function saveRaw() {
    try {
      const parsed = JSON.parse(raw) as Profile
      await persist(parsed)
      flash('ok', 'Profile saved.')
    } catch (e) {
      flash('err', `Invalid JSON: ${e instanceof Error ? e.message : String(e)}`)
    }
  }

  function field(label: string, key: keyof Profile) {
    if (!p) return null
    return (
      <label className="field">
        <span>{label}</span>
        <input
          type="text"
          value={String(p[key] ?? '')}
          onChange={(e) => setP({ ...p, [key]: e.target.value })}
        />
      </label>
    )
  }

  if (!p) return <div className="empty">Loading…</div>

  return (
    <div>
      <div className="section">
        <h2>Import</h2>
        <div className="hint" style={{ marginBottom: 8 }}>
          Paste your <code>data/profile.json</code> or pick the file to seed everything at once.
        </div>
        <div className="row">
          <button className="btn secondary" onClick={() => importFile.current?.click()}>
            Import profile.json…
          </button>
        </div>
        <input
          ref={importFile}
          type="file"
          accept="application/json,.json"
          style={{ display: 'none' }}
          onChange={onImportFile}
        />
      </div>

      <div className="section">
        <h2>Resume</h2>
        <div className="hint" style={{ marginBottom: 8 }}>
          {resumeName ? (
            <>
              Current: <strong>{resumeName}</strong>
            </>
          ) : (
            'No resume uploaded. Used to auto-attach on file-upload fields.'
          )}
        </div>
        <div className="row">
          <button className="btn secondary" onClick={() => resumeFile.current?.click()}>
            Upload PDF…
          </button>
          {resumeName && (
            <button className="btn danger" style={{ flex: '0 0 auto' }} onClick={clearResume}>
              Remove
            </button>
          )}
        </div>
        <input
          ref={resumeFile}
          type="file"
          accept="application/pdf,.pdf,.doc,.docx"
          style={{ display: 'none' }}
          onChange={onResumeFile}
        />
      </div>

      <div className="section">
        <h2>Basics</h2>
        <div className="row">
          {field('First name', 'first_name')}
          {field('Last name', 'last_name')}
        </div>
        {field('Email', 'email')}
        {field('Phone', 'phone')}
        {field('LinkedIn', 'linkedin')}
        {field('GitHub', 'github')}
        {field('Portfolio', 'portfolio')}
        <label className="field">
          <span>City / State</span>
          <div className="row">
            <input
              type="text"
              placeholder="City"
              value={p.address.city}
              onChange={(e) => setP({ ...p, address: { ...p.address, city: e.target.value } })}
            />
            <input
              type="text"
              placeholder="State"
              value={p.address.state}
              onChange={(e) => setP({ ...p, address: { ...p.address, state: e.target.value } })}
            />
          </div>
        </label>
        <button
          className="btn"
          onClick={async () => {
            await persist(p)
            flash('ok', 'Profile saved.')
          }}
        >
          Save basics
        </button>
      </div>

      <div className="section">
        <h2>
          Advanced{' '}
          <button
            className="pill"
            style={{ float: 'right' }}
            onClick={() => setShowRaw((v) => !v)}
          >
            {showRaw ? 'hide' : 'edit raw JSON'}
          </button>
        </h2>
        {showRaw && (
          <>
            <textarea
              style={{ minHeight: 260, fontFamily: 'monospace', fontSize: 12 }}
              value={raw}
              onChange={(e) => setRaw(e.target.value)}
            />
            <div className="row" style={{ marginTop: 8 }}>
              <button className="btn" onClick={saveRaw}>
                Save JSON
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
