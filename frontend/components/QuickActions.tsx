'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@/lib/auth';

interface QuickActionsProps {
  onScrape: () => void;
  onAutoApply: () => void;
  isScraping?: boolean;
  isApplying?: boolean;
  scrapeProgress?: {
    current_source: string;
    jobs_found: number;
    jobs_new: number;
  } | null;
  applyProgress?: {
    current_job: string;
    applied_count: number;
    total_count: number;
  } | null;
}

export default function QuickActions({ 
  onScrape, 
  onAutoApply, 
  isScraping, 
  isApplying,
  scrapeProgress,
  applyProgress 
}: QuickActionsProps) {
  const { isAdmin } = useAuth();
  const [showConfirmApply, setShowConfirmApply] = useState(false);
  const [pulseEffect, setPulseEffect] = useState(false);

  // Trigger pulse animation when new jobs are found
  useEffect(() => {
    if (scrapeProgress && scrapeProgress.jobs_new > 0) {
      setPulseEffect(true);
      const timer = setTimeout(() => setPulseEffect(false), 1000);
      return () => clearTimeout(timer);
    }
  }, [scrapeProgress?.jobs_new]);

  return (
    <>
      <div className="tech-border bg-[var(--valo-gray)] rounded-lg p-5 mb-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-display text-lg font-bold tracking-wider text-[var(--valo-text)]">
            OPERATIONS
          </h3>
          <div className="flex items-center gap-2">
            <span className={`w-2 h-2 rounded-full ${isScraping || isApplying ? 'bg-[var(--valo-green)] animate-pulse' : 'bg-[var(--valo-gray-light)]'}`}></span>
            <span className="text-xs text-[var(--valo-text-dim)]">
              {isScraping || isApplying ? 'ACTIVE' : 'STANDBY'}
            </span>
          </div>
        </div>

        {/* Main Action Buttons */}
        <div className="grid grid-cols-2 gap-4 mb-4">
          {/* Scan Jobs Button */}
          <button
            onClick={onScrape}
            disabled={isScraping || isApplying || !isAdmin}
            className={`relative p-8 rounded-lg transition-all duration-300 flex flex-col items-center text-center overflow-hidden group tech-button ${
              !isAdmin
                ? 'bg-[var(--valo-gray-light)] cursor-not-allowed opacity-60'
                : isScraping 
                  ? 'bg-[var(--valo-cyan)]/20 border-2 border-[var(--valo-cyan)]' 
                  : isScraping || isApplying
                    ? 'bg-[var(--valo-gray-light)] cursor-not-allowed opacity-50'
                    : 'bg-[var(--valo-dark)] hover:bg-[var(--valo-cyan)]/10 hover:border-[var(--valo-cyan)]'
            }`}
          >
            {isScraping && (
              <div className="absolute inset-0 bg-gradient-to-r from-transparent via-[var(--valo-cyan)]/20 to-transparent animate-shimmer"></div>
            )}
            <div className={`p-4 rounded-full mb-4 transition-all duration-300 ${isScraping ? 'bg-[var(--valo-cyan)]/20 animate-pulse' : 'bg-[var(--valo-cyan)]/10 group-hover:bg-[var(--valo-cyan)] group-hover:text-[var(--valo-dark)]'}`}>
               {isScraping ? (
                 <div className="w-8 h-8 border-2 border-[var(--valo-cyan)] border-t-transparent rounded-full animate-spin"></div>
               ) : (
                 <svg className="w-8 h-8 text-[var(--valo-cyan)] group-hover:text-[var(--valo-dark)] transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
               )}
            </div>
            
            <span className="font-display font-bold text-2xl tracking-widest text-[var(--valo-text)] group-hover:text-[var(--valo-cyan)] transition-colors">
              {isScraping ? 'SCANNING...' : 'RECON'}
            </span>
            <span className="text-xs text-[var(--valo-text-dim)] uppercase tracking-wider mt-2 group-hover:text-[var(--valo-text)]">
              {!isAdmin ? '🔒 Admin Only' : 'Identify Targets'}
            </span>
          </button>

          {/* Auto Apply Button */}
          <button
            onClick={() => setShowConfirmApply(true)}
            disabled={isScraping || isApplying || !isAdmin}
            className={`relative p-8 rounded-lg transition-all duration-300 flex flex-col items-center text-center overflow-hidden group tech-button ${
              !isAdmin
                ? 'bg-[var(--valo-gray-light)] cursor-not-allowed opacity-60'
                : isApplying 
                  ? 'bg-[var(--valo-green)]/20 border-2 border-[var(--valo-green)]' 
                  : isScraping || isApplying
                    ? 'bg-[var(--valo-gray-light)] cursor-not-allowed opacity-50'
                    : 'bg-[var(--valo-dark)] hover:bg-[var(--valo-green)]/10 hover:border-[var(--valo-green)]'
            }`}
          >
            {isApplying && (
              <div className="absolute inset-0 bg-gradient-to-r from-transparent via-[var(--valo-green)]/20 to-transparent animate-shimmer"></div>
            )}
            <div className={`p-4 rounded-full mb-4 transition-all duration-300 ${isApplying ? 'bg-[var(--valo-green)]/20 animate-pulse' : 'bg-[var(--valo-green)]/10 group-hover:bg-[var(--valo-green)] group-hover:text-[var(--valo-dark)]'}`}>
               {isApplying ? (
                 <div className="w-8 h-8 border-2 border-[var(--valo-green)] border-t-transparent rounded-full animate-spin"></div>
               ) : (
                 <svg className="w-8 h-8 text-[var(--valo-green)] group-hover:text-[var(--valo-dark)] transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
               )}
            </div>
            
            <span className="font-display font-bold text-2xl tracking-widest text-[var(--valo-text)] group-hover:text-[var(--valo-green)] transition-colors">
              {isApplying ? 'DEPLOYING...' : 'ENGAGE'}
            </span>
            <span className="text-xs text-[var(--valo-text-dim)] uppercase tracking-wider mt-2 group-hover:text-[var(--valo-text)]">
              {!isAdmin ? '🔒 Admin Only' : 'Execute Protocols'}
            </span>
          </button>
        </div>

        {/* Real-time Progress Display */}
        {(isScraping && scrapeProgress) && (
          <div className="bg-[var(--valo-darker)] rounded-lg p-4 border border-[var(--valo-cyan)] animate-in slide-in-from-top-2">
            <div className="flex items-center justify-between mb-3">
              <span className="font-display font-semibold text-[var(--valo-cyan)] tracking-wider">
                SCAN PROGRESS
              </span>
              <span className="text-xs text-[var(--valo-text-dim)]">
                {scrapeProgress.current_source || 'Initializing...'}
              </span>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="text-center">
                <div className={`font-display text-3xl font-bold text-[var(--valo-yellow)] ${pulseEffect ? 'animate-bounce' : ''}`}>
                  {scrapeProgress.jobs_found}
                </div>
                <div className="text-xs text-[var(--valo-text-dim)]">JOBS FOUND</div>
              </div>
              <div className="text-center">
                <div className={`font-display text-3xl font-bold text-[var(--valo-green)] ${pulseEffect ? 'animate-bounce' : ''}`}>
                  {scrapeProgress.jobs_new}
                </div>
                <div className="text-xs text-[var(--valo-text-dim)]">NEW JOBS</div>
              </div>
            </div>
          </div>
        )}

        {(isApplying && applyProgress) && (
          <div className="bg-[var(--valo-darker)] rounded-lg p-4 border border-[var(--valo-green)] animate-in slide-in-from-top-2">
            <div className="flex items-center justify-between mb-3">
              <span className="font-display font-semibold text-[var(--valo-green)] tracking-wider">
                APPLICATION PROGRESS
              </span>
              <span className="text-sm text-[var(--valo-text)]">
                {applyProgress.applied_count} / {applyProgress.total_count}
              </span>
            </div>
            <div className="w-full h-2 bg-[var(--valo-gray)] rounded-full overflow-hidden">
              <div 
                className="h-full bg-[var(--valo-green)] transition-all duration-500"
                style={{ width: `${(applyProgress.applied_count / applyProgress.total_count) * 100}%` }}
              ></div>
            </div>
            {applyProgress.current_job && (
              <div className="mt-2 text-sm text-[var(--valo-text-dim)] truncate">
                Current: {applyProgress.current_job}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Confirmation Modal */}
      {showConfirmApply && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 animate-in fade-in">
          <div className="tech-border bg-[var(--valo-gray)] rounded-lg p-6 max-w-md mx-4 animate-in zoom-in-95">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-12 h-12 rounded-lg bg-[var(--valo-red)] bg-opacity-20 flex items-center justify-center">
                <span className="text-2xl">⚡</span>
              </div>
              <h3 className="font-display text-xl font-bold text-[var(--valo-text)]">
                CONFIRM AUTO APPLY
              </h3>
            </div>
            <p className="text-[var(--valo-text-dim)] mb-6">
              This will automatically fill and submit applications to pending job listings. 
              Applications will be submitted on your behalf.
            </p>
            <div className="flex gap-4">
              <button
                onClick={() => setShowConfirmApply(false)}
                className="flex-1 py-3 rounded-lg bg-[var(--valo-gray-light)] text-[var(--valo-text)] font-semibold hover:bg-opacity-80 transition-all active:scale-95"
              >
                CANCEL
              </button>
              <button
                onClick={() => {
                  setShowConfirmApply(false);
                  onAutoApply();
                }}
                className="flex-1 py-3 rounded-lg bg-[var(--valo-green)] text-[var(--valo-dark)] font-semibold hover:shadow-[0_0_20px_rgba(0,255,163,0.5)] transition-all active:scale-95"
              >
                START APPLYING
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
