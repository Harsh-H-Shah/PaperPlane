'use client';

interface TacticalHeaderProps {
  streak: number;
  totalXp: number;
}

// SVG Icons for professional look
const StatusDot = () => (
  <span className="w-2 h-2 rounded-full bg-[var(--valo-green)] energy-pulse" style={{ '--pulse-color': 'rgba(0, 255, 163, 0.5)' } as React.CSSProperties}></span>
);

const FlameIcon = ({ className = "w-5 h-5" }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
    <path d="M17.657 18.657A8 8 0 016.343 7.343S7 9 9 10c0-2 .5-5 2.986-7C14 5 16.09 5.777 17.656 7.343A7.975 7.975 0 0120 13a7.975 7.975 0 01-2.343 5.657z" />
    <path d="M9.879 16.121A3 3 0 1012.015 11L11 14H9c0 .768.293 1.536.879 2.121z" />
  </svg>
);

const BoltIcon = ({ className = "w-5 h-5" }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
  </svg>
);

export default function TacticalHeader({ streak, totalXp }: TacticalHeaderProps) {
  return (
    <header className="glass-card p-6 mb-6" data-gsap="fade-up">
      {/* Accent line at top */}
      <div className="accent-line mb-4" />

      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2 text-[var(--valo-text-dim)] text-sm mb-1">
            <StatusDot />
            SYSTEM STATUS: ONLINE
          </div>
          <h1 className="font-display text-4xl font-bold tracking-wider vibrant-text">
            TACTICAL DASHBOARD
          </h1>
        </div>

        <div className="flex items-center gap-8">
          {/* Streak Counter */}
          <div className="text-right group cursor-default">
            <div className="font-display text-3xl font-bold text-[var(--valo-cyan)] flex items-center gap-2 group-hover:drop-shadow-[0_0_12px_rgba(0,217,255,0.5)] transition-all">
              <span className="count-up">{streak.toString().padStart(2, '0')}</span>
              <FlameIcon className="w-6 h-6" />
            </div>
            <div className="text-xs text-[var(--valo-text-dim)] tracking-wider">OPERATION STREAK</div>
          </div>

          {/* XP Counter */}
          <div className="text-right group cursor-default">
            <div className="font-display text-3xl font-bold text-[var(--valo-green)] flex items-center gap-2 group-hover:drop-shadow-[0_0_12px_rgba(0,255,163,0.5)] transition-all">
              <span className="count-up">{totalXp.toLocaleString()}</span>
              <BoltIcon className="w-6 h-6" />
            </div>
            <div className="text-xs text-[var(--valo-text-dim)] tracking-wider">TOTAL RADIANT XP</div>
          </div>
        </div>
      </div>
    </header>
  );
}
