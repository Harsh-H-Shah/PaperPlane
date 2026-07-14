// In-page UI in a Shadow DOM (host-page CSS can't touch it). Light theme.
// On detection it AUTO-ASKS ("Fill this application?"); dismiss collapses to a
// small pill. Also renders the review panel + status toasts.

export interface ReviewItem {
  id: string
  label: string
  value: string
  reason?: string
  isEssay?: boolean
  question?: string
}

export interface OverlayCallbacks {
  onFill: () => void
  onAccept?: (id: string, value: string) => void
  onSkip?: (id: string) => void
  onRegenerate?: (id: string, instructions?: string) => Promise<string>
}

const PLANE = `<svg width="20" height="20" viewBox="0 0 64 64" aria-hidden="true">
  <defs><linearGradient id="og" x1="0%" y1="100%" x2="100%" y2="0%">
    <stop offset="0%" stop-color="#00D9FF"/><stop offset="100%" stop-color="#00E39A"/>
  </linearGradient></defs>
  <rect width="64" height="64" rx="15" fill="url(#og)"/>
  <path d="M50 15 L14 30 L27 34 L31 47 L37 36 L50 15 Z" fill="#07131A"/>
  <path d="M50 15 L27 34 L37 36 Z" fill="#ffffff" opacity="0.22"/>
</svg>`

const STYLE = `
:host { all: initial; }
* { box-sizing: border-box; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
.wrap { position: fixed; right: 18px; bottom: 18px; z-index: 2147483647; }

.prompt {
  width: 268px; background: #fff; color: #17203a;
  border: 1px solid #e4e8f0; border-radius: 14px; padding: 14px;
  box-shadow: 0 10px 34px rgba(20,30,60,.18);
}
.prompt .top { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.prompt .top .name { font-size: 12px; font-weight: 700; letter-spacing: -0.2px; }
.prompt .top .x { margin-left: auto; background: none; border: none; color: #98a2b3; font-size: 17px; cursor: pointer; line-height: 1; padding: 0 2px; }
.prompt .top .x:hover { color: #17203a; }
.prompt h4 { margin: 0 0 3px; font-size: 14.5px; }
.prompt .sub { color: #6a7488; font-size: 12px; margin-bottom: 12px; }
.prompt .row { display: flex; gap: 8px; }
.prompt .row .btn { flex: 1; }

.pill {
  display: inline-flex; align-items: center; gap: 8px;
  background: #fff; color: #17203a; border: 1px solid #e4e8f0;
  border-radius: 999px; padding: 8px 14px 8px 10px; cursor: pointer;
  box-shadow: 0 6px 20px rgba(20,30,60,.16); font-size: 13px; font-weight: 600;
}
.pill:hover { border-color: #0aa2c0; }

.btn { border: none; border-radius: 9px; padding: 9px 13px; font-size: 12.5px; font-weight: 600; cursor: pointer; }
.btn.primary { background: linear-gradient(135deg,#00c6f0,#12d39a); color: #fff; }
.btn.primary:hover { filter: brightness(1.05); }
.btn.ghost { background: #f2f4f8; color: #17203a; border: 1px solid #e4e8f0; }
.btn.ghost:hover { background: #e9edf3; }

.toast {
  position: fixed; right: 18px; bottom: 74px; z-index: 2147483647;
  background: #17203a; color: #fff; border-radius: 10px;
  padding: 10px 14px; font-size: 12.5px; max-width: 320px; box-shadow: 0 8px 24px rgba(0,0,0,.28);
}

.panel {
  position: fixed; right: 18px; bottom: 74px; z-index: 2147483647;
  width: 360px; max-height: 68vh; overflow-y: auto;
  background: #fff; color: #17203a; border: 1px solid #e4e8f0; border-radius: 14px;
  box-shadow: 0 14px 40px rgba(20,30,60,.22); padding: 14px;
}
.panel .head { display: flex; align-items: center; gap: 8px; margin-bottom: 3px; }
.panel h3 { margin: 0; font-size: 14px; }
.panel .subh { color: #6a7488; font-size: 12px; margin-bottom: 12px; }
.item { border: 1px solid #e4e8f0; border-radius: 11px; padding: 11px; margin-bottom: 9px; background: #fbfcfe; }
.item .q { font-size: 12px; color: #17203a; font-weight: 600; margin-bottom: 6px; }
.item .reason { font-size: 11px; color: #dc8a00; margin-bottom: 6px; }
.item textarea { width: 100%; min-height: 66px; background: #fff; color: #17203a; border: 1px solid #d3d9e6; border-radius: 8px; padding: 8px; font-size: 12.5px; font-family: inherit; resize: vertical; }
.item textarea:focus { outline: none; border-color: #0aa2c0; box-shadow: 0 0 0 3px rgba(10,162,192,.14); }
.item .actions { display: flex; gap: 6px; margin-top: 8px; }
.panel .footer { display: flex; gap: 8px; margin-top: 4px; }
.panel .footer .btn { flex: 1; }
`

let shadow: ShadowRoot | null = null
let wrapEl: HTMLElement | null = null
let toastEl: HTMLElement | null = null
let reviewEl: HTMLElement | null = null
let cbs: OverlayCallbacks | null = null
let currentCount = 0

function ensureRoot(): ShadowRoot {
  if (shadow) return shadow
  const host = document.createElement('div')
  host.id = 'paperplane-overlay-host'
  host.style.all = 'initial'
  document.documentElement.appendChild(host)
  shadow = host.attachShadow({ mode: 'open' })
  const style = document.createElement('style')
  style.textContent = STYLE
  shadow.appendChild(style)
  return shadow
}

