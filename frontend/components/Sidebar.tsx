'use client';

import { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useAuth } from '@/lib/auth';

// Valorant agent data with image URLs from official sources
export const VALORANT_AGENTS: Record<string, { name: string; icon: string; color: string }> = {
  jett: { name: 'Jett', icon: 'https://media.valorant-api.com/agents/add6443a-41bd-e414-f6ad-e58d267f4e95/displayicon.png', color: '#5EB5E5' },
  phoenix: { name: 'Phoenix', icon: 'https://media.valorant-api.com/agents/eb93336a-449b-9c1b-0a54-a891f7921d69/displayicon.png', color: '#FE8900' },
  sage: { name: 'Sage', icon: 'https://media.valorant-api.com/agents/569fdd95-4d10-43ab-ca70-79becc718b46/displayicon.png', color: '#5EEAD4' },
  reyna: { name: 'Reyna', icon: 'https://media.valorant-api.com/agents/a3bfb853-43b2-7238-a4f1-ad90e9e46bcc/displayicon.png', color: '#C27FFF' },
  killjoy: { name: 'Killjoy', icon: 'https://media.valorant-api.com/agents/1e58de9c-4950-5125-93e9-a0aee9f98746/displayicon.png', color: '#FFE500' },
  cypher: { name: 'Cypher', icon: 'https://media.valorant-api.com/agents/117ed9e3-49f3-6512-3ccf-0cada7e3823b/displayicon.png', color: '#F0F0F0' },
  sova: { name: 'Sova', icon: 'https://media.valorant-api.com/agents/320b2a48-4d9b-a075-30f1-1f93a9b638fa/displayicon.png', color: '#3B82F6' },
  raze: { name: 'Raze', icon: 'https://media.valorant-api.com/agents/f94c3b30-42be-e959-889c-5aa313dba261/displayicon.png', color: '#FF7F00' },
  omen: { name: 'Omen', icon: 'https://media.valorant-api.com/agents/8e253930-4c05-31dd-1b6c-968525494517/displayicon.png', color: '#4B5563' },
  viper: { name: 'Viper', icon: 'https://media.valorant-api.com/agents/707eab51-4836-f488-046a-cda6bf494859/displayicon.png', color: '#22C55E' },
  breach: { name: 'Breach', icon: 'https://media.valorant-api.com/agents/5f8d3a7f-467b-97f3-062c-13acf203c006/displayicon.png', color: '#F97316' },
  brimstone: { name: 'Brimstone', icon: 'https://media.valorant-api.com/agents/9f0d8ba9-4140-b941-57d3-a7ad57c6b417/displayicon.png', color: '#DC2626' },
  yoru: { name: 'Yoru', icon: 'https://media.valorant-api.com/agents/7f94d92c-4234-0a36-9646-3a87eb8b5c89/displayicon.png', color: '#4F46E5' },
  astra: { name: 'Astra', icon: 'https://media.valorant-api.com/agents/41fb69c1-4189-7b37-f117-bcaf1e96f1bf/displayicon.png', color: '#A855F7' },
  kayo: { name: 'KAY/O', icon: 'https://media.valorant-api.com/agents/601dbbe7-43ce-be57-2a40-4abd24953621/displayicon.png', color: '#3B82F6' },
  skye: { name: 'Skye', icon: 'https://media.valorant-api.com/agents/6f2a04ca-43e0-be17-7f36-b3908627744d/displayicon.png', color: '#22D3EE' },
  chamber: { name: 'Chamber', icon: 'https://media.valorant-api.com/agents/22697a3d-45bf-8dd7-4fec-84a9e28c69d7/displayicon.png', color: '#D4AF37' },
  neon: { name: 'Neon', icon: 'https://media.valorant-api.com/agents/bb2a4828-46eb-8cd1-e765-15848195d751/displayicon.png', color: '#00D9FF' },
  fade: { name: 'Fade', icon: 'https://media.valorant-api.com/agents/dade69b4-4f5a-8528-247b-219e5a1facd6/displayicon.png', color: '#6B21A8' },
  harbor: { name: 'Harbor', icon: 'https://media.valorant-api.com/agents/95b78ed7-4637-86d9-7e41-71ba8c293152/displayicon.png', color: '#0EA5E9' },
  gekko: { name: 'Gekko', icon: 'https://media.valorant-api.com/agents/e370fa57-4757-3604-3648-499e1f642d3f/displayicon.png', color: '#84CC16' },
  deadlock: { name: 'Deadlock', icon: 'https://media.valorant-api.com/agents/cc8b64c8-4b25-4ff9-6e7f-37b4da43d235/displayicon.png', color: '#78716C' },
  iso: { name: 'Iso', icon: 'https://media.valorant-api.com/agents/0e38b510-41a8-5780-5e8f-568b2a4f2d6c/displayicon.png', color: '#7C3AED' },
  clove: { name: 'Clove', icon: 'https://media.valorant-api.com/agents/1dbf2edd-4729-0984-3115-daa5eed44993/displayicon.png', color: '#EC4899' },
};



