import { useEffect, useState } from 'react'
import { Settings } from './Settings'
import { ProfilePanel } from './Profile'
import { Chat } from './Chat'
import { Learned } from './Learned'
import { Logo } from './Logo'
import { ActionBar } from './ActionBar'
import { Toaster } from './toast'
import { store } from '../lib/storage'

type Tab = 'chat' | 'profile' | 'learned' | 'settings'

const TABS: { id: Tab; label: string }[] = [
  { id: 'chat', label: 'Chat' },
  { id: 'profile', label: 'Profile' },
  { id: 'learned', label: 'Learned' },
  { id: 'settings', label: 'Settings' },
]

export function App() {
  const [tab, setTab] = useState<Tab>('chat')
  const [usage, setUsage] = useState<string>('')

  useEffect(() => {
    const refresh = () =>
      store.getUsage().then((u) => {
        if (u && u.dailyRequests > 0) setUsage(`${u.dailyRequests} today`)
      })
    refresh()
    const id = setInterval(refresh, 4000)
    return () => clearInterval(id)
  }, [])

  return (
    <div className="app">
      <header className="topbar">
        <span className="logo">
          <Logo size={24} />
        </span>
        <h1>PaperPlane</h1>
        <span className="spacer" />
        {usage && <span className="usage">{usage}</span>}
        <button className="closebtn" title="Close panel" onClick={() => window.close()}>
          ×
        </button>
      </header>

      <ActionBar />

      <nav className="tabs">
        <div className="seg">
          {TABS.map((t) => (
            <button
              key={t.id}
              className={tab === t.id ? 'active' : ''}
              onClick={() => setTab(t.id)}
            >
              {t.label}
            </button>
          ))}
        </div>
      </nav>

      <main className="content">
        {tab === 'chat' && <Chat />}
        {tab === 'profile' && <ProfilePanel />}
        {tab === 'learned' && <Learned />}
        {tab === 'settings' && <Settings />}
      </main>

      <Toaster />
    </div>
  )
}
