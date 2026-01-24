import { Job } from '@/lib/api';

interface JobDetailsProps {
  job: Job;
  onApply: (id: string) => void;
  onMarkApplied: (id: string) => void;
  onUndo: (id: string) => void;
  onDelete: (id: string) => void;
}

export default function JobDetails({ job, onApply, onMarkApplied, onUndo, onDelete }: JobDetailsProps) {
  return (
    <div className="px-6 pb-6 pt-0 border-t border-[var(--valo-gray-light)]/20 bg-[var(--valo-dark)]/30 animate-in slide-in-from-top-2">
      <div className="pt-4">
        {/* Job Stats/Tags Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
           <div className="bg-[var(--valo-darker)] p-3 border border-white/5 relative overflow-hidden group">
              <div className="absolute top-0 right-0 p-1 opacity-10 group-hover:opacity-20 transition-opacity">
                <svg className="w-12 h-12" fill="currentColor" viewBox="0 0 24 24"><path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10 10-4.5 10-10S17.5 2 12 2zm0 18c-4.4 0-8-3.6-8-8s3.6-8 8-8 8 3.6 8 8-3.6 8-8 8z"/></svg>
              </div>
              <label className="text-[10px] text-[var(--valo-text-dim)] tracking-widest uppercase block mb-1">DISCOVERED</label>
              <div className="font-mono text-sm">{job.discovered_at ? new Date(job.discovered_at).toLocaleDateString() : 'N/A'}</div>
           </div>
           
           <div className="bg-[var(--valo-darker)] p-3 border border-white/5 relative overflow-hidden group">
              <label className="text-[10px] text-[var(--valo-text-dim)] tracking-widest uppercase block mb-1">POSTED</label>
              <div className="font-mono text-sm text-[var(--valo-cyan)]">
                {job.posted_date ? new Date(job.posted_date).toLocaleDateString() : 'UNKNOWN'}
              </div>
           </div>
           
           <div className="bg-[var(--valo-darker)] p-3 border border-white/5 relative overflow-hidden group">
              <label className="text-[10px] text-[var(--valo-text-dim)] tracking-widest uppercase block mb-1">TYPE</label>
              <div className="font-mono text-sm">{job.application_type?.toUpperCase() || 'EASY APPLY'}</div>
           </div>
           
           <div className="bg-[var(--valo-darker)] p-3 border border-white/5 relative overflow-hidden group">
              <label className="text-[10px] text-[var(--valo-text-dim)] tracking-widest uppercase block mb-1">MATCH SCORE</label>
              <div className="font-mono text-sm text-[var(--valo-green)] flex items-center gap-2">
                HIGH PRIORITY
                <span className="w-2 h-2 rounded-full bg-[var(--valo-green)] animate-pulse"></span>
              </div>
           </div>
           
           <div className="bg-[var(--valo-darker)] p-3 border border-white/5 relative overflow-hidden group">
              <label className="text-[10px] text-[var(--valo-text-dim)] tracking-widest uppercase block mb-1">STATUS</label>
              <div className={`font-mono text-sm font-bold ${
                job.status === 'applied' ? 'text-[var(--valo-green)]' :
                job.status === 'failed' ? 'text-[var(--valo-red)]' :
                'text-[var(--valo-yellow)]'
              }`}>
                {job.status.toUpperCase().replace('_', ' ')}
              </div>
           </div>
        </div>
        
        {/* Actions Bar */}
        <div className="flex flex-wrap gap-3">
          <a
            href={job.url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex-1 py-3 px-4 bg-[var(--valo-cyan)] text-[var(--valo-dark)] font-bold text-center hover:bg-cyan-300 hover:scale-[1.02] active:scale-95 transition-all duration-200 tech-button-solid clip-path-button shadow-[0_0_15px_rgba(0,255,255,0.1)] hover:shadow-[0_0_20px_rgba(0,255,255,0.3)]"
            style={{ clipPath: 'polygon(10px 0, 100% 0, 100% calc(100% - 10px), calc(100% - 10px) 100%, 0 100%, 0 10px)' }}
          >
            VIEW MISSION
          </a>
          
          {(job.status === 'new' || job.status === 'needs_review' || job.status === 'failed') && (
            <button
              onClick={() => onApply(job.id)}
              className={`flex-1 py-3 px-4 font-bold text-center hover:scale-[1.02] active:scale-95 transition-all duration-200 tech-button-solid shadow-lg ${
                job.status === 'failed' ? 'bg-[var(--valo-red)] text-white hover:bg-red-400' : 'bg-[var(--valo-green)] text-[var(--valo-dark)] hover:bg-green-400'
              }`}
              style={{ clipPath: 'polygon(10px 0, 100% 0, 100% calc(100% - 10px), calc(100% - 10px) 100%, 0 100%, 0 10px)' }}
            >
              {job.status === 'failed' ? 'RETRY DEPLOY' : 'DEPLOY AGENT'}
            </button>
          )}
          
          {job.status !== 'applied' && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onMarkApplied(job.id);
              }}
              className="flex-1 py-3 px-4 border border-[var(--valo-green)] text-[var(--valo-green)] font-bold text-center hover:bg-[var(--valo-green)] hover:text-[var(--valo-dark)] active:scale-95 transition tech-button"
            >
              MARK COMPLETE
            </button>
          )}
          
          <button
            onClick={() => job.status === 'applied' ? onUndo(job.id) : onDelete(job.id)}
            className={`flex-1 py-3 px-4 border font-bold text-center active:scale-95 transition tech-button ${
                job.status === 'applied' 
                ? 'border-[var(--valo-yellow)] text-[var(--valo-yellow)] hover:bg-[var(--valo-yellow)] hover:text-black'
                : 'border-[var(--valo-red)] text-[var(--valo-red)] hover:bg-[var(--valo-red)] hover:text-white'
            }`}
          >
            {job.status === 'applied' ? 'REVOKE' : 'ABORT'}
          </button>
        </div>
      </div>
    </div>
  );
}
