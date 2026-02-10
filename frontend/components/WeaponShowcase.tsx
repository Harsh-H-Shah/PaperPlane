import { useState } from 'react';

// Valorant Weapon Data
const WEAPONS = [
  // Sidearms
  {
    id: 'classic',
    name: 'CLASSIC',
    category: 'SIDEARM',
    price: 0,
    jobRole: 'Profile Setup',
    desc: 'The foundation of every operation. Essential data entry.',
    xp: '10 XP',
    icon: 'https://media.valorant-api.com/weapons/29a0cfab-485b-f5d5-779a-b59f85e204a8/displayicon.png'
  },
  {
    id: 'sheriff',
    name: 'SHERIFF',
    category: 'SIDEARM',
    price: 800,
    jobRole: 'Networking',
    desc: 'High impact connections. One shot, one opportunity.',
    xp: '50 XP',
    icon: 'https://media.valorant-api.com/weapons/e336c6b8-418d-9340-d77f-7a9e4cfe0702/displayicon.png'
  },

  // SMGs
  {
    id: 'spectre',
    name: 'SPECTRE',
    category: 'SMG',
    price: 1600,
    jobRole: 'Quick Apply',
    desc: 'Rapid fire applications. Good for high volume targets.',
    xp: '20 XP',
    icon: 'https://media.valorant-api.com/weapons/462080d1-4035-2937-7c09-27aa2a5c27a7/displayicon.png'
  },

  // Rifles
  {
    id: 'phantom',
    name: 'PHANTOM',
    category: 'RIFLE',
    price: 2900,
    jobRole: 'Custom Cover Letter',
    desc: 'Silenced and precise. Tailored for specific companies.',
    xp: '100 XP',
    icon: 'https://media.valorant-api.com/weapons/ee8e8d15-496b-07ac-e5f6-8fae5d4c7b1a/displayicon.png'
  },
  {
    id: 'vandal',
    name: 'VANDAL',
    category: 'RIFLE',
    price: 2900,
    jobRole: 'Tailored Resume',
    desc: 'Heavy hitter. Guarantees attention at any range.',
    xp: '150 XP',
    icon: 'https://media.valorant-api.com/weapons/9c82e19d-4575-0200-1a81-3eacf00cf872/displayicon.png'
  },

  // Sniper
  {
    id: 'operator',
    name: 'OPERATOR',
    category: 'SNIPER',
    price: 4700,
    jobRole: 'Interview',
    desc: 'The big gun. Holding the angle for the offer.',
    xp: '500 XP',
    icon: 'https://media.valorant-api.com/weapons/a03b24d3-4319-996d-0f8c-94bbfba1dfc7/displayicon.png'
  },
];

