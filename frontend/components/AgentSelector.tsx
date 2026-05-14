import React, { useEffect, useState, useCallback, useMemo } from 'react';
import useEmblaCarousel from 'embla-carousel-react';
import { motion } from 'framer-motion';
import { VALORANT_AGENTS } from './Sidebar';

interface AgentSelectorProps {
  selectedAgent: string;
  onSelectToken: (agentKey: string) => void;
  disabled?: boolean;
}

export default function AgentSelector({ selectedAgent, onSelectToken, disabled }: AgentSelectorProps) {
  const [emblaRef, emblaApi] = useEmblaCarousel({ 
    loop: true,
    dragFree: true,
    containScroll: 'trimSnaps',
    align: 'center',
    skipSnaps: false,
  });

  const agentsList = useMemo(() => Object.entries(VALORANT_AGENTS), []);
  const [selectedIndex, setSelectedIndex] = useState(0);

  // Sync external selection to carousel
  useEffect(() => {
    if (!emblaApi) return;
    const index = agentsList.findIndex(([key]) => key === selectedAgent);
    if (index !== -1 && index !== selectedIndex) {
      emblaApi.scrollTo(index);
      setSelectedIndex(index);
    }
  }, [selectedAgent, emblaApi, agentsList]);

  // Sync carousel scroll to state
  const onSelect = useCallback(() => {
    if (!emblaApi) return;
    const index = emblaApi.selectedScrollSnap();
    setSelectedIndex(index);
  }, [emblaApi]);

  useEffect(() => {
    if (!emblaApi) return;
    emblaApi.on('select', onSelect);
    emblaApi.on('reInit', onSelect);
    onSelect();
  }, [emblaApi, onSelect]);

  const handleAgentClick = (index: number, key: string) => {
    // When disabled (not admin or saving), still call onSelectToken so the parent
    // can surface an error toast — but skip the optimistic scroll, so the carousel
    // doesn't visually drift away from the actual saved selection.
    if (disabled) {
      onSelectToken(key);
      return;
    }
    if (index !== selectedIndex) {
      emblaApi?.scrollTo(index);
    }
    onSelectToken(key);
  };

  const scrollPrev = useCallback(() => emblaApi && emblaApi.scrollPrev(), [emblaApi]);
  const scrollNext = useCallback(() => emblaApi && emblaApi.scrollNext(), [emblaApi]);

  return (
    <div className="relative w-full group/carousel py-2">
       {/* Controls */}
       <button 
        onClick={scrollPrev}
        className="absolute left-0 top-1/2 -translate-y-1/2 z-20 p-3 bg-[var(--valo-dark)]/80 border border-[var(--valo-gray-light)] text-white hover:bg-[var(--valo-red)] transition-all -ml-4 shadow-lg active:scale-95"
        style={{ clipPath: 'polygon(20% 0, 100% 0, 100% 100%, 0 50%)' }}
      >
        <svg className="w-6 h-6 rotate-180" fill="currentColor" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
      </button>
      
      <button 
        onClick={scrollNext}
        className="absolute right-0 top-1/2 -translate-y-1/2 z-20 p-3 bg-[var(--valo-dark)]/80 border border-[var(--valo-gray-light)] text-white hover:bg-[var(--valo-red)] transition-all -mr-4 shadow-lg active:scale-95"
        style={{ clipPath: 'polygon(0 0, 80% 0, 100% 50%, 0 100%)' }}
      >
        <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
      </button>

      <div className={`overflow-hidden ${disabled ? 'cursor-not-allowed opacity-80' : 'cursor-grab active:cursor-grabbing'}`} ref={emblaRef}>
        <div className="flex touch-pan-y">
           {agentsList.map(([key, agent], index) => {
              const isSelected = index === selectedIndex;
              return (
                <div
                    key={key}
                    className="flex-[0_0_auto] min-w-0 pl-4 sm:pl-8 md:pl-12 relative py-4"
                >
                   <motion.div
                      layout
                      onClick={() => handleAgentClick(index, key)}
                      animate={{
                         scale: isSelected ? 1.05 : 0.85,
                         opacity: isSelected ? 1 : 0.5,
                         zIndex: isSelected ? 50 : 1,
                         y: isSelected ? 0 : 20,
                         filter: isSelected ? 'grayscale(0)' : 'grayscale(0%) brightness(0.7)'
                      }}
                      transition={{
                        type: "spring",
                        stiffness: 300,
                        damping: 30
                      }}
                      className={`relative w-32 sm:w-40 md:w-48 ${disabled ? 'cursor-not-allowed' : 'cursor-pointer'} transform transition-all h-[220px] sm:h-[280px] md:h-[340px]`}
                   >
                        {/* Card Container */}
                        <div
                            className={`
                                w-full h-full relative border bg-[var(--valo-dark)]/90 backdrop-blur-md overflow-visible
                                transition-colors duration-300
                                ${isSelected ? 'border-[var(--valo-red)] box-shadow-[0_0_30px_rgba(255,70,85,0.3)]' : 'border-white/10 hover:border-white/30'}
                            `}
                            style={{
                                clipPath: 'polygon(0 0, 100% 0, 100% calc(100% - 20px), calc(100% - 20px) 100%, 0 100%)',
                            }}
                        >
                            {/* Background Name Text (Vertical) */}
                            <div 
                                className="absolute top-0 bottom-0 right-2 writing-mode-vertical font-display text-4xl font-bold opacity-[0.05] select-none pointer-events-none"
                                style={{ color: agent.color, writingMode: 'vertical-rl' }}
                            >
                                {agent.name.toUpperCase()}
                            </div>

                            {/* Agent Image - Pops out */}
                            <motion.div 
                                className="absolute inset-x-0 bottom-0 top-0 flex items-end justify-center pointer-events-none"
                                animate={{
                                    y: isSelected ? 10 : 15, // Lowered to center better
                                    scale: isSelected ? 1.3 : 0.85, 
                                }}
                            >
                                <img 
                                    src={agent.icon} 
                                    alt={agent.name}
                                    className="w-full h-auto max-w-none drop-shadow-2xl"
                                    style={{
                                        filter: `drop-shadow(0 10px 20px ${agent.color}40)`
                                    }}
                                    draggable={false}
                                />
                            </motion.div>

                            {/* Name Overlay */}
                            <div className="absolute bottom-0 left-0 right-0 p-3 bg-gradient-to-t from-black via-black/80 to-transparent z-10">
                                <motion.div 
                                    className="font-display font-bold text-center tracking-wider"
                                    animate={{
                                        color: isSelected ? agent.color : '#ffffff',
                                        scale: isSelected ? 1.1 : 1
                                    }}
                                >
                                    <span className="text-xl md:text-2xl">{agent.name.toUpperCase()}</span>
                                </motion.div>
                            </div>
                            
                            {/* Top Accent Line */}
                            <div 
                                className="absolute top-0 left-0 right-0 h-1 opacity-80"
                                style={{ backgroundColor: agent.color }}
                            />
                        </div>
                   </motion.div>
                </div>
              );
           })}
        </div>
      </div>
      
       {/* Fade Sides */}
       <div className="absolute left-0 top-0 bottom-0 w-12 sm:w-20 md:w-32 bg-gradient-to-r from-[var(--valo-darker)] via-[var(--valo-darker)]/80 to-transparent pointer-events-none z-10" />
       <div className="absolute right-0 top-0 bottom-0 w-12 sm:w-20 md:w-32 bg-gradient-to-l from-[var(--valo-darker)] via-[var(--valo-darker)]/80 to-transparent pointer-events-none z-10" />
    </div>
  );
}
