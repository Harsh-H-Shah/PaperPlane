'use client';

import { useState, useEffect, useCallback } from 'react';

const TAGLINES = [
  'ESTABLISHING CONNECTION...',
  'LOADING RECON DATA...',
  'CALIBRATING SYSTEMS...',
  'MAPPING TARGETS...',
  'SYNCING INTEL...',
];

export default function LoadingScreen({ onComplete }: { onComplete: () => void }) {
  const [progress, setProgress] = useState(0);
  const [tagline] = useState(() => TAGLINES[Math.floor(Math.random() * TAGLINES.length)]);

  const stableOnComplete = useCallback(onComplete, [onComplete]);

  useEffect(() => {
    // Single RAF-based progress animation — no setInterval, no re-renders every 50ms
    const duration = 2400; // ms — fast but not jarring
    const start = performance.now();
    let raf: number;

    const tick = (now: number) => {
      const elapsed = now - start;
      const pct = Math.min(100, (elapsed / duration) * 100);
      // Use easeOutQuart for smooth deceleration
      const eased = 1 - Math.pow(1 - pct / 100, 4);
      setProgress(Math.floor(eased * 100));

      if (elapsed < duration) {
        raf = requestAnimationFrame(tick);
      } else {
        setProgress(100);
        setTimeout(stableOnComplete, 400);
      }
    };

    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [stableOnComplete]);

  return (
    <div className="loading-screen">
      {/* Subtle grid pattern — CSS only, no external image */}
      <div className="loading-grid" />
      
      {/* Center content */}
      <div className="loading-center">
        <h2 className="loading-title">PAPERPLANE</h2>
        <div className="loading-divider">
          <span className="loading-diamond" />
        </div>
        <p className="loading-tagline">{tagline}</p>
      </div>

      {/* Bottom progress */}
      <div className="loading-bottom">
        <div className="loading-info">
          <span className="loading-label">INITIALIZING</span>
          <span className="loading-percent">{progress}%</span>
        </div>
        <div className="loading-bar-track">
          <div 
            className="loading-bar-fill" 
            style={{ width: `${progress}%` }} 
          />
        </div>
      </div>

      <style jsx>{`
        .loading-screen {
          position: fixed;
          inset: 0;
          z-index: 100;
          background: #0a0a0f;
          display: flex;
          flex-direction: column;
          justify-content: center;
          align-items: center;
          color: white;
          overflow: hidden;
          animation: fadeIn 0.3s ease-out;
        }

        @keyframes fadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }

        .loading-grid {
          position: absolute;
          inset: 0;
          opacity: 0.04;
          background-image: 
            linear-gradient(rgba(255,70,85,0.3) 1px, transparent 1px),
            linear-gradient(90deg, rgba(255,70,85,0.3) 1px, transparent 1px);
          background-size: 60px 60px;
        }

        .loading-center {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 16px;
          animation: slideUp 0.6s ease-out both;
          animation-delay: 0.15s;
        }

        @keyframes slideUp {
          from { opacity: 0; transform: translateY(20px); }
          to { opacity: 1; transform: translateY(0); }
        }

        .loading-title {
          font-family: var(--font-teko), sans-serif;
          font-size: clamp(3rem, 8vw, 6rem);
          font-weight: 700;
          letter-spacing: 0.2em;
          background: linear-gradient(180deg, #fff 40%, rgba(255,255,255,0.4));
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          background-clip: text;
          line-height: 1;
          margin: 0;
        }

        .loading-divider {
          display: flex;
          align-items: center;
          gap: 12px;
          width: 200px;
        }
        .loading-divider::before, .loading-divider::after {
          content: '';
          flex: 1;
          height: 1px;
          background: linear-gradient(90deg, transparent, #ff4655, transparent);
        }

        .loading-diamond {
          width: 6px;
          height: 6px;
          background: #ff4655;
          transform: rotate(45deg);
          flex-shrink: 0;
        }

        .loading-tagline {
          font-family: var(--font-rajdhani), monospace;
          font-size: 0.8rem;
          letter-spacing: 0.3em;
          color: #ff4655;
          opacity: 0.9;
          animation: pulse 2s ease-in-out infinite;
          margin: 0;
        }

        @keyframes pulse {
          0%, 100% { opacity: 0.6; }
          50% { opacity: 1; }
        }

        .loading-bottom {
          position: absolute;
          bottom: 0;
          left: 0;
          right: 0;
          padding: 24px 48px 32px;
        }

        .loading-info {
          display: flex;
          justify-content: space-between;
          align-items: baseline;
          margin-bottom: 8px;
        }

        .loading-label {
          font-family: var(--font-teko), sans-serif;
          font-size: 1.2rem;
          letter-spacing: 0.15em;
          color: rgba(255,255,255,0.5);
        }

        .loading-percent {
          font-family: var(--font-rajdhani), monospace;
          font-size: 2rem;
          font-weight: 600;
          color: rgba(255,255,255,0.3);
        }

        .loading-bar-track {
          width: 100%;
          height: 3px;
          background: rgba(255,255,255,0.08);
          overflow: hidden;
        }

        .loading-bar-fill {
          height: 100%;
          background: #ff4655;
          box-shadow: 0 0 12px rgba(255,70,85,0.5);
          transition: width 0.1s linear;
          will-change: width;
        }
      `}</style>
    </div>
  );
}
