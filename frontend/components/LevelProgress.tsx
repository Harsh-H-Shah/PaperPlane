'use client';

interface LevelProgressProps {
  currentLevel: number;       // tier_index from backend (3=Iron1 → 27=Radiant)
  levelTitle: string;         // e.g. "Iron 1"
  totalXp: number;
  currentXpInLevel: number;   // current RR (0-99)
  xpForNextLevel: number;     // always 100
  rankIcon?: string;          // URL from valorant-api.com
}

// Valorant rank tiers matching backend (tier_index 3-27)
const VALORANT_RANKS = [
  { tier: 3,  title: 'Iron 1',      division: 'Iron',      color: '#6B7280' },
  { tier: 4,  title: 'Iron 2',      division: 'Iron',      color: '#6B7280' },
  { tier: 5,  title: 'Iron 3',      division: 'Iron',      color: '#6B7280' },
  { tier: 6,  title: 'Bronze 1',    division: 'Bronze',    color: '#CD7F32' },
  { tier: 7,  title: 'Bronze 2',    division: 'Bronze',    color: '#CD7F32' },
  { tier: 8,  title: 'Bronze 3',    division: 'Bronze',    color: '#CD7F32' },
  { tier: 9,  title: 'Silver 1',    division: 'Silver',    color: '#C0C0C0' },
  { tier: 10, title: 'Silver 2',    division: 'Silver',    color: '#C0C0C0' },
  { tier: 11, title: 'Silver 3',    division: 'Silver',    color: '#C0C0C0' },
  { tier: 12, title: 'Gold 1',      division: 'Gold',      color: '#FFD700' },
  { tier: 13, title: 'Gold 2',      division: 'Gold',      color: '#FFD700' },
  { tier: 14, title: 'Gold 3',      division: 'Gold',      color: '#FFD700' },
  { tier: 15, title: 'Platinum 1',  division: 'Platinum',  color: '#00D9FF' },
  { tier: 16, title: 'Platinum 2',  division: 'Platinum',  color: '#00D9FF' },
  { tier: 17, title: 'Platinum 3',  division: 'Platinum',  color: '#00D9FF' },
  { tier: 18, title: 'Diamond 1',   division: 'Diamond',   color: '#A855F7' },
  { tier: 19, title: 'Diamond 2',   division: 'Diamond',   color: '#A855F7' },
  { tier: 20, title: 'Diamond 3',   division: 'Diamond',   color: '#A855F7' },
  { tier: 21, title: 'Ascendant 1', division: 'Ascendant', color: '#00FFA3' },
  { tier: 22, title: 'Ascendant 2', division: 'Ascendant', color: '#00FFA3' },
  { tier: 23, title: 'Ascendant 3', division: 'Ascendant', color: '#00FFA3' },
  { tier: 24, title: 'Immortal 1',  division: 'Immortal',  color: '#FF4655' },
  { tier: 25, title: 'Immortal 2',  division: 'Immortal',  color: '#FF4655' },
  { tier: 26, title: 'Immortal 3',  division: 'Immortal',  color: '#FF4655' },
  { tier: 27, title: 'Radiant',     division: 'Radiant',   color: '#FFE500' },
];

// Show milestone tiers only (one per division) for the visual map
const MILESTONE_TIERS = [3, 6, 9, 12, 15, 18, 21, 24, 27];
const TIER_UUID = '03621f52-342b-cf4e-4f86-9350a49c6d04';

function getRankColor(tier: number): string {
  const rank = VALORANT_RANKS.find(r => r.tier === tier);
  return rank?.color || '#6B7280';
}

function getRankTitle(tier: number): string {
  const rank = VALORANT_RANKS.find(r => r.tier === tier);
  return rank?.title || 'Unranked';
}

function getDivision(tier: number): string {
  const rank = VALORANT_RANKS.find(r => r.tier === tier);
  return rank?.division || 'Iron';
}

