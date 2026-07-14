// Content script — runs in the top frame AND sub-frames (ATS forms are often
// iframed). Detects fields robustly (observer + retries for late SPA forms),
// shows the badge in whichever frame has the form, and fills on click.

import { detectFields, detectAts, detectJob, type DetectedEntry } from '../lib/detect'
import { applyResolved, type ResumeBytes } from '../lib/fill'
import { store } from '../lib/storage'
import { mountPrompt, updateCount, showToast, showReview, type ReviewItem } from './overlay'
import type { Message, ResolveFieldsResponse, ResumeResponse } from '../lib/messaging'
import type { AtsKind, DetectedField, JobContext, ResolvedField } from '../lib/types'

let registry = new Map<string, DetectedEntry>()
let lastEntries: DetectedEntry[] = []
let ats: AtsKind = 'generic'
let badgeMounted = false
let autofilled = false
let autoFillOnDetect = false
let observer: MutationObserver | null = null

function scan(): { entries: DetectedEntry[]; job: JobContext } {
  ats = detectAts()
  const entries = detectFields()
  registry = new Map()
  for (const e of entries) {
    e.field.ats = ats
    registry.set(e.field.id, e)
  }
  lastEntries = entries
  return { entries, job: detectJob() }
}

/** Does this frame look like it holds an application form (vs. a marketing page)? */
function looksLikeApplication(entries: DetectedEntry[], atsKind: AtsKind): boolean {
  const n = entries.length
  if (n === 0) return false
  const hasFile = entries.some((e) => e.field.type === 'file')
  const hasTextarea = entries.some((e) => e.field.type === 'textarea')
  const hasEmail = entries.some((e) => e.field.type === 'email')
  const signal = hasFile || hasTextarea || atsKind !== 'generic'
  return n >= 3 || (n >= 2 && (signal || hasEmail)) || (n >= 1 && hasFile)
}

function tryShowBadge() {
  const { entries } = scan()
  if (badgeMounted) {
    updateCount(entries.length)
    return
  }
  if (looksLikeApplication(entries, ats)) {
    console.debug(`[PaperPlane] detected ${entries.length} fields (${ats})`)
    badgeMounted = true
    observer?.disconnect()
    if (autoFillOnDetect && !autofilled) {
      // User opted into filling immediately without being asked.
      autofilled = true
      mountPrompt(entries.length, promptCallbacks) // still show, then fill
      runFill()
    } else {
      // Auto-ask: proactively offer to fill.
      mountPrompt(entries.length, promptCallbacks)
    }
  }
}

const promptCallbacks = {
  onFill: () => runFill(),
  onAccept: acceptReview,
  onSkip: () => {},
  onRegenerate: regenerate,
}

async function getResume(fields: DetectedField[]): Promise<ResumeBytes | null> {
  if (!fields.some((f) => f.type === 'file')) return null
  const res = (await chrome.runtime.sendMessage({ type: 'GET_RESUME' })) as ResumeResponse
  if (res?.ok && res.base64) return { base64: res.base64, name: res.name!, mimeType: res.mimeType! }
  return null
}

async function runFill() {
  const { entries, job } = scan()
  const fields = entries.map((e) => e.field)
  // Silent when this frame has nothing — a broadcast fill hits empty frames too.
  if (fields.length === 0) return
  showToast('Filling…', 1200)

  let resolved: ResolvedField[]
  try {
    const res = (await chrome.runtime.sendMessage({ type: 'RESOLVE_FIELDS', job, fields })) as
      | ResolveFieldsResponse
      | { ok: false; error: string }
    if (!res.ok) {
      showToast(`Could not resolve fields: ${res.error}`)
      return
    }
    resolved = res.resolved
  } catch (e) {
    showToast(`Error: ${e instanceof Error ? e.message : String(e)}`)
    return
  }

  const resume = await getResume(fields)
  let filled = 0
  const review: ReviewItem[] = []

  for (const r of resolved) {
    const entry = registry.get(r.id)
    if (!entry) continue
    if (r.needsReview) {
      review.push({
        id: r.id,
        label: entry.field.label,
        value: r.value,
        reason: r.reviewReason,
        isEssay: r.isEssay,
        question: r.question ?? entry.field.label,
      })
      continue
    }
    if (r.source === 'none' || r.value === '') continue
    const result = await applyResolved(entry, r, resume)
    if (result.filled) filled++
    else if (result.note) console.debug('[PaperPlane]', entry.field.label, '→', result.note)
  }

  if (review.length > 0) {
    showReview(review)
    showToast(`Filled ${filled}. ${review.length} need${review.length === 1 ? 's' : ''} review.`)
  } else {
    showToast(`Filled ${filled} field${filled === 1 ? '' : 's'}.`)
  }
}

async function acceptReview(id: string, value: string) {
  const entry = registry.get(id)
  if (!entry) return
  const resume = await getResume([entry.field])
  await applyResolved(entry, { id, value, source: 'llm', confidence: 1, needsReview: false }, resume)
  const isEssay =
    entry.field.type === 'textarea' || (entry.field.type === 'text' && entry.field.label.length > 40)
  if (isEssay && value.trim()) {
    chrome.runtime.sendMessage({ type: 'LEARN_ANSWER', question: entry.field.label, answer: value })
  }
}

async function regenerate(id: string): Promise<string> {
  const entry = registry.get(id)
  if (!entry) return ''
  const res = (await chrome.runtime.sendMessage({
    type: 'REGENERATE',
    job: detectJob(),
    field: entry.field,
  })) as { ok: boolean; resolved?: ResolvedField; error?: string }
  return res.ok && res.resolved ? res.resolved.value : ''
}

// ─── Detection triggers: observer + timed retries for late-rendering forms ─────

let debounce: ReturnType<typeof setTimeout> | null = null
function scheduleTry() {
  if (badgeMounted) return
  if (debounce) clearTimeout(debounce)
  debounce = setTimeout(tryShowBadge, 400)
}

async function init() {
  const settings = await store.getSettings()
  if (!settings.enabled) return
  autoFillOnDetect = settings.autoFillOnDetect

  tryShowBadge()
  // Retry over ~10s for SPA forms (Ashby/Workday) that paint after load.
  ;[800, 2000, 4000, 8000].forEach((ms) => setTimeout(tryShowBadge, ms))

  // React to DOM changes (form appears after clicking "Apply", route change, etc.).
  observer = new MutationObserver(scheduleTry)
  observer.observe(document.documentElement, { childList: true, subtree: true })
}

// Guard against double-init when the script is also injected on demand from the
// panel/popup (chrome.scripting) into a page that already has it.
interface PPWindow extends Window {
  __paperplaneInit?: boolean
}
const ppWin = window as PPWindow

if (!ppWin.__paperplaneInit) {
  ppWin.__paperplaneInit = true

  chrome.runtime.onMessage.addListener((msg: Message, _sender, sendResponse) => {
    switch (msg.type) {
      case 'PING': {
        const { entries } = scan()
        sendResponse({ ok: true, count: entries.length })
        break
      }
      case 'TRIGGER_FILL':
        runFill()
        sendResponse({ ok: true, count: lastEntries.length })
        break
      case 'RESCAN':
        tryShowBadge()
        sendResponse({ ok: true, count: lastEntries.length })
        break
      default:
        sendResponse({ ok: false, error: 'unhandled' })
    }
    return true
  })

  if (document.readyState === 'loading') {
    window.addEventListener('DOMContentLoaded', init)
  } else {
    init()
  }
}