interface NavItem {
  name: string;
  href: string;
  icon: React.ReactNode;
}

const navItems: NavItem[] = [
  {
    name: 'Dashboard',
    href: '/',
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
      </svg>
    ),
  },
  {
    name: 'All Jobs',
    href: '/missions',
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
      </svg>
    ),
  },
  {
    name: 'Emails',
    href: '/emails',
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
      </svg>
    ),
  },
  {
    name: 'Statistics',
    href: '/stats',
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
      </svg>
    ),
  },
  {
    name: 'Profile',
    href: '/profile',
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
      </svg>
    ),
  },
];

interface SidebarProps {
  agentName: string;
  userName?: string;
  valorantAgent?: string;
  levelTitle: string;
  level: number;
  rankIcon?: string;
  onDeploy: () => void;
  isDeploying?: boolean;
}

 
export default function Sidebar({ 
  agentName, 
  userName, 
  valorantAgent = 'jett',
  levelTitle, 
  level, 
  rankIcon,
  onDeploy, 
  isDeploying 
}: SidebarProps) {
  const pathname = usePathname();
  const { isAdmin, login, logout } = useAuth();
  const [showLoginModal, setShowLoginModal] = useState(false);
  const [loginToken, setLoginToken] = useState('');
  const [loginError, setLoginError] = useState('');
  
  const agent = VALORANT_AGENTS[valorantAgent.toLowerCase()] || VALORANT_AGENTS.jett;

  const handleLogin = async () => {
    setLoginError('');
    const success = await login(loginToken);
    if (success) {
      setShowLoginModal(false);
      setLoginToken('');
    } else {
      setLoginError('Invalid token');
    }
  };

  return (
    <>
    <aside className="w-64 min-h-screen bg-[var(--valo-dark)] border-r border-[var(--valo-gray-light)] flex flex-col">
      {/* Logo */}
      <div className="p-4 border-b border-[var(--valo-gray-light)]">
        <div className="flex items-center gap-2 p-2 tech-button">
          <img 
            src="/logo.png" 
            alt="PaperPlane" 
            className="w-8 h-8 object-contain"
          />
          <span className="font-display text-2xl font-bold tracking-tighter text-[var(--valo-red)]">
            PAPERPLANE
          </span>
        </div>
      </div>

      {/* User Profile */}
      <Link href="/profile" className="block p-4 border-b border-[var(--valo-gray-light)] hover:bg-transparent">
        <div className="flex flex-col items-center p-4 tech-button hover:bg-[var(--valo-dark)]/50 transition-colors">
          {/* Valorant Agent Avatar */}
          <div className="relative mb-3">
            <div 
              className="w-20 h-20 overflow-hidden transition-all duration-300 hover:scale-110"
              style={{ 
                border: `2px solid ${agent.color}`,
                boxShadow: `0 0 20px ${agent.color}40`,
                clipPath: 'polygon(20% 0, 100% 0, 100% 80%, 80% 100%, 0 100%, 0 20%)'
              }}
            >
              <img 
                key={agent.name}
                src={agent.icon} 
                alt={agent.name}
                className="w-full h-full object-cover bg-[var(--valo-darker)]"
                onError={(e) => {
                  // Fallback to emoji if image fails
                  e.currentTarget.style.display = 'none';
                }}
              />
            </div>
            {/* Rank Badge */}
            <div 
              className="absolute -bottom-2 -right-2 w-10 h-10 flex items-center justify-center bg-[var(--valo-dark)] border border-[var(--valo-gold)] overflow-hidden shadow-lg"
              style={{ clipPath: 'polygon(50% 0, 100% 50%, 50% 100%, 0 50%)' }}
            >
              {rankIcon ? (
                <img 
                  src={rankIcon} 
                  alt="Rank" 
                  className="w-full h-full object-contain p-1"
                />
              ) : (
                <span className="font-bold text-white text-xs">{level}</span>
              )}
            </div>
          </div>
          
          {/* User's Real Name */}
          <h2 className="font-display text-xl font-bold tracking-wider text-[var(--valo-text)] text-center">
            {userName || agentName}
          </h2>
          
          {/* Agent Title */}
          <p 
            className="text-sm font-semibold tracking-wide"
            style={{ color: agent.color }}
          >
            {levelTitle}
          </p>
          
          {/* Valorant Agent Name */}
          <p className="text-xs text-[var(--valo-text-dim)] mt-1 uppercase tracking-widest">
            {agent.name} MAIN
          </p>
        </div>
      </Link>

      {/* Navigation */}
      <nav className="flex-1 p-4">
        <ul className="space-y-2">
          {navItems.map((item) => {
            const isActive = pathname === item.href;
            return (
              <li key={item.name}>
                <Link
                  href={item.href}
                  className={`flex items-center gap-3 px-4 py-3 transition-all duration-200 tech-button ${
                    isActive
                      ? 'active text-[var(--valo-red)]'
                      : 'text-[var(--valo-text-dim)] hover:text-[var(--valo-text)]'
                  }`}
                >
                  {item.icon}
                  <span className="font-semibold tracking-wide">{item.name}</span>
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      {/* Deploy Button */}
      <div className="p-4">
        <button
          onClick={onDeploy}
          disabled={isDeploying || !isAdmin}
          className={`w-full py-4 font-display font-bold tracking-wider text-lg transition-all duration-200 flex items-center justify-center gap-2 tech-button-solid ${
            !isAdmin
              ? 'bg-[var(--valo-gray)] text-[var(--valo-text-dim)] cursor-not-allowed'
              : isDeploying
                ? 'bg-[var(--valo-gray)] text-[var(--valo-text-dim)] cursor-not-allowed'
                : 'bg-[var(--valo-red)] text-white hover:shadow-[0_0_30px_rgba(255,70,85,0.5)] active:scale-95'
          }`}
        >
          {!isAdmin ? (
            <>
              <span className="text-xl">🔒</span>
              ADMIN ONLY
            </>
          ) : isDeploying ? (
            <>
              <svg className="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              SCANNING...
            </>
          ) : (
            <>
              <span className="text-xl">🚀</span>
              FULL DEPLOY
            </>
          )}
        </button>
        <p className="text-center text-xs text-[var(--valo-text-dim)] mt-2">
          {isAdmin ? 'Scan + Auto Apply' : 'Login to unlock'}
        </p>
      </div>

      {/* Admin Login/Logout */}
      <div className="p-4 pt-0">
        {isAdmin ? (
          <button
            onClick={logout}
            className="w-full py-2 text-xs font-semibold tracking-wider text-[var(--valo-text-dim)] hover:text-[var(--valo-red)] transition-colors flex items-center justify-center gap-2"
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
            </svg>
            LOGOUT
          </button>
        ) : (
          <button
            onClick={() => setShowLoginModal(true)}
            className="w-full py-2 text-xs font-semibold tracking-wider text-[var(--valo-text-dim)] hover:text-[var(--valo-cyan)] transition-colors flex items-center justify-center gap-2"
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
            </svg>
            ADMIN LOGIN
          </button>
        )}
      </div>
    </aside>

    {/* Login Modal */}
    {showLoginModal && (
      <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 animate-in fade-in">
        <div className="tech-border bg-[var(--valo-gray)] rounded-lg p-6 max-w-sm mx-4 w-full animate-in zoom-in-95">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-lg bg-[var(--valo-cyan)]/20 flex items-center justify-center">
              <svg className="w-5 h-5 text-[var(--valo-cyan)]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
              </svg>
            </div>
            <h3 className="font-display text-lg font-bold text-[var(--valo-text)] tracking-wider">
              ADMIN ACCESS
            </h3>
          </div>
          <input
            type="password"
            value={loginToken}
            onChange={(e) => setLoginToken(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleLogin()}
            placeholder="Enter admin token"
            className="w-full px-4 py-3 bg-[var(--valo-dark)] border border-[var(--valo-gray-light)] rounded-lg text-[var(--valo-text)] placeholder-[var(--valo-text-dim)] focus:border-[var(--valo-cyan)] focus:outline-none transition-colors mb-3 font-mono text-sm"
            autoFocus
          />
          {loginError && (
            <p className="text-[var(--valo-red)] text-xs mb-3 font-semibold">{loginError}</p>
          )}
          <div className="flex gap-3">
            <button
              onClick={() => { setShowLoginModal(false); setLoginToken(''); setLoginError(''); }}
              className="flex-1 py-2.5 rounded-lg bg-[var(--valo-gray-light)] text-[var(--valo-text)] font-semibold text-sm hover:bg-opacity-80 transition-all"
            >
              CANCEL
            </button>
            <button
              onClick={handleLogin}
              className="flex-1 py-2.5 rounded-lg bg-[var(--valo-cyan)] text-[var(--valo-dark)] font-semibold text-sm hover:shadow-[0_0_15px_rgba(0,255,255,0.4)] transition-all"
            >
              LOGIN
            </button>
          </div>
        </div>
      </div>
    )}
    </>
  );
}