export default function LevelProgress({
  currentLevel,
  levelTitle,
  totalXp,
  currentXpInLevel,
  xpForNextLevel,
  rankIcon,
}: LevelProgressProps) {
  const progressPercent = xpForNextLevel > 0
    ? Math.min((currentXpInLevel / xpForNextLevel) * 100, 100)
    : 0;
  
  const currentColor = getRankColor(currentLevel);
  
  // Find position in milestone map
  const currentMilestoneIdx = MILESTONE_TIERS.findIndex(t => t > currentLevel);
  const progressThroughMilestones = currentMilestoneIdx === -1
    ? 100 // Past all milestones (Radiant)
    : ((currentMilestoneIdx) / (MILESTONE_TIERS.length)) * 100;

  return (
    <div className="glass-card p-6 mb-6" data-gsap="fade-up">
      <h3 className="font-display text-xl font-bold tracking-wider vibrant-text mb-4 inline-block">
        RANK PROGRESSION
      </h3>

      {/* Current Rank Display */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          {/* Rank Icon from Valorant API */}
          <div
            className="w-16 h-16 rounded-lg bg-[var(--valo-darker)] flex items-center justify-center border-2 relative overflow-hidden"
            style={{ borderColor: currentColor, boxShadow: `0 0 20px ${currentColor}40` }}
          >
            {rankIcon ? (
              <img src={rankIcon} alt={levelTitle} className="w-12 h-12 object-contain" />
            ) : (
              <div className="text-2xl font-bold font-display" style={{ color: currentColor }}>
                {currentLevel}
              </div>
            )}
          </div>
          <div>
            <div className="font-display text-2xl font-bold" style={{ color: currentColor, textShadow: `0 0 10px ${currentColor}40` }}>
              {levelTitle}
            </div>
            <div className="text-sm text-[var(--valo-text-dim)]">
              Tier {currentLevel} · {getDivision(currentLevel)}
            </div>
          </div>
        </div>
        <div className="text-right">
          <div className="font-display text-3xl font-bold text-[var(--valo-cyan)] drop-shadow-[0_0_10px_rgba(0,217,255,0.3)]">
            {totalXp.toLocaleString()} XP
          </div>
          <div className="text-sm text-[var(--valo-text-dim)]">
            {currentXpInLevel} / {xpForNextLevel} RR to rank up
          </div>
        </div>
      </div>

      {/* RR Progress Bar */}
      <div className="mb-6">
        <div className="flex justify-between text-xs text-[var(--valo-text-dim)] mb-1">
          <span>{levelTitle}</span>
          <span className="font-bold" style={{ color: currentColor }}>{currentXpInLevel} / {xpForNextLevel} RR</span>
          <span>{getRankTitle(Math.min(currentLevel + 1, 27))}</span>
        </div>
        <div className="h-4 bg-[var(--valo-darker)] rounded-full overflow-hidden relative border border-white/5">
          <div
            className="h-full rounded-full transition-all duration-1000 relative"
            style={{
              width: `${progressPercent}%`,
              background: `linear-gradient(90deg, ${currentColor}80, ${currentColor})`,
              boxShadow: `0 0 12px ${currentColor}60`,
            }}
          >
            {/* Animated shimmer overlay */}
            <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/25 to-transparent animate-shimmer" />
          </div>
          {/* Glowing tip */}
          {progressPercent > 3 && (
            <div
              className="absolute top-0 h-full w-3 rounded-full blur-sm transition-all duration-1000"
              style={{
                left: `calc(${progressPercent}% - 6px)`,
                backgroundColor: `${currentColor}90`,
              }}
            />
          )}
        </div>
      </div>

      {/* Rank Milestone Map */}
      <div className="relative">
        <div className="flex justify-between relative z-10">
          {MILESTONE_TIERS.map((tier) => {
            const isCompleted = currentLevel >= tier;
            const isCurrent = currentLevel >= tier && (
              tier === 27 || currentLevel < MILESTONE_TIERS[MILESTONE_TIERS.indexOf(tier) + 1]
            );
            const color = getRankColor(tier);
            const division = getDivision(tier);

            return (
              <div key={tier} className="flex flex-col items-center group relative">
                {/* Rank Node */}
                <div
                  className={`w-9 h-9 rounded-full flex items-center justify-center transition-all duration-300 cursor-pointer border-2 ${
                    isCurrent
                      ? 'scale-110'
                      : isCompleted
                      ? ''
                      : 'opacity-40'
                  }`}
                  style={{
                    borderColor: isCompleted ? color : 'var(--valo-gray-light)',
                    backgroundColor: isCompleted ? `${color}20` : 'var(--valo-darker)',
                    boxShadow: isCurrent ? `0 0 15px ${color}50, 0 0 30px ${color}20` : 'none',
                  }}
                  title={`${getRankTitle(tier)} — ${(tier - 3) * 100} XP`}
                >
                  {/* Rank icon from API */}
                  <img
                    src={`https://media.valorant-api.com/competitivetiers/${TIER_UUID}/${tier}/smallicon.png`}
                    alt={getRankTitle(tier)}
                    className="w-5 h-5 object-contain"
                    style={{ filter: isCompleted ? 'none' : 'grayscale(100%) brightness(0.4)' }}
                    onError={(e) => {
                      // Fallback to text if image fails
                      (e.target as HTMLImageElement).style.display = 'none';
                    }}
                  />
                </div>

                {/* Tooltip on hover */}
                <div className="absolute bottom-full mb-2 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-20">
                  <div className="bg-[var(--valo-darker)] backdrop-blur-md border border-[var(--valo-gray-light)] rounded px-2 py-1 text-xs whitespace-nowrap shadow-lg">
                    <div className="font-semibold" style={{ color }}>{getRankTitle(tier)}</div>
                    <div className="text-[var(--valo-text-dim)]">{(tier - 3) * 100} XP required</div>
                  </div>
                </div>

                {/* Division label */}
                <div className={`mt-1.5 text-[9px] font-bold tracking-wider uppercase ${
                  isCurrent ? '' : isCompleted ? 'opacity-80' : 'opacity-30'
                }`}
                  style={{ color: isCompleted ? color : 'var(--valo-text-dim)' }}
                >
                  {division === 'Radiant' ? 'RAD' : division.slice(0, 3).toUpperCase()}
                </div>
              </div>
            );
          })}
        </div>

        {/* Connection line */}
        <div className="absolute top-[18px] left-5 right-5 h-0.5 bg-[var(--valo-gray-light)]/30 -z-0">
          <div
            className="h-full transition-all duration-1000"
            style={{
              width: `${progressThroughMilestones}%`,
              background: `linear-gradient(90deg, ${getRankColor(3)}, ${currentColor})`,
              boxShadow: `0 0 8px ${currentColor}40`,
            }}
          />
        </div>
      </div>
    </div>
  );
}
