// Panel → active tab helpers: count fillable fields (across frames) and trigger fill.

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

async function activeTab(): Promise<chrome.tabs.Tab | undefined> {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true })
  return tab
}

export async function countActiveTabFields(): Promise<number | null> {
  const tab = await activeTab()
  if (!tab?.id) return null
  try {
    const results = await chrome.scripting.executeScript({
      target: { tabId: tab.id, allFrames: true },
      func: countFieldsInFrame,
    })
    return results.reduce((sum, r) => sum + (typeof r.result === 'number' ? r.result : 0), 0)
  } catch {
    return null
  }
}

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms))

export async function fillActiveTab(): Promise<boolean> {
  const tab = await activeTab()
  if (!tab?.id) return false

  try {
    await chrome.tabs.sendMessage(tab.id, { type: 'TRIGGER_FILL' })
    return true
  } catch {
    // Content script isn't in this page yet (e.g. the tab predates the extension
    // reload). Inject it on demand, then retry.
    try {
      const files = chrome.runtime.getManifest().content_scripts?.[0]?.js ?? []
      if (files.length === 0) return false
      await chrome.scripting.executeScript({ target: { tabId: tab.id, allFrames: true }, files })
      await sleep(450)
      await chrome.tabs.sendMessage(tab.id, { type: 'TRIGGER_FILL' })
      return true
    } catch {
      return false
    }
  }
}
