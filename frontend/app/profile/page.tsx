'use client';

import { useState, useEffect } from 'react';
import Sidebar from '@/components/Sidebar';
import Footer from '@/components/Footer';
import AgentSelector from '@/components/AgentSelector';
import { VALORANT_AGENTS } from '@/components/Sidebar';
import { api, Profile, Gamification } from '@/lib/api';
import { useAuth } from '@/lib/auth';

export default function ProfilePage() {
  const { isAdmin } = useAuth();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [gamification, setGamification] = useState<Gamification | null>(null);
  const [selectedAgent, setSelectedAgent] = useState<string>('jett');
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [profileData, gamData] = await Promise.all([
          api.getProfile(),
          api.getGamification(),
        ]);
        setProfile(profileData);
        setGamification(gamData);
        setSelectedAgent(profileData.valorant_agent || 'jett');
      } catch (err) {
        console.error('Failed to fetch profile:', err);
      }
    };
    fetchData();
  }, []);

  const handleSaveAgent = async (agentKey: string) => {
    if (!isAdmin) {
      setSaveError('Admin login required to change agent');
      setTimeout(() => setSaveError(null), 2500);
      return;
    }
    setSaving(true);
    setSaveError(null);
    try {
      await api.updateProfile({ valorant_agent: agentKey });
      setSelectedAgent(agentKey);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (err: any) {
      console.error('Failed to save agent:', err);
      const msg = String(err?.message || '');
      setSaveError(msg.includes('403') ? 'Admin login required to change agent' : 'Failed to save agent. Try again.');
      setTimeout(() => setSaveError(null), 3000);
    } finally {
      setSaving(false);
    }
  };

  const agent = VALORANT_AGENTS[selectedAgent] || VALORANT_AGENTS.jett;

  return (
    <div className="flex min-h-screen bg-[var(--valo-darker)]">
      <Sidebar
        agentName={profile?.agent_name || 'AGENT'}
        userName={profile?.full_name || profile?.first_name}
        valorantAgent={selectedAgent}
        levelTitle={gamification?.level_title || 'RECRUIT'}
        level={gamification?.level || 1}
        rankIcon={gamification?.rank_icon}
        onDeploy={() => {}}
        isDeploying={false}
      />

      <div className="flex-1 flex flex-col h-screen overflow-hidden min-w-0">
        <main className="flex-1 flex overflow-hidden">
          
          {/* LEFT COLUMN: Hero Character (Fixed) */}
          <div className="w-1/3 relative hidden xl:flex items-center justify-center bg-gradient-to-r from-black/20 to-transparent">
             {/* Dynamic Background Text */}
             <div className="absolute inset-0 flex items-center justify-center overflow-hidden">
                <h1 
                  className="text-[15rem] font-display font-bold opacity-5 transform -rotate-90 whitespace-nowrap select-none pointer-events-none"
                  style={{ color: agent.color }}
                >
                  {agent.name.toUpperCase()}
                </h1>
             </div>

             {/* Full Scale Agent Image */}
             <div className="relative z-10 h-[100%] w-full flex items-center justify-center">
                <img 
                  key={agent.name}
                  src={agent.icon.replace('displayicon.png', 'fullportrait.png')}
                  alt={agent.name}
                  className="h-[120%] w-auto object-contain drop-shadow-[0_0_50px_rgba(0,0,0,0.5)] animate-in slide-in-from-left-4 fade-in duration-700 scale-135 origin-bottom translate-y-6"
                  style={{ filter: `drop-shadow(0 0 30px ${agent.color}30)` }}
                />
             </div>
             
             {/* Role/Class Info (Optional overlay) */}
             <div className="absolute bottom-10 left-10 z-20">
                <div className="text-6xl font-display font-bold text-white tracking-widest drop-shadow-lg">
                  {agent.name.toUpperCase()}
                </div>
                <div className="text-xl text-[var(--valo-text-dim)] tracking-[0.5em] font-bold">
                  AGENT PROFILE
                </div>
             </div>
          </div>

          {/* RIGHT COLUMN: Scrollable Content */}
          <div className="flex-1 overflow-y-auto p-4 sm:p-6 md:p-8 relative">
             <div className="max-w-4xl mx-auto space-y-6 sm:space-y-8">

                {/* Header (Mobile Only) */}
                <div className="xl:hidden mb-4 sm:mb-8 pl-12 md:pl-0">
                  <h1 className="font-display text-2xl sm:text-3xl md:text-4xl font-bold tracking-wider text-[var(--valo-text)]">
                    AGENT PROFILE
                  </h1>
                </div>

                {/* Personal Info Card (Compact) */}
                <div className="tech-border p-4 sm:p-6 relative overflow-hidden">
                   <div className="absolute top-0 right-0 p-4 opacity-5">
                      <svg className="w-32 h-32" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z" />
                      </svg>
                   </div>

                   <h2 className="font-display text-lg font-bold tracking-wider text-[var(--valo-text)] mb-6 flex items-center gap-2">
                      <span className="w-1 h-6 bg-[var(--valo-red)]"></span>
                      SERVICE RECORD
                   </h2>

                   <div className="grid grid-cols-1 sm:grid-cols-2 gap-y-4 sm:gap-y-6 gap-x-6 sm:gap-x-12 relative z-10">
                      <div>
                        <label className="text-xs text-[var(--valo-text-dim)] font-bold tracking-widest uppercase block mb-1">OPERATIVE NAME</label>
                        <div className="font-display text-xl sm:text-2xl text-[var(--valo-text)] tracking-wide break-words">{profile?.full_name || 'UNKNOWN'}</div>
                      </div>
                      <div>
                        <label className="text-xs text-[var(--valo-text-dim)] font-bold tracking-widest uppercase block mb-1">CONTACT</label>
                        <div className="font-mono text-sm text-[var(--valo-green)] break-all">{profile?.email || 'UNKNOWN'}</div>
                      </div>
                      <div>
                        <label className="text-xs text-[var(--valo-text-dim)] font-bold tracking-widest uppercase block mb-1">CURRENT RANK</label>
                        <div className="flex items-center gap-3">
                           {gamification?.rank_icon && <img src={gamification.rank_icon} className="w-10 h-10 object-contain drop-shadow-md" alt="Rank" />}
                           <div className="font-display text-xl text-[var(--valo-text)]">{gamification?.level_title || 'UNRANKED'}</div>
                        </div>
                      </div>
                      <div>
                        <label className="text-xs text-[var(--valo-text-dim)] font-bold tracking-widest uppercase block mb-1">TOTAL EXPERIENCE</label>
                        <div className="font-display text-xl sm:text-2xl text-[var(--valo-yellow)]">{gamification?.total_xp || 0} XP</div>
                      </div>
                   </div>
                </div>

                {/* Rank Rating Bar */}
                <div className="tech-border p-4 sm:p-6">
                   <div className="flex flex-col sm:flex-row sm:justify-between sm:items-end mb-2 gap-1">
                      <h2 className="font-display text-lg font-bold tracking-wider text-[var(--valo-text)]">RANK RATING</h2>
                      <span className="font-mono text-sm sm:text-base text-[var(--valo-cyan)]">{gamification?.current_xp_in_level || 0} / 100 RR</span>
                   </div>
                   <div className="h-4 bg-[var(--valo-darker)] rounded-full overflow-hidden border border-[var(--valo-gray-light)]">
                      <div 
                        className="h-full bg-gradient-to-r from-[var(--valo-cyan)] to-[var(--valo-green)] relative"
                        style={{ width: `${gamification ? (gamification.current_xp_in_level / 100) * 100 : 0}%` }}
                      >
                         <div className="absolute right-0 top-0 bottom-0 w-[2px] bg-white shadow-[0_0_10px_white]"></div>
                      </div>
                   </div>
                </div>

                {/* New 3D Agent Carousel */}
                <div className="mb-12">
                   <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 mb-4 sm:mb-6">
                      <h2 className="font-display text-xl sm:text-2xl font-bold tracking-wider text-[var(--valo-text)]">
                         SELECT AGENT
                      </h2>
                      <div className="flex gap-2 items-center">
                        {!isAdmin && <span className="text-[var(--valo-text-dim)] uppercase tracking-widest text-[10px] font-bold flex items-center gap-1">🔒 ADMIN LOGIN REQUIRED</span>}
                        {saving && <span className="text-[var(--valo-yellow)] animate-pulse uppercase tracking-widest text-xs font-bold">SAVING...</span>}
                        {saved && <span className="text-[var(--valo-green)] uppercase tracking-widest text-xs font-bold">CONFIRMED</span>}
                        {saveError && <span className="text-[var(--valo-red)] uppercase tracking-widest text-xs font-bold">{saveError}</span>}
                      </div>
                   </div>

                   <AgentSelector
                      selectedAgent={selectedAgent}
                      onSelectToken={handleSaveAgent}
                      disabled={saving || !isAdmin}
                   />
                </div>

             </div>
          </div>

        </main>
        <Footer />
      </div>
    </div>
  );
}