function ensureWrap(): HTMLElement {
  const root = ensureRoot()
  if (!wrapEl) {
    wrapEl = document.createElement('div')
    wrapEl.className = 'wrap'
    root.appendChild(wrapEl)
  }
  return wrapEl
}

/** Auto-ask prompt shown when a form is detected. */
export function mountPrompt(count: number, callbacks: OverlayCallbacks) {
  cbs = callbacks
  currentCount = count
  const wrap = ensureWrap()
  wrap.innerHTML = `
    <div class="prompt">
      <div class="top">${PLANE}<span class="name">PaperPlane</span>
        <button class="x" title="Dismiss">×</button></div>
      <h4>Fill this application?</h4>
      <div class="sub">${count} field${count === 1 ? '' : 's'} detected on this page.</div>
      <div class="row">
        <button class="btn primary" data-act="fill">Fill it</button>
        <button class="btn ghost" data-act="later">Not now</button>
      </div>
    </div>`
  wrap.querySelector('[data-act="fill"]')?.addEventListener('click', () => {
    collapseToPill()
    cbs?.onFill()
  })
  wrap.querySelector('[data-act="later"]')?.addEventListener('click', collapseToPill)
  wrap.querySelector('.x')?.addEventListener('click', () => {
    wrap.remove()
    wrapEl = null
  })
}

function collapseToPill() {
  const wrap = ensureWrap()
  wrap.innerHTML = `<button class="pill">${PLANE}<span>Fill · ${currentCount}</span></button>`
  wrap.querySelector('.pill')?.addEventListener('click', () => cbs?.onFill())
}

export function updateCount(count: number) {
  currentCount = count
  const sub = wrapEl?.querySelector('.sub')
  if (sub) sub.textContent = `${count} field${count === 1 ? '' : 's'} detected on this page.`
  const pillText = wrapEl?.querySelector('.pill span')
  if (pillText) pillText.textContent = `Fill · ${count}`
}

export function showToast(text: string, ms = 3500) {
  const root = ensureRoot()
  if (toastEl) toastEl.remove()
  toastEl = document.createElement('div')
  toastEl.className = 'toast'
  toastEl.textContent = text
  root.appendChild(toastEl)
  if (ms > 0) setTimeout(() => toastEl?.remove(), ms)
}

export function showReview(items: ReviewItem[]) {
  const root = ensureRoot()
  if (reviewEl) reviewEl.remove()
  if (items.length === 0) return
  reviewEl = document.createElement('div')
  reviewEl.className = 'panel'

  const head = document.createElement('div')
  head.innerHTML = `<div class="head">${PLANE}<h3>Review ${items.length} answer${items.length === 1 ? '' : 's'}</h3></div>
    <div class="subh">Generated or flagged — accept, edit, or skip before they're filled.</div>`
  reviewEl.appendChild(head)

  for (const it of items) {
    const wrap = document.createElement('div')
    wrap.className = 'item'
    wrap.dataset.id = it.id

    const q = document.createElement('div')
    q.className = 'q'
    q.textContent = it.label
    wrap.appendChild(q)

    if (it.reason) {
      const r = document.createElement('div')
      r.className = 'reason'
      r.textContent = `⚠ ${it.reason}`
      wrap.appendChild(r)
    }

    const ta = document.createElement('textarea')
    ta.value = it.value
    wrap.appendChild(ta)

    const actions = document.createElement('div')
    actions.className = 'actions'

    const accept = document.createElement('button')
    accept.className = 'btn primary'
    accept.textContent = 'Accept'
    accept.addEventListener('click', () => {
      cbs?.onAccept?.(it.id, ta.value)
      wrap.remove()
      cleanupIfEmpty()
    })
    actions.appendChild(accept)

    if (it.isEssay) {
      const regen = document.createElement('button')
      regen.className = 'btn ghost'
      regen.textContent = 'Regenerate'
      regen.addEventListener('click', async () => {
        const prev = regen.textContent
        regen.textContent = '…'
        const next = await cbs?.onRegenerate?.(it.id)
        if (next) ta.value = next
        regen.textContent = prev
      })
      actions.appendChild(regen)
    }

    const skip = document.createElement('button')
    skip.className = 'btn ghost'
    skip.textContent = 'Skip'
    skip.addEventListener('click', () => {
      cbs?.onSkip?.(it.id)
      wrap.remove()
      cleanupIfEmpty()
    })
    actions.appendChild(skip)

    wrap.appendChild(actions)
    reviewEl.appendChild(wrap)
  }

  const footer = document.createElement('div')
  footer.className = 'footer'
  const acceptAll = document.createElement('button')
  acceptAll.className = 'btn primary'
  acceptAll.textContent = 'Accept all'
  acceptAll.addEventListener('click', () => {
    reviewEl?.querySelectorAll<HTMLElement>('.item').forEach((el) => {
      cbs?.onAccept?.(el.dataset.id!, el.querySelector('textarea')!.value)
    })
    reviewEl?.remove()
    reviewEl = null
  })
  const close = document.createElement('button')
  close.className = 'btn ghost'
  close.textContent = 'Close'
  close.addEventListener('click', () => {
    reviewEl?.remove()
    reviewEl = null
  })
  footer.appendChild(acceptAll)
  footer.appendChild(close)
  reviewEl.appendChild(footer)
  root.appendChild(reviewEl)
}

function cleanupIfEmpty() {
  if (reviewEl && reviewEl.querySelectorAll('.item').length === 0) {
    reviewEl.remove()
    reviewEl = null
  }
}
