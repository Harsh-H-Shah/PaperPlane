"use client";

import { useEffect, useState, useRef } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Activity, Terminal } from "lucide-react";

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
    const interval = setInterval(fetchLogs, 2000); // Poll every 2s

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
    <Card className="h-[400px] flex flex-col shadow-lg border-2 border-slate-200 dark:border-slate-800">
      <CardHeader className="pb-2 border-b bg-slate-50 dark:bg-slate-900/50">
        <CardTitle className="flex items-center gap-2 text-sm font-bold uppercase tracking-wider text-slate-500">
          <Terminal className="h-4 w-4" />
          Live Activity Feed
        </CardTitle>
      </CardHeader>
      <CardContent className="flex-1 p-0 bg-slate-950 text-slate-300 font-mono text-xs overflow-hidden relative">
        <ScrollArea className="h-full w-full p-4" ref={scrollRef}>
          <div className="flex flex-col gap-1">
            {logs.length === 0 && (
                <div className="text-slate-600 italic">Waiting for activity...</div>
            )}
            {logs.map((log, i) => {
                // Heuristic coloring
                let colorClass = "text-slate-300";
                if (log.includes("ERROR") || log.includes("❌")) colorClass = "text-red-400";
                else if (log.includes("WARNING") || log.includes("⚠️")) colorClass = "text-yellow-400";
                else if (log.includes("SUCCESS") || log.includes("✅") || log.includes("🚀")) colorClass = "text-green-400 font-bold";
                else if (log.includes("INFO")) colorClass = "text-blue-300";

                return (
                    <div key={i} className={`${colorClass} whitespace-pre-wrap break-all`}>
                        {log}
                    </div>
                );
            })}
             {/* Anchor for auto-scroll */}
             <div className="h-4" />
          </div>
        </ScrollArea>
        {/* Status indicator dot */}
        <div className="absolute top-2 right-2 flex items-center gap-2 px-2 py-1 bg-slate-900/80 rounded-full border border-slate-800 backdrop-blur-sm">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
            </span>
            <span className="text-[10px] font-semibold text-green-500 uppercase tracking-widest">Live</span>
        </div>
      </CardContent>
    </Card>
  );
}
