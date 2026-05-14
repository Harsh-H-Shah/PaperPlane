'use client';

import { useEffect, useState } from 'react';

interface LevelUpOverlayProps {
  level: number;
  title: string;
  rankIcon?: string;
  onDismiss: () => void;
}

export default function LevelUpOverlay({ level, title, rankIcon, onDismiss }: LevelUpOverlayProps) {
  const [show, setShow] = useState(false);

  useEffect(() => {
    setShow(true);
    // Auto dismiss after animation if desired, or let user click
  }, []);

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center bg-black/90 backdrop-blur-sm cursor-pointer animate-in fade-in duration-300 px-4"
      onClick={onDismiss}
    >
      <div className="relative w-full max-w-4xl text-center">
        {/* Background Burst */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[300px] h-[300px] sm:w-[600px] sm:h-[600px] bg-[var(--valo-green)]/20 rounded-full blur-[80px] sm:blur-[100px] animate-pulse" />

        {/* Rank Icon */}
        <div className="relative z-10 mb-6 sm:mb-8 animate-in zoom-in-50 duration-[1.5s] delay-100 flex justify-center">
           <div className="w-32 h-32 sm:w-40 sm:h-40 md:w-48 md:h-48 relative">
              <div className="absolute inset-0 bg-[var(--valo-green)] blur-xl opacity-50 animate-pulse" />
              {/* Fallback circle if no icon */}
              {rankIcon ? (
                  <img src={rankIcon} alt="Rank" className="w-full h-full object-contain drop-shadow-[0_0_30px_rgba(0,255,163,0.6)]" />
              ) : (
                  <div className="w-full h-full rounded-full border-4 border-[var(--valo-green)] flex items-center justify-center text-6xl">
                    {level}
                  </div>
              )}
           </div>
        </div>

        {/* Text */}
        <div className="relative z-10 space-y-3 sm:space-y-4">
             <h2 className="font-display text-xl sm:text-3xl md:text-4xl text-[var(--valo-text-dim)] tracking-[0.3em] sm:tracking-[0.5em] animate-in slide-in-from-bottom-8 fade-in duration-1000 delay-300">
                PROMOTION
             </h2>
             <h1 className="font-display text-5xl sm:text-7xl md:text-9xl font-bold text-white tracking-tighter drop-shadow-[0_4px_0_var(--valo-dark)] animate-in scale-150 duration-500 delay-500 mix-blend-overlay">
                RUBY
             </h1>
              <h1 className="font-display text-4xl sm:text-6xl md:text-8xl font-bold text-[var(--valo-green)] tracking-tighter absolute top-8 sm:top-12 md:top-14 left-0 right-0 animate-in scale-100 duration-500 delay-500 break-all px-2">
                {title.toUpperCase()}
             </h1>

             <div className="h-[2px] w-48 sm:w-64 bg-gradient-to-r from-transparent via-[var(--valo-green)] to-transparent mx-auto mt-6 sm:mt-8 animate-in width-0 duration-1000 delay-700" />

             <p className="font-mono text-xs sm:text-base text-[var(--valo-text)] mt-4 animate-in fade-in duration-1000 delay-1000 px-2">
                LEVEL {level} UNLOCKED // NEW CLEARANCE GRANTED
             </p>
        </div>

        {/* Click to continue */}
        <div className="absolute -bottom-16 sm:-bottom-24 left-0 right-0 text-center animate-pulse opacity-50 text-xs sm:text-sm">
            [ CLICK TO CONTINUE ]
        </div>
      </div>
    </div>
  );
}
