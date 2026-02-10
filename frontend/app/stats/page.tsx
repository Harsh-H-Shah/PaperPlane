'use client';

import { useState, useEffect } from 'react';
import Sidebar from '@/components/Sidebar';
import LevelProgress from '@/components/LevelProgress';
import LevelUpOverlay from '@/components/LevelUpOverlay';
import StatsCharts from '@/components/StatsCharts';
import WeaponShowcase from '@/components/WeaponShowcase';
import Footer from '@/components/Footer';
import { api, Profile, Gamification, Stats } from '@/lib/api';

export default function StatsPage() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [gamification, setGamification] = useState<Gamification | null>(null);
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [profileData, gamData, statsData] = await Promise.all([
          api.getProfile(),
          api.getGamification(),
          api.getStats(),
        ]);
        setProfile(profileData);
        setGamification(gamData);
        setStats(statsData);
      } catch (err) {
        console.error('Failed to fetch:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const [showLevelUp, setShowLevelUp] = useState(false);

  const handleSimulateLevelUp = () => {
     setShowLevelUp(true);
  };

  return (
    <div className="flex min-h-screen bg-[var(--valo-darker)]">
      {/* Level Up Overlay */}
      {showLevelUp && gamification && (
        <LevelUpOverlay
           level={gamification.level + 1}
           title="PROMOTION"
           rankIcon={gamification.rank_icon}
           onDismiss={() => setShowLevelUp(false)}
        />
      )}

      <Sidebar
        agentName={profile?.agent_name || 'AGENT'}
        userName={profile?.full_name || profile?.first_name}
        valorantAgent={profile?.valorant_agent || 'jett'}
        levelTitle={gamification?.level_title || 'RECRUIT'}
        level={gamification?.level || 1}
        rankIcon={gamification?.rank_icon}
        onDeploy={() => {}}
        isDeploying={false}
      />

      <div className="flex-1 flex flex-col">
        <main className="flex-1 p-8 overflow-auto">
          {/* Stats Header Bar — The "upper bar" with key metrics */}
          <header className="glass-card p-6 mb-8" data-gsap="fade-up">
            <div className="accent-line mb-4" />
            <div className="flex items-center justify-between">
              <div>
                <div className="flex items-center gap-2 text-[var(--valo-text-dim)] text-sm mb-1">
                  <span className="w-2 h-2 rounded-full bg-[var(--valo-green)] energy-pulse" style={{ '--pulse-color': 'rgba(0, 255, 163, 0.5)' } as React.CSSProperties}></span>
                  PERFORMANCE METRICS
                </div>
                <h1 className="font-display text-4xl font-bold tracking-wider vibrant-text inline-block">
                  CAREER STATS
                </h1>
              </div>

              {/* Key Metrics in Header */}
              <div className="flex items-center gap-8">
                {/* Streak */}
                <div className="text-right group cursor-default">
                  <div className="font-display text-3xl font-bold text-[var(--valo-cyan)] flex items-center gap-2 group-hover:drop-shadow-[0_0_12px_rgba(0,217,255,0.5)] transition-all">
                    <span className="count-up">{(gamification?.streak || 0).toString().padStart(2, '0')}</span>
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path d="M17.657 18.657A8 8 0 016.343 7.343S7 9 9 10c0-2 .5-5 2.986-7C14 5 16.09 5.777 17.656 7.343A7.975 7.975 0 0120 13a7.975 7.975 0 01-2.343 5.657z"/></svg>
                  </div>
                  <div className="text-xs text-[var(--valo-text-dim)] tracking-wider">STREAK</div>
                </div>

                {/* Total XP */}
                <div className="text-right group cursor-default">
                  <div className="font-display text-3xl font-bold text-[var(--valo-green)] flex items-center gap-2 group-hover:drop-shadow-[0_0_12px_rgba(0,255,163,0.5)] transition-all">
                    <span className="count-up">{(gamification?.total_xp || 0).toLocaleString()}</span>
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>
                  </div>
                  <div className="text-xs text-[var(--valo-text-dim)] tracking-wider">TOTAL XP</div>
                </div>

                {/* Level */}
                <div className="text-right group cursor-default">
                  <div className="font-display text-3xl font-bold text-[var(--valo-yellow)] flex items-center gap-2 group-hover:drop-shadow-[0_0_12px_rgba(255,229,0,0.5)] transition-all">
                    <span className="count-up">{gamification?.level || 1}</span>
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/></svg>
                  </div>
                  <div className="text-xs text-[var(--valo-text-dim)] tracking-wider">LEVEL</div>
                </div>

                {/* Today */}
                <div className="text-right group cursor-default">
                  <div className="font-display text-3xl font-bold text-[var(--valo-red)] flex items-center gap-2 group-hover:drop-shadow-[0_0_12px_rgba(255,70,85,0.5)] transition-all">
                    <span className="count-up">{gamification?.applications_today || 0}</span>
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M15 3L21 9M21 3L15 9M5 21l7-7m0 0l7-7M12 14l-7 7"/></svg>
                  </div>
                  <div className="text-xs text-[var(--valo-text-dim)] tracking-wider">TODAY</div>
                </div>

                {/* Secret Dev Button */}
                <button
                  onClick={handleSimulateLevelUp}
                  className="text-[10px] text-[var(--valo-gray-light)] hover:text-[var(--valo-text-dim)] uppercase tracking-widest border border-transparent hover:border-[var(--valo-gray-light)] px-2 py-1"
                >
                  [SIM]
                </button>
              </div>
            </div>
          </header>

          {loading ? (
            <div className="text-center py-12 text-[var(--valo-text-dim)]">
              Loading statistics...
            </div>
          ) : (
            <>
              {/* Level Progression Map */}
              {gamification && (
                <LevelProgress
                  currentLevel={gamification.level}
                  levelTitle={gamification.level_title}
                  totalXp={gamification.total_xp}
                  currentXpInLevel={gamification.current_xp_in_level}
                  xpForNextLevel={gamification.xp_for_next_level}
                  rankIcon={gamification.rank_icon}
                />
              )}

              {/* Weapon Loadout / Armory */}
              <div className="mb-8" data-gsap="fade-up" data-gsap-delay="0.1">
                 <WeaponShowcase />
              </div>

              {/* Stats Grid */}
              <div className="grid grid-cols-4 gap-4 mb-6" data-gsap="stagger">
                <div className="gradient-card p-5 text-center stat-card-glow cursor-pointer group" data-color="cyan">
                  <div className="flex justify-center mb-2 text-[var(--valo-cyan)]">
                    <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><circle cx="12" cy="12" r="10" /><circle cx="12" cy="12" r="6" /><circle cx="12" cy="12" r="2" /></svg>
                  </div>
                  <div className="font-display text-4xl font-bold text-[var(--valo-text)] mb-1 group-hover:text-[var(--valo-cyan)] transition-colors group-hover:drop-shadow-[0_0_15px_rgba(0,217,255,0.4)]">
                    {stats?.total || 0}
                  </div>
                  <div className="text-sm text-[var(--valo-text-dim)]">TOTAL TARGETS</div>
                </div>
                <div className="gradient-card p-5 text-center stat-card-glow cursor-pointer group" data-color="green">
                  <div className="flex justify-center mb-2 text-[var(--valo-green)]">
                    <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/></svg>
                  </div>
                  <div className="font-display text-4xl font-bold text-[var(--valo-green)] mb-1 group-hover:drop-shadow-[0_0_15px_rgba(0,255,163,0.4)]">
                    {stats?.applied || 0}
                  </div>
                  <div className="text-sm text-[var(--valo-text-dim)]">DEPLOYED</div>
                </div>
                <div className="gradient-card p-5 text-center stat-card-glow cursor-pointer group" data-color="yellow">
                  <div className="flex justify-center mb-2 text-[var(--valo-yellow)]">
                    <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><circle cx="12" cy="12" r="10" /><path d="M12 6v6l4 2"/></svg>
                  </div>
                  <div className="font-display text-4xl font-bold text-[var(--valo-yellow)] mb-1 group-hover:drop-shadow-[0_0_15px_rgba(255,229,0,0.4)]">
                    {stats?.pending || 0}
                  </div>
                  <div className="text-sm text-[var(--valo-text-dim)]">PENDING</div>
                </div>
                <div className="gradient-card p-5 text-center stat-card-glow cursor-pointer group" data-color="red">
                  <div className="flex justify-center mb-2 text-[var(--valo-red)]">
                    <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                  </div>
                  <div className="font-display text-4xl font-bold text-[var(--valo-red)] mb-1 group-hover:drop-shadow-[0_0_15px_rgba(255,70,85,0.4)]">
                    {stats?.failed || 0}
                  </div>
                  <div className="text-sm text-[var(--valo-text-dim)]">FAILED</div>
                </div>
              </div>

              {/* Charts */}
              {stats && (
                <StatsCharts
                  bySource={stats.by_source}
                  applied={stats.applied}
                  pending={stats.pending}
                  failed={stats.failed}
                  total={stats.total}
                  weeklyActivity={stats.weekly_activity}
                />
              )}

              {/* Streak & Daily Stats */}
              <div className="grid grid-cols-2 gap-4 mt-6" data-gsap="stagger">
                <div className="gradient-card p-6 text-center cursor-pointer group">
                  <div className="flex justify-center mb-3 text-[var(--valo-cyan)]">
                    <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path d="M17.657 18.657A8 8 0 016.343 7.343S7 9 9 10c0-2 .5-5 2.986-7C14 5 16.09 5.777 17.656 7.343A7.975 7.975 0 0120 13a7.975 7.975 0 01-2.343 5.657z"/><path d="M9.879 16.121A3 3 0 1012.015 11L11 14H9c0 .768.293 1.536.879 2.121z"/></svg>
                  </div>
                  <div className="font-display text-5xl font-bold text-[var(--valo-cyan)] mb-2 group-hover:drop-shadow-[0_0_20px_rgba(0,217,255,0.4)] transition-all">
                    {gamification?.streak || 0}
                  </div>
                  <div className="text-[var(--valo-text-dim)] font-semibold">DAY STREAK</div>
                  <p className="text-xs text-[var(--valo-text-dim)] mt-2">
                    Apply daily to maintain your streak and earn bonus XP!
                  </p>
                </div>
                <div className="gradient-card p-6 text-center cursor-pointer group">
                  <div className="flex justify-center mb-3 text-[var(--valo-green)]">
                    <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M15 3L21 9M21 3L15 9M5 21l7-7m0 0l7-7M12 14l-7 7"/></svg>
                  </div>
                  <div className="font-display text-5xl font-bold text-[var(--valo-green)] mb-2 group-hover:drop-shadow-[0_0_20px_rgba(0,255,163,0.4)] transition-all">
                    {gamification?.applications_today || 0}
                  </div>
                  <div className="text-[var(--valo-text-dim)] font-semibold">DEPLOYED TODAY</div>
                  <p className="text-xs text-[var(--valo-text-dim)] mt-2">
                    Complete 5 applications today to finish your daily quest!
                  </p>
                </div>
              </div>
            </>
          )}
        </main>

        <Footer />
      </div>
    </div>
  );
}
