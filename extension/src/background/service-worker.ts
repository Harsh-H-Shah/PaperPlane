// Service worker — the hub. In Phase 1 it wires the side panel and a health ping.
// Phases 3–4 add RESOLVE_FIELDS / REGENERATE / CHAT / GET_RESUME handlers here.

import type { Message, MsgResponse } from '../lib/messaging'
import { handleWorkerMessage } from './handlers'

chrome.runtime.onInstalled.addListener(() => {
  // Let clicking the toolbar icon open the popup (manifest default_popup);
  // the popup exposes an "Open side panel" button.
  chrome.sidePanel?.setPanelBehavior?.({ openPanelOnActionClick: false }).catch(() => {})
})

chrome.runtime.onMessage.addListener((msg: Message, sender, sendResponse) => {
  handleWorkerMessage(msg, sender)
    .then((res: MsgResponse) => sendResponse(res))
    .catch((err: unknown) =>
      sendResponse({ ok: false, error: err instanceof Error ? err.message : String(err) }),
    )
  return true // keep the message channel open for the async response
})
