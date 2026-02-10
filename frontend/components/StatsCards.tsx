'use client';

import { useEffect, useState, useRef } from 'react';

interface StatCardProps {
  label: string;
  value: number | string;
  icon: React.ReactNode;
  color: string;
  colorName: string;
  sublabel?: string;
  delay?: number;
}

function useCountUp(target: number, duration = 1200) {
  const [count, setCount] = useState(0);
  const ref = useRef<number>(0);

  useEffect(() => {
    if (target === 0) { setCount(0); return; }
    const start = performance.now();
    const from = ref.current;

    const tick = (now: number) => {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      const eased = progress === 1 ? 1 : 1 - Math.pow(2, -10 * progress);
      const current = Math.floor(from + (target - from) * eased);
      setCount(current);

      if (progress < 1) {
        requestAnimationFrame(tick);
      } else {
        ref.current = target;
      }
    };

    requestAnimationFrame(tick);
  }, [target, duration]);

  return count;
}

// SVG Icon components
const TargetIcon = ({ className = "w-6 h-6" }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
    <circle cx="12" cy="12" r="10" /><circle cx="12" cy="12" r="6" /><circle cx="12" cy="12" r="2" />
  </svg>
);

const CheckShieldIcon = ({ className = "w-6 h-6" }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
    <path d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
  </svg>
);

const ClockIcon = ({ className = "w-6 h-6" }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
    <circle cx="12" cy="12" r="10" /><path d="M12 6v6l4 2" />
  </svg>
);

const FlameIcon = ({ className = "w-6 h-6" }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
    <path d="M17.657 18.657A8 8 0 016.343 7.343S7 9 9 10c0-2 .5-5 2.986-7C14 5 16.09 5.777 17.656 7.343A7.975 7.975 0 0120 13a7.975 7.975 0 01-2.343 5.657z" />
    <path d="M9.879 16.121A3 3 0 1012.015 11L11 14H9c0 .768.293 1.536.879 2.121z" />
  </svg>
);

function StatCard({ label, value, icon, color, colorName, sublabel, delay = 0 }: StatCardProps) {
  const numericValue = typeof value === 'number' ? value : 0;
  const animatedValue = useCountUp(numericValue);
  const displayValue = typeof value === 'number' ? animatedValue : value;

  return (
    <div
      className="gradient-card p-5 stat-card-glow cursor-default group"
      style={{ borderColor: `${color}20` }}
      data-color={colorName}
      data-gsap="fade-up"
      data-gsap-delay={String(delay / 1000)}
    >
      <div className="flex items-start justify-between">
        <div>
          <div className="text-xs text-[var(--valo-text-dim)] tracking-wider mb-2 uppercase">
            {label}
          </div>
          <div
            className="font-display text-4xl font-bold transition-all duration-300 group-hover:drop-shadow-[0_0_15px_currentColor]"
            style={{ color }}
          >
            {typeof displayValue === 'number' ? displayValue.toLocaleString() : displayValue}
          </div>
          {sublabel && (
            <div className="text-xs text-[var(--valo-text-dim)] mt-1">{sublabel}</div>
          )}
        </div>
        <div
          className="p-2.5 rounded-lg transition-transform duration-300 group-hover:scale-110"
          style={{ backgroundColor: `${color}12`, color }}
        >
          {icon}
        </div>
      </div>
    </div>
  );
}

interface StatsCardsProps {
  totalJobs: number;
  appliedJobs: number;
  pendingJobs: number;
  failedJobs: number;
  level?: number;
  streak?: number;
}

export default function StatsCards({
  totalJobs,
  appliedJobs,
  pendingJobs,
  failedJobs,
  level = 1,
  streak = 0,
}: StatsCardsProps) {
  return (
    <div className="grid grid-cols-4 gap-4 mb-6" data-gsap="stagger">
      <StatCard
        label="Total Jobs Found"
        value={totalJobs}
        icon={<TargetIcon className="w-7 h-7" />}
        color="#00D9FF"
        colorName="cyan"
        sublabel="In database"
        delay={0}
      />
      <StatCard
        label="Applications Sent"
        value={appliedJobs}
        icon={<CheckShieldIcon className="w-7 h-7" />}
        color="#00FFA3"
        colorName="green"
        sublabel="Successfully deployed"
        delay={100}
      />
      <StatCard
        label="Pending"
        value={pendingJobs}
        icon={<ClockIcon className="w-7 h-7" />}
        color="#FFE500"
        colorName="yellow"
        sublabel="Ready to apply"
        delay={200}
      />
      <StatCard
        label="Current Streak"
        value={`${streak} days`}
        icon={<FlameIcon className="w-7 h-7" />}
        color="#FF4655"
        colorName="red"
        sublabel={streak >= 7 ? 'ON FIRE!' : streak >= 3 ? 'Keep it up!' : 'Start applying!'}
        delay={300}
      />
    </div>
  );
}