export default function WeaponShowcase() {
  const [selectedWeapon, setSelectedWeapon] = useState(WEAPONS[4]); // Default to Vandal

  return (
    <div className="glass-card p-6 relative overflow-hidden group" data-gsap="fade-up">
      {/* Header */}
      <div className="flex justify-between items-end mb-6 border-b border-white/10 pb-4">
        <div>
           <div className="text-[var(--valo-text-dim)] text-xs tracking-widest mb-1">BUY PHASE</div>
           <h2 className="font-display text-3xl font-bold tracking-wider vibrant-text-fire inline-block">
             LOADOUT
           </h2>
        </div>
        <div className="text-right">
             <div className="text-[var(--valo-green)] font-mono text-xl drop-shadow-[0_0_10px_rgba(0,255,163,0.3)]">
                CREDITS: <span className="font-bold">∞</span>
             </div>
        </div>
      </div>

      <div className="flex gap-8">
        {/* Left: Weapon Grid (Buy Menu Style) */}
        <div className="flex-1 grid grid-cols-2 gap-4">
           {['SIDEARM', 'SMG', 'RIFLE', 'SNIPER'].map(category => (
              <div key={category} className="space-y-2">
                 <div className="text-[10px] text-[var(--valo-text-dim)] font-bold mb-2">{category}</div>
                 {WEAPONS.filter(w => w.category === category).map(weapon => (
                    <div
                      key={weapon.id}
                      onClick={() => setSelectedWeapon(weapon)}
                      className={`
                        relative h-20 border cursor-pointer transition-all duration-300 group/item overflow-visible transform hover:scale-105
                        ${selectedWeapon.id === weapon.id
                           ? 'bg-[var(--valo-green)]/10 border-[var(--valo-green)] shadow-[0_0_15px_rgba(0,255,163,0.15)]'
                           : 'bg-[var(--valo-gray)] border-transparent hover:bg-[var(--valo-gray-light)] hover:shadow-[0_0_10px_rgba(0,217,255,0.1)]'
                        }
                      `}
                      style={{
                         clipPath: 'polygon(0 0, 100% 0, 100% calc(100% - 10px), calc(100% - 10px) 100%, 0 100%)'
                      }}
                    >
                       <img
                          src={weapon.icon}
                          alt={weapon.name}
                          className="absolute right-[-10px] top-1/2 -translate-y-1/2 h-16 object-contain z-10 transition-transform duration-300 group-hover/item:scale-110 group-hover/item:rotate-3"
                       />
                       <div className="absolute top-2 left-3 z-20">
                          <div className={`font-display font-bold text-lg leading-none ${selectedWeapon.id === weapon.id ? 'text-[var(--valo-green)] drop-shadow-[0_0_8px_rgba(0,255,163,0.4)]' : 'text-white'}`}>
                             {weapon.name}
                          </div>
                          <div className="text-[10px] text-[var(--valo-text-dim)] mt-1">{weapon.price}</div>
                       </div>
                    </div>
                 ))}
              </div>
           ))}
        </div>

        {/* Right: Selected Weapon Detail */}
        <div className="w-1/3 bg-[var(--valo-dark)]/80 backdrop-blur-md border border-white/5 p-6 relative flex flex-col items-center text-center">
            {/* Background energy pulse */}
            <div
              className="absolute inset-0 opacity-10 pointer-events-none"
              style={{
                background: `radial-gradient(circle at 50% 40%, ${selectedWeapon.category === 'SNIPER' ? 'rgba(255,70,85,0.3)' : selectedWeapon.category === 'RIFLE' ? 'rgba(0,255,163,0.3)' : 'rgba(0,217,255,0.3)'}, transparent 70%)`
              }}
            />

            <div className="flex-1 flex items-center justify-center w-full relative">
                 <img
                    src={selectedWeapon.icon}
                    alt={selectedWeapon.name}
                    className="w-full object-contain drop-shadow-[0_0_30px_rgba(255,255,255,0.15)] floating-animation"
                 />
            </div>

            <div className="w-full space-y-4 relative z-10 mt-4">
                <div>
                   <h3 className="font-display text-4xl font-bold text-[var(--valo-red)] drop-shadow-[0_0_15px_rgba(255,70,85,0.3)]">{selectedWeapon.name}</h3>
                   <div className="text-[var(--valo-text-dim)] text-sm">{selectedWeapon.category}</div>
                </div>

                <div className="w-full h-[1px] bg-gradient-to-r from-transparent via-white/20 to-transparent" />

                <div className="space-y-2">
                   <div className="flex justify-between items-center">
                      <span className="text-xs text-[var(--valo-text-dim)]">TACTICAL ROLE</span>
                      <span className="font-bold text-white text-sm">{selectedWeapon.jobRole}</span>
                   </div>
                   <div className="flex justify-between items-center">
                      <span className="text-xs text-[var(--valo-text-dim)]">REWARD</span>
                      <span className="font-bold text-[var(--valo-green)] text-sm drop-shadow-[0_0_8px_rgba(0,255,163,0.3)]">{selectedWeapon.xp}</span>
                   </div>
                </div>

                <div className="bg-[var(--valo-gray)]/80 backdrop-blur-sm p-3 text-xs text-[var(--valo-text)] italic border-l-2 border-[var(--valo-red)] text-left">
                   &ldquo;{selectedWeapon.desc}&rdquo;
                </div>

                <button className="w-full py-3 bg-[var(--valo-red)] text-white font-display font-bold tracking-widest hover:brightness-110 hover:shadow-[0_0_30px_rgba(255,70,85,0.4)] active:scale-95 transition-all clip-path-check mt-2">
                   EQUIP
                </button>
            </div>
        </div>
      </div>
    </div>
  );
}
