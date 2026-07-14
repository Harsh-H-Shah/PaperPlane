// Lightweight global toast: call toast(msg, kind) from anywhere; <Toaster/> renders.

import { useEffect, useState } from 'react'

type Kind = 'ok' | 'err' | 'info'
interface Item {
  id: number
  message: string
  kind: Kind
}

export function toast(message: string, kind: Kind = 'ok') {
  window.dispatchEvent(new CustomEvent('pp-toast', { detail: { message, kind } }))
}

export function Toaster() {
  const [items, setItems] = useState<Item[]>([])

  useEffect(() => {
    let counter = 0
    const handler = (e: Event) => {
      const detail = (e as CustomEvent).detail as { message: string; kind: Kind }
      const id = ++counter
      setItems((x) => [...x, { id, ...detail }])
      setTimeout(() => setItems((x) => x.filter((i) => i.id !== id)), 2600)
    }
    window.addEventListener('pp-toast', handler)
    return () => window.removeEventListener('pp-toast', handler)
  }, [])

  return (
    <div className="toaster">
      {items.map((i) => (
        <div key={i.id} className={`toastmsg ${i.kind}`}>
          {i.kind === 'ok' ? '✓' : i.kind === 'err' ? '⚠' : '✈️'} {i.message}
        </div>
      ))}
    </div>
  )
}
