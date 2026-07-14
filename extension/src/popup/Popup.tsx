import { useEffect, useState } from 'react'
import { store } from '../lib/storage'
import { Logo } from '../panel/Logo'
import { fillActiveTab } from '../panel/pageActions'

// Injected into every frame of the active tab to count visible fillable controls.
function countFieldsInFrame(): number {
  const nodes = document.querySelectorAll(
    'input:not([type=hidden]):not([type=submit]):not([type=button]):not([type=reset]):not([type=password]):not([type=search]), textarea, select, [role="combobox"], [contenteditable="true"]',
  )
  let n = 0
  nodes.forEach((el) => {
    const h = el as HTMLElement
    if (h.offsetParent !== null || (h.getClientRects && h.getClientRects().length > 0)) n++
  })
  return n
}

export function Popup() {
  const [detected, setDetected] = useState<number | null>(null)
  const [hasKey, setHasKey] = useState(true)
  const [note, setNote] = useState('')

  useEffect(() => {
    store.getSettings().then((s) => setHasKey(s.provider === 'ollama' || !!s.geminiApiKey))
    ;(async () => {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true })
      if (!tab?.id) return setDetected(null)
      try {
        const results = await chrome.scripting.executeScript({
          target: { tabId: tab.id, allFrames: true },
          func: countFieldsInFrame,
        })
        const total = results.reduce((sum, r) => sum + (typeof r.result === 'number' ? r.result : 0), 0)
        setDetected(total)
      } catch {
        setDetected(null)
      }
    })()
  }, [])

  async function fill() {
    const ok = await fillActiveTab()
    if (ok) window.close()
    else setNote('Open a job application page, then try again.')
  }

  async function openPanel() {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true })
    if (tab?.windowId != null) {
      await chrome.sidePanel.open({ windowId: tab.windowId })
      window.close()
    }
  }

  return (
    <div className="popup">
      <div className="head">
        <Logo size={22} />
        <h1>PaperPlane Autofill</h1>
      </div>

      <div className="status-line">
        {detected === null
          ? "Can't read this page (try a job application URL)."
          : detected === 0
            ? 'No fillable fields detected on this page.'
            : `${detected} field${detected === 1 ? '' : 's'} detected on this page.`}
        {!hasKey && (
          <>
            <br />
            <span style={{ color: 'var(--warn)' }}>
              Add your Gemini key in Settings to enable AI answers.
            </span>
          </>
        )}
      </div>

      {note && <div className="status err">{note}</div>}

      <div className="actions">
        <button className="btn" onClick={fill} disabled={!detected}>
          Fill this page
        </button>
        <button className="btn secondary" onClick={openPanel}>
          Open side panel
        </button>
      </div>
    </div>
  )
}
