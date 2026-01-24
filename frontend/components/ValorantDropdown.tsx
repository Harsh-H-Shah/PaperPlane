import React, { useState, useRef, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { motion, AnimatePresence } from 'framer-motion';

interface Option {
  key: string;
  label: string;
}

interface ValorantDropdownProps {
  options: Option[];
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  className?: string;
}

export default function ValorantDropdown({ options, value, onChange, placeholder, className = '' }: ValorantDropdownProps) {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const selectedOption = options.find(opt => opt.key === value);

  // Close when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  const [coords, setCoords] = useState({ top: 0, left: 0, width: 0 });

  const updateCoords = () => {
    if (containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect();
        setCoords({
            top: rect.bottom + 5, // 5px gap
            left: rect.left,
            width: rect.width
        });
    }
  };

  useEffect(() => {
    if (isOpen) {
        updateCoords();
        window.addEventListener('scroll', updateCoords, true);
        window.addEventListener('resize', updateCoords);
    }
    return () => {
        window.removeEventListener('scroll', updateCoords, true);
        window.removeEventListener('resize', updateCoords);
    };
  }, [isOpen]);

  return (
    <div className={`relative min-w-[200px] ${className} ${isOpen ? 'z-[99]' : 'z-auto'}`} ref={containerRef}>
      {/* Trigger Button */}
      <button
        type="button"
        onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            setIsOpen(!isOpen);
        }}
        className={`
          w-full flex items-center justify-between
          bg-[var(--valo-dark)] border border-[var(--valo-gray-light)] 
          text-[var(--valo-text)] px-4 py-3 
          font-bold tracking-wider uppercase text-sm
          transition-all duration-200
          hover:bg-[var(--valo-dark)]/80 hover:border-[var(--valo-text-dim)]
          ${isOpen ? 'border-[var(--valo-red)] bg-[var(--valo-darker)]' : ''}
        `}
        style={{ 
          clipPath: 'polygon(10px 0, 100% 0, 100% calc(100% - 10px), calc(100% - 10px) 100%, 0 100%, 0 10px)',
        }}
      >
        <span className={!selectedOption && placeholder ? 'text-[var(--valo-text-dim)]' : ''}>
           {selectedOption ? selectedOption.label : (placeholder || 'SELECT')}
        </span>
        <svg 
            className={`w-4 h-4 text-[var(--valo-red)] transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`} 
            fill="none" viewBox="0 0 24 24" stroke="currentColor"
        >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Decorative Corner Lines on Trigger */}
      <div className="absolute top-0 right-0 w-2 h-2 border-t-2 border-r-2 border-[var(--valo-red)] pointer-events-none opacity-50" />
      <div className="absolute bottom-0 left-0 w-2 h-2 border-b-2 border-l-2 border-[var(--valo-red)] pointer-events-none opacity-50" />

      {/* Dropdown Menu - Portal Render */}
      {mounted && createPortal(
          <AnimatePresence>
            {isOpen && (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 5 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.15 }}
                className="fixed z-[200001] bg-[#0f1923] border border-[var(--valo-gray-light)] shadow-[20px_20px_60px_rgba(0,0,0,0.8)]"
                style={{ 
                    top: coords.top,
                    left: coords.left,
                    width: coords.width,
                    clipPath: 'polygon(0 0, 100% 0, 100% calc(100% - 10px), calc(100% - 10px) 100%, 0 100%, 0 0)'
                }}
              >
                 {/* Header Line */}
                 <div className="h-1 w-full bg-[var(--valo-red)]" />

                 <div className="max-h-60 overflow-y-auto scrollbar-thin scrollbar-thumb-[var(--valo-red)] scrollbar-track-[var(--valo-dark)]">
                    {options.map((option) => {
                        const isSelected = option.key === value;
                        return (
                            <button
                                key={option.key}
                                type="button"
                                onClick={(e) => {
                                    e.preventDefault();
                                    e.stopPropagation();
                                    onChange(option.key);
                                    setIsOpen(false);
                                }}
                                className={`
                                    w-full text-left px-4 py-3 text-sm font-bold tracking-wider uppercase
                                    transition-colors duration-150 flex items-center justify-between
                                    border-b border-white/5 last:border-0
                                    ${isSelected 
                                        ? 'bg-[var(--valo-red)] text-white' 
                                        : 'text-[var(--valo-text-dim)] hover:bg-[var(--valo-gray-dark)] hover:text-white hover:pl-6'
                                    }
                                `}
                            >
                                {option.label}
                                {isSelected && (
                                    <span className="w-2 h-2 bg-white rounded-full shadow-[0_0_5px_white]" />
                                )}
                            </button>
                        );
                    })}
                 </div>
              </motion.div>
            )}
          </AnimatePresence>,
          document.body
      )}
    </div>
  );
}
