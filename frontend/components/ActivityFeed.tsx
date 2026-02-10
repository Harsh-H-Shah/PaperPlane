"use client";

import { useEffect, useState, useRef } from "react";
import { ScrollArea } from "@/components/ui/scroll-area";

export default function ActivityFeed() {
  const [logs, setLogs] = useState<string[]>([]);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const fetchLogs = async () => {
      try {
        const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';
        const res = await fetch(`${apiBase}/api/activity?lines=100`);
        if (res.ok) {
          const data = await res.json();
          setLogs(data.logs);
        }
      } catch (e) {
        console.error("Failed to fetch logs", e);
      }
    };

    fetchLogs();
    const interval = setInterval(fetchLogs, 2000);

    return () => clearInterval(interval);
  }, []);

  // Smart auto-scroll
  useEffect(() => {
    if (scrollRef.current) {
        const viewport = scrollRef.current.querySelector('[data-radix-scroll-area-viewport]');
        if (viewport) {
             const isAtBottom = viewport.scrollHeight - viewport.scrollTop - viewport.clientHeight < 100;
             
             if (isAtBottom || logs.length < 5) {
                 viewport.scrollTo({ top: viewport.scrollHeight, behavior: 'smooth' });
             }
        }
    }
  }, [logs]);

  return (
    <div className="h-[400px] flex flex-col tech-border overflow-hidden relative" data-gsap="fade-up">
      {/* Header */}
      <div className="px-4 py-3 border-b border-white/10 flex items-center justify-between bg-black/40">
        <div className="flex items-center gap-2">
          <svg className="w-4 h-4 text-[var(--valo-green)]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
          <span className="text-xs font-bold uppercase tracking-widest text-[var(--valo-text-dim)]">
            Live Activity Feed
          </span>
        </div>
        {/* Live indicator */}
        <div className="flex items-center gap-2 px-2 py-1 bg-black/50 backdrop-blur-sm border border-white/5">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[var(--valo-green)] opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-[var(--valo-green)]"></span>
          </span>
          <span className="text-[10px] font-semibold text-[var(--valo-green)] uppercase tracking-widest">Live</span>
        </div>
      </div>

      {/* Terminal body — black background */}
      <div className="flex-1 bg-black font-mono text-xs overflow-hidden relative">
        <ScrollArea className="h-full w-full p-4" ref={scrollRef}>
          <div className="flex flex-col gap-1">
            {logs.length === 0 && (
                <div className="text-[var(--valo-text-dim)] italic">Waiting for activity...</div>
            )}
            {logs.map((log, i) => {
                // Heuristic coloring
                let colorClass = "text-[#8B9AB0]";
                if (log.includes("ERROR") || log.includes("❌")) colorClass = "text-[var(--valo-red)]";
                else if (log.includes("WARNING") || log.includes("⚠️")) colorClass = "text-[var(--valo-yellow)]";
                else if (log.includes("SUCCESS") || log.includes("✅") || log.includes("🚀")) colorClass = "text-[var(--valo-green)] font-bold";
                else if (log.includes("INFO")) colorClass = "text-[var(--valo-cyan)]";

                return (
                    <div key={i} className={`${colorClass} whitespace-pre-wrap break-all leading-5`}>
                        <span className="text-[var(--valo-text-dim)]/50 mr-2 select-none">{String(i + 1).padStart(3, ' ')}</span>
                        {log}
                    </div>
                );
            })}
             <div className="h-4" />
          </div>
        </ScrollArea>

        {/* Scanline overlay for terminal feel */}
        <div className="absolute inset-0 pointer-events-none opacity-[0.03]" style={{
          background: 'repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,255,163,0.1) 2px, rgba(0,255,163,0.1) 4px)'
        }} />
      </div>
    </div>
  );
}
