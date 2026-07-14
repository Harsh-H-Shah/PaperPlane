import { useEffect, useState } from 'react'
import { countActiveTabFields, fillActiveTab } from './pageActions'
import { toast } from './toast'

export function ActionBar() {
  const [count, setCount] = useState<number | null>(null)
  const [filling, setFilling] = useState(false)

  function refresh() {
    countActiveTabFields().then(setCount)
  }

  useEffect(() => {
    refresh()
    const onActivated = () => refresh()
    const onUpdated = (_id: number, info: chrome.tabs.TabChangeInfo, tab: chrome.tabs.Tab) => {
      if (info.status === 'complete' && tab.active) refresh()
    }
    chrome.tabs.onActivated.addListener(onActivated)
    chrome.tabs.onUpdated.addListener(onUpdated)
    return () => {
      chrome.tabs.onActivated.removeListener(onActivated)
      chrome.tabs.onUpdated.removeListener(onUpdated)
    }
  }, [])

  async function fill() {
    setFilling(true)
    const ok = await fillActiveTab()
    setFilling(false)
    if (ok) toast('Filling the current page…', 'info')
    else toast('Open a job application page, then try again.', 'err')
  }

  const has = (count ?? 0) > 0
  const label =
    count === null
      ? "Can't read this page"
      : has
        ? `${count} field${count === 1 ? '' : 's'} on this page`
        : 'No form detected here'

  return (
    <div className="actionbar">
      <div className="ab-status">
        <span className={`dot ${has ? 'on' : ''}`} />
        <span>{label}</span>
        <button className="ab-refresh" title="Rescan this page" onClick={refresh}>
          ⟳
        </button>
      </div>
      <button className="btn" disabled={!has || filling} onClick={fill}>
        {filling ? 'Filling…' : 'Fill this page'}
      </button>
    </div>
  )
}
