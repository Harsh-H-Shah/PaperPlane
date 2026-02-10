'use client';

import { useState, useEffect } from 'react';
import Sidebar from '@/components/Sidebar';
import Footer from '@/components/Footer';
import { api, Profile, Gamification } from '@/lib/api';

interface Scraper {
  name: string;
  enabled: boolean;
  configured: boolean;
  icon: string;
  note?: string;
}

export default function ArsenalPage() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [gamification, setGamification] = useState<Gamification | null>(null);
  const [scrapers, setScrapers] = useState<Scraper[]>([]);
  const [activeScraper, setActiveScraper] = useState<string | null>(null);
  const [scrapeProgress, setScrapeProgress] = useState<{
    is_running: boolean;
    current_source: string;
    jobs_found: number;
    jobs_new: number;
  } | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [profileData, gamData, scraperData] = await Promise.all([
          api.getProfile(),
          api.getGamification(),
          api.getScraperStatus(),
        ]);
        setProfile(profileData);
        setGamification(gamData);
        setScrapers(scraperData.scrapers || []);
      } catch (err) {
        console.error('Failed to fetch:', err);
      }
    };
    fetchData();
  }, []);

  const handleScrape = async (source?: string) => {
    setActiveScraper(source || 'all');
    try {
      await api.triggerScrape(source ? [source] : undefined);
      
      const pollInterval = setInterval(async () => {
        const progress = await api.getScrapeProgress();
        setScrapeProgress(progress);
        if (!progress.is_running) {
          clearInterval(pollInterval);
          setActiveScraper(null);
        }
      }, 1000);
    } catch (err) {
      console.error('Scrape failed:', err);
      setActiveScraper(null);
    }
  };

  const tools = [
    {
      id: 'resume',
      name: 'RESUME GENERATOR',
      description: 'Generate tailored resumes for specific job roles',
      icon: '📄',
      status: 'READY',
      onClick: () => alert('Resume generation - Run: python main.py resume'),
    },
    {
      id: 'auto-apply',
      name: 'AUTO-APPLY ENGINE',
      description: 'Automatically fill and submit job applications',
      icon: '🚀',
      status: 'READY',
      onClick: () => alert('Auto-apply - Run: python main.py apply'),
    },
    {
      id: 'scheduler',
      name: 'SCHEDULER',
      description: 'Schedule automated job scraping runs',
      icon: '⏰',
      status: 'IDLE',
      onClick: () => alert('Scheduler - Run: python main.py scheduler start'),
    },
    {
      id: 'llm',
      name: 'AI ANALYZER',
      description: 'Analyze job fit and generate responses',
      icon: '🤖',
      status: 'READY',
      onClick: () => alert('AI Analyzer - Uses Gemini API for intelligent responses'),
    },
  ];

  return (
    <div className="flex min-h-screen bg-[var(--valo-darker)]">
      <Sidebar
        agentName={profile?.agent_name || 'AGENT'}
        levelTitle={gamification?.level_title || 'RECRUIT'}
        level={gamification?.level || 1}
        onDeploy={() => handleScrape()}
        isDeploying={!!activeScraper}
      />

      <div className="flex-1 flex flex-col">
        <main className="flex-1 p-8 overflow-auto">
          <header className="mb-8">
            <div className="flex items-center gap-2 text-[var(--valo-text-dim)] text-sm mb-1">
              <span className="w-2 h-2 rounded-full bg-[var(--valo-yellow)] pulse-green"></span>
              EQUIPMENT LOADOUT
            </div>
            <h1 className="font-display text-4xl font-bold tracking-wider text-[var(--valo-text)]">
              ARSENAL
            </h1>
          </header>

          {/* Scrape Progress */}
          {activeScraper && scrapeProgress && (
            <div className="tech-border bg-[var(--valo-gray)] rounded-lg p-6 mb-6 animate-pulse">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-display text-lg font-bold text-[var(--valo-cyan)]">
                  🔍 SCANNING: {scrapeProgress.current_source?.toUpperCase() || 'INITIALIZING...'}
                </h3>
                <div className="flex gap-6">
                  <div className="text-center">
                    <div className="font-display text-2xl font-bold text-[var(--valo-green)]">
                      {scrapeProgress.jobs_found}
                    </div>
                    <div className="text-xs text-[var(--valo-text-dim)]">FOUND</div>
                  </div>
                  <div className="text-center">
                    <div className="font-display text-2xl font-bold text-[var(--valo-cyan)]">
                      {scrapeProgress.jobs_new}
                    </div>
                    <div className="text-xs text-[var(--valo-text-dim)]">NEW</div>
                  </div>
                </div>
              </div>
              <div className="h-2 bg-[var(--valo-darker)] rounded-full overflow-hidden">
                <div className="h-full bg-gradient-to-r from-[var(--valo-cyan)] to-[var(--valo-green)] rounded-full w-full animate-pulse" />
              </div>
            </div>
          )}

          {/* Mass Scan Button */}
          <div className="tech-border bg-[var(--valo-gray)] rounded-lg p-6 mb-6">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-display text-xl font-bold text-[var(--valo-text)] mb-1">
                  FULL RECONNAISSANCE
                </h3>
                <p className="text-[var(--valo-text-dim)]">
                  Scan all intelligence sources simultaneously for maximum coverage
                </p>
              </div>
              <button
                onClick={() => handleScrape()}
                disabled={!!activeScraper}
                className={`px-8 py-4 rounded-lg font-display font-bold tracking-wider transition-all ${
                  activeScraper
                    ? 'bg-[var(--valo-gray-light)] text-[var(--valo-text-dim)] cursor-not-allowed'
                    : 'bg-[var(--valo-red)] text-white hover:opacity-80 glow-red'
                }`}
              >
                {activeScraper ? 'SCANNING...' : 'DEPLOY FULL SCAN'}
              </button>
            </div>
          </div>

          {/* Scrapers Grid */}
          <h2 className="font-display text-xl font-bold text-[var(--valo-text)] mb-4">
            INTELLIGENCE SOURCES
          </h2>
          <div className="grid grid-cols-3 gap-4 mb-8">
            {scrapers.map((scraper) => (
              <div
                key={scraper.name}
                className={`tech-border rounded-lg p-5 card-hover ${
                  scraper.configured ? 'bg-[var(--valo-gray)]' : 'bg-[var(--valo-gray)] opacity-50'
                }`}
              >
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <span className="text-3xl">{scraper.icon}</span>
                    <div>
                      <h3 className="font-semibold text-[var(--valo-text)]">{scraper.name}</h3>
                      {scraper.note && (
                        <p className="text-xs text-[var(--valo-text-dim)]">{scraper.note}</p>
                      )}
                    </div>
                  </div>
                  <span className={`px-2 py-1 rounded text-xs font-semibold ${
                    scraper.enabled ? 'status-green' : 'status-gray'
                  }`}>
                    {scraper.enabled ? 'ONLINE' : 'OFFLINE'}
                  </span>
                </div>
                <button
                  onClick={() => handleScrape(scraper.name.toLowerCase())}
                  disabled={!scraper.configured || !!activeScraper}
                  className={`w-full py-3 rounded-lg font-semibold transition ${
                    scraper.configured && !activeScraper
                      ? 'bg-[var(--valo-cyan)] text-[var(--valo-dark)] hover:opacity-80'
                      : 'bg-[var(--valo-gray-light)] text-[var(--valo-text-dim)] cursor-not-allowed'
                  }`}
                >
                  {activeScraper === scraper.name.toLowerCase() ? 'SCANNING...' : 'DEPLOY SCAN'}
                </button>
              </div>
            ))}
          </div>

          {/* Tools Grid */}
          <h2 className="font-display text-xl font-bold text-[var(--valo-text)] mb-4">
            TACTICAL TOOLS
          </h2>
          <div className="grid grid-cols-2 gap-4">
            {tools.map((tool) => (
              <div
                key={tool.id}
                onClick={tool.onClick}
                className="tech-border bg-[var(--valo-gray)] rounded-lg p-5 card-hover cursor-pointer group"
              >
                <div className="flex items-start gap-4">
                  <span className="text-4xl group-hover:scale-110 transition-transform">{tool.icon}</span>
                  <div className="flex-1">
                    <div className="flex items-center justify-between mb-1">
                      <h3 className="font-semibold text-[var(--valo-text)] group-hover:text-[var(--valo-cyan)] transition-colors">
                        {tool.name}
                      </h3>
                      <span className="text-xs text-[var(--valo-green)]">{tool.status}</span>
                    </div>
                    <p className="text-sm text-[var(--valo-text-dim)]">{tool.description}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </main>
        
        <Footer />
      </div>
    </div>
  );
}
