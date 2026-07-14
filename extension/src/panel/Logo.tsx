// Inline brand mark (browser renders the gradient fine, unlike the rasterized icon).

export function Logo({ size = 22, rounded = true }: { size?: number; rounded?: boolean }) {
  const gradId = `ppG${size}`
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" aria-hidden="true">
      <defs>
        <linearGradient id={gradId} x1="0%" y1="100%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="#00D9FF" />
          <stop offset="100%" stopColor="#00E39A" />
        </linearGradient>
      </defs>
      <rect width="64" height="64" rx={rounded ? 15 : 0} fill={`url(#${gradId})`} />
      <path d="M50 15 L14 30 L27 34 L31 47 L37 36 L50 15 Z" fill="#07131A" />
      <path d="M50 15 L27 34 L37 36 Z" fill="#ffffff" opacity="0.22" />
    </svg>
  )
}
