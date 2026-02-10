'use client';

import { useState } from 'react';
import { CombatHistoryItem } from '@/lib/api';

interface CombatHistoryProps {
  history: CombatHistoryItem[];
  onViewJob: (jobId: string) => void;
  onApplyJob: (jobId: string) => void;
  onMarkApplied?: (jobId: string) => void;
}

function getStatusClass(color: string): string {
  switch (color) {
    case 'green': return 'status-green';
    case 'yellow': return 'status-yellow';
    case 'red': return 'status-red';
    case 'orange': return 'status-orange';
    default: return 'status-gray';
  }
}

function getStatusIcon(status: string): string {
  switch (status) {
    case 'applied': return '✅';
    case 'new': return '🆕';
    case 'in_progress': return '⏳';
    case 'failed': return '❌';
    case 'needs_review': return '👀';
    default: return '📋';
  }
}

function formatTimeAgo(dateStr: string | null): string {
  if (!dateStr) return '';
  
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffDays = Math.floor(diffHours / 24);
  
  if (diffDays > 0) return `${diffDays}d ago`;
  if (diffHours > 0) return `${diffHours}h ago`;
  return 'Just now';
}

export default function CombatHistoryEnhanced({ history, onViewJob, onApplyJob, onMarkApplied }: CombatHistoryProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [filter, setFilter] = useState<string>('all');

  const filteredHistory = filter === 'all' 
    ? history 
    : history.filter(item => item.status === filter);

  const statusCounts = {
    all: history.length,
    new: history.filter(h => h.status === 'new').length,
    applied: history.filter(h => h.status === 'applied').length,
    failed: history.filter(h => h.status === 'failed').length,
  };

  return (
    <div className="tech-border bg-[var(--valo-gray)] rounded-lg overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-[var(--valo-gray-light)]">
        <div className="flex items-center gap-3">
          <h3 className="font-display text-lg font-bold tracking-wider text-[var(--valo-text)]">
            JOB TARGETS
          </h3>
          <span className="px-2 py-1 text-xs font-semibold bg-[var(--valo-cyan)] text-[var(--valo-dark)] rounded">
            {history.length}
          </span>
        </div>
        {/* Filter Tabs */}
        <div className="flex gap-1">
          {(['all', 'new', 'applied', 'failed'] as const).map(status => (
            <button
              key={status}
              onClick={() => setFilter(status)}
              className={`px-3 py-1 text-xs font-semibold rounded transition-all ${
                filter === status
                  ? 'bg-[var(--valo-cyan)] text-[var(--valo-dark)]'
                  : 'bg-[var(--valo-darker)] text-[var(--valo-text-dim)] hover:text-[var(--valo-text)]'
              }`}
            >
              {status.toUpperCase()} ({statusCounts[status]})
            </button>
          ))}
        </div>
      </div>
      
      {/* List */}
      <div className="divide-y divide-[var(--valo-gray-light)] max-h-[500px] overflow-y-auto">
        {filteredHistory.length === 0 ? (
          <div className="px-5 py-12 text-center">
            <div className="text-4xl mb-3">🎯</div>
            <div className="text-[var(--valo-text-dim)]">
              {filter === 'all' 
                ? 'No jobs found yet. Click "SCAN FOR JOBS" to discover opportunities.'
                : `No ${filter} jobs.`}
            </div>
          </div>
        ) : (
          filteredHistory.map((item, index) => (
            <div
              key={item.id}
              className="group animate-in slide-in-from-top-2"
              style={{ animationDelay: `${index * 50}ms` }}
            >
              {/* Main Row */}
              <div
                onClick={() => setExpandedId(expandedId === item.id ? null : item.id)}
                className="flex items-center justify-between px-5 py-4 hover:bg-[var(--valo-darker)] transition-all cursor-pointer"
              >
                <div className="flex items-center gap-4 flex-1 min-w-0">
                  {/* Status Icon */}
                  <div className="w-10 h-10 rounded-lg bg-[var(--valo-darker)] border border-[var(--valo-gray-light)] flex items-center justify-center text-xl flex-shrink-0 group-hover:border-[var(--valo-cyan)] transition-colors">
                    {getStatusIcon(item.status)}
                  </div>
                  
                  {/* Job Info */}
                  <div className="flex-1 min-w-0">
                    <div className="font-semibold text-[var(--valo-text)] group-hover:text-[var(--valo-cyan)] transition-colors truncate">
                      {item.title}
                    </div>
                    <div className="flex items-center gap-2 text-sm text-[var(--valo-text-dim)]">
                      <span className="truncate max-w-[200px]">{item.company}</span>
                      <span className="text-[var(--valo-gray-light)]">•</span>
                      <span className="text-[var(--valo-cyan)] uppercase text-xs">{item.source}</span>
                      <span className="text-[var(--valo-gray-light)]">•</span>
                      <span>{formatTimeAgo(item.discovered_at)}</span>
                    </div>
                  </div>
                </div>
                
                {/* Right Side */}
                <div className="flex items-center gap-3 flex-shrink-0">
                  <span className={`px-3 py-1 rounded text-xs font-semibold tracking-wider whitespace-nowrap ${getStatusClass(item.status_color)}`}>
                    {item.status_label}
                  </span>
                  {item.xp_reward > 0 && (
                    <span className="text-[var(--valo-green)] font-semibold text-sm whitespace-nowrap">
                      +{item.xp_reward} XP
                    </span>
                  )}
                  <svg 
                    className={`w-4 h-4 text-[var(--valo-text-dim)] transition-transform ${expandedId === item.id ? 'rotate-180' : ''}`}
                    fill="none" 
                    viewBox="0 0 24 24" 
                    stroke="currentColor"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </div>
              </div>
              
              {/* Expanded Details */}
              {expandedId === item.id && (
                <div className="px-5 py-4 bg-[var(--valo-darker)] border-t border-[var(--valo-gray-light)] animate-in slide-in-from-top-2">
                  <div className="flex items-center gap-3 flex-wrap">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onViewJob(item.id);
                      }}
                      className="px-4 py-2 bg-[var(--valo-cyan)] text-[var(--valo-dark)] rounded font-semibold hover:shadow-[0_0_15px_rgba(0,217,255,0.4)] transition-all text-sm active:scale-95"
                    >
                      VIEW DETAILS
                    </button>
                    {(item.status === 'new' || item.status === 'needs_review') && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onApplyJob(item.id);
                        }}
                        className="px-4 py-2 bg-[var(--valo-green)] text-[var(--valo-dark)] rounded font-semibold hover:shadow-[0_0_15px_rgba(0,255,163,0.4)] transition-all text-sm active:scale-95"
                      >
                        APPLY NOW
                      </button>
                    )}
                    <a
                      href={`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080'}/api/jobs/${item.id}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      onClick={(e) => e.stopPropagation()}
                      className="px-4 py-2 bg-[var(--valo-gray-light)] text-[var(--valo-text)] rounded font-semibold hover:bg-opacity-80 transition-all text-sm"
                    >
                      OPEN LINK
                    </a>
                    {onMarkApplied && item.status !== 'applied' && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onMarkApplied(item.id);
                        }}
                        className="px-4 py-2 bg-transparent border border-[var(--valo-green)] text-[var(--valo-green)] rounded font-semibold hover:bg-[var(--valo-green)] hover:text-[var(--valo-dark)] transition-all text-sm active:scale-95 whitespace-nowrap"
                      >
                        MARK APPLIED
                      </button>
                    )}
                    <div className="flex-1" />
                    <span className="text-sm text-[var(--valo-text-dim)]">
                      Source: <span className="text-[var(--valo-cyan)]">{item.source.toUpperCase()}</span>
                    </span>
                  </div>
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
