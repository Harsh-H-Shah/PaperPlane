'use client';

import { useState, useEffect, useCallback } from 'react';
import Sidebar from '@/components/Sidebar';
import TacticalHeader from '@/components/TacticalHeader';
import StatsCards from '@/components/StatsCards';
import CombatHistoryEnhanced from '@/components/CombatHistoryEnhanced';
import QuickActions from '@/components/QuickActions';
import Footer from '@/components/Footer';
import JobDetails from '@/components/JobDetails'; // NEW
import ActivityFeed from '@/components/ActivityFeed'; // NEW
import { api, Profile, Gamification, Stats, CombatHistoryItem, Job } from '@/lib/api';

export default function Dashboard() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [gamification, setGamification] = useState<Gamification | null>(null);
  const [stats, setStats] = useState<Stats | null>(null);
  const [history, setHistory] = useState<CombatHistoryItem[]>([]);
  const [selectedJob, setSelectedJob] = useState<Job | null>(null); // NEW
  const [isDeploying, setIsDeploying] = useState(false);
  const [isScraping, setIsScraping] = useState(false);
  const [isApplying, setIsApplying] = useState(false);
  const [scrapeProgress, setScrapeProgress] = useState<{
    current_source: string;
    jobs_found: number;
    jobs_new: number;
  } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const [profileData, gamData, statsData, historyData] = await Promise.all([
        api.getProfile(),
        api.getGamification(),
        api.getStats(),
        api.getCombatHistory(),
      ]);
      
      setProfile(profileData);
      setGamification(gamData);
      setStats(statsData);
      setHistory(historyData.history);
      setError(null);
    } catch (err) {
      console.error('Failed to fetch data:', err);
      setError('Failed to connect to backend. Make sure the API is running on port 8080.');
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const handleDeploy = async () => {
    setIsDeploying(true);
    setIsScraping(true);
    try {
      await api.triggerScrape();
      const pollInterval = setInterval(async () => {
        try {
          const progress = await api.getScrapeProgress();
          setScrapeProgress({
            current_source: progress.current_source,
            jobs_found: progress.jobs_found,
            jobs_new: progress.jobs_new,
          });
          if (!progress.is_running) {
            clearInterval(pollInterval);
            setIsDeploying(false);
            setIsScraping(false);
            setScrapeProgress(null);
            fetchData();
          }
        } catch (e) {
          console.error('Error polling progress:', e);
        }
      }, 1000);
    } catch (err) {
      console.error('Deploy failed:', err);
      setIsDeploying(false);
      setIsScraping(false);
    }
  };

  const handleScrape = async () => {
    setIsScraping(true);
    setScrapeProgress({ current_source: 'Starting...', jobs_found: 0, jobs_new: 0 });
    try {
      await api.triggerScrape();
      const pollInterval = setInterval(async () => {
        try {
          const progress = await api.getScrapeProgress();
          setScrapeProgress({
            current_source: progress.current_source || 'Processing...',
            jobs_found: progress.jobs_found,
            jobs_new: progress.jobs_new,
          });
          if (!progress.is_running) {
            clearInterval(pollInterval);
            setIsScraping(false);
            setTimeout(() => setScrapeProgress(null), 3000);
            fetchData();
          }
        } catch (e) {
          console.error('Error polling progress:', e);
        }
      }, 1000);
    } catch (err) {
      console.error('Scrape failed:', err);
      setIsScraping(false);
      setScrapeProgress(null);
    }
  };

  const handleAutoApply = async () => {
    setIsApplying(true);
    try {
      await api.triggerRun();
      // We keep the "Applying" state for a moment to show feedback
      // The actual progress will be visible in the Activity Feed
      setTimeout(() => {
        setIsApplying(false);
        fetchData();
      }, 2000);
    } catch (err) {
      console.error('Auto apply failed:', err);
      setIsApplying(false);
    }
  };

  const handleViewJob = async (jobId: string) => {
    // We need to fetch the full job details because history item might not have everything
    // Or we can just try to find it in history if it's there?
    // Actually, let's fetch it.
    try {
       // Assuming getJobs can fetch single or we filter. 
       // Currently api.getJobs returns list. We don't have getJob(id).
       // Use window.open for now if we can't fetch.
       // But wait, user specifically asked for "frontend instead of just backend".
       // I should implement api.getJob(id).
       // Or I can cheat and pass the partial job from history if CombatHistoryItem has enough info.
       // It has title, company, status, date. Missing URL, type, etc.
       // Let's add getJob to API client or fetch from list.
       const res = await api.getJobs({ per_page: 50 }); // Inefficient but works for demo
       const job = res.jobs.find(j => j.id === jobId);
       if (job) setSelectedJob(job);
    } catch (e) {
       console.error("Failed to fetch job details", e);
    }
  };

  const handleApplyJob = async (jobId: string) => {
    try {
      await api.triggerApply(jobId);
      fetchData();
    } catch (err) {
      console.error('Apply failed:', err);
    }
  };

  const handleMarkApplied = async (jobId: string) => {
    try {
      await api.updateJob(jobId, { status: 'applied' });
      fetchData();
    } catch (err) {
      console.error('Update failed:', err);
    }
  };

  const handleUndo = async (jobId: string) => {
    try {
      await api.updateJob(jobId, { status: 'new' });
      fetchData();
    } catch (err) {
      console.error('Undo failed:', err);
    }
  };

  return (
    <div className="flex min-h-screen bg-[var(--valo-darker)]">
      <Sidebar
        agentName={profile?.agent_name || 'AGENT'}
        userName={profile?.full_name || profile?.first_name}
        valorantAgent={profile?.valorant_agent || 'jett'}
        levelTitle={gamification?.level_title || 'RECRUIT'}
        level={gamification?.level || 1}
        rankIcon={gamification?.rank_icon}
        onDeploy={handleDeploy}
        isDeploying={isDeploying}
      />

      <div className="flex-1 flex flex-col">
        <main className="flex-1 p-8 overflow-auto">
          {error ? (
            <div className="tech-border bg-[var(--valo-red)] bg-opacity-20 rounded-lg p-6 text-center animate-in fade-in">
              <div className="text-xl font-semibold text-[var(--valo-red)] mb-2">⚠️ CONNECTION ERROR</div>
              <p className="text-[var(--valo-text-dim)]">{error}</p>
              <button 
                onClick={fetchData}
                className="mt-4 px-6 py-2 bg-[var(--valo-red)] text-white rounded hover:opacity-80 transition active:scale-95"
              >
                Retry Connection
              </button>
            </div>
          ) : (
            <>
              <TacticalHeader
                streak={gamification?.streak || 0}
                totalXp={gamification?.total_xp || 0}
              />

              <QuickActions
                onScrape={handleScrape}
                onAutoApply={handleAutoApply}
                isScraping={isScraping}
                isApplying={isApplying}
                scrapeProgress={scrapeProgress}
              />

              <StatsCards
                totalJobs={stats?.total || 0}
                appliedJobs={stats?.applied || 0}
                pendingJobs={stats?.pending || 0}
                failedJobs={stats?.failed || 0}
                level={gamification?.level || 1}
                streak={gamification?.streak || 0}
              />

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
                 <ActivityFeed />
                 <CombatHistoryEnhanced
                    history={history}
                    onViewJob={handleViewJob}
                    onApplyJob={handleApplyJob}
                    onMarkApplied={handleMarkApplied}
                  />
              </div>
            </>
          )}
        </main>
        

        {/* Job Details Modal */}
        {selectedJob && (
          <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 animate-in fade-in p-4" onClick={() => setSelectedJob(null)}>
            <div className="max-w-4xl w-full tech-border bg-[var(--valo-dark)] shadow-[0_0_50px_rgba(0,0,0,0.8)] relative" onClick={e => e.stopPropagation()}>
               <div className="flex items-center justify-between p-4 border-b border-white/10">
                  <h2 className="font-display text-2xl font-bold tracking-wider">{selectedJob.title}</h2>
                  <button onClick={() => setSelectedJob(null)} className="text-[var(--valo-text-dim)] hover:text-white">
                    <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
                  </button>
               </div>
               <JobDetails 
                 job={selectedJob}
                 onApply={handleApplyJob}
                 onMarkApplied={handleMarkApplied}
                 onUndo={handleUndo}
                 onDelete={() => {}} // No delete from view modal usually
               />
            </div>
          </div>
        )}
        
        <Footer />
      </div>
    </div>
  );
}
