'use client';

import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import ValorantDropdown from './ValorantDropdown';

interface ManualJobModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: {
    title: string;
    company: string;
    url: string;
    location: string;
    application_type: string;
  }) => Promise<void>;
}

export default function ManualJobModal({ isOpen, onClose, onSubmit }: ManualJobModalProps) {
  const [isVisible, setIsVisible] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formData, setFormData] = useState({
    title: '',
    company: '',
    url: '',
    location: '',
    application_type: 'unknown',
  });

  useEffect(() => {
    if (isOpen) {
      setIsVisible(true);
    } else {
      const timer = setTimeout(() => setIsVisible(false), 300);
      return () => clearTimeout(timer);
    }
  }, [isOpen]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.title || !formData.company || !formData.url) return;
    
    setIsSubmitting(true);
    try {
      await onSubmit(formData);
      setFormData({
        title: '',
        company: '',
        url: '',
        location: '',
        application_type: 'unknown',
      });
      onClose();
    } catch (err) {
      console.error('Failed to submit manual job:', err);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!isVisible && !isOpen) return null;

  const inputClasses = "w-full bg-[var(--valo-dark)] border border-[var(--valo-gray-light)] text-[var(--valo-text)] px-4 py-3 focus:outline-none focus:border-[var(--valo-cyan)] transition-colors";
  const labelClasses = "block text-[var(--valo-text-dim)] text-xs font-bold tracking-widest uppercase mb-1";

  const appTypes = [
    { key: 'unknown', label: 'AUTO DETECT' },
    { key: 'ashby', label: 'ASHBY' },
    { key: 'greenhouse', label: 'GREENHOUSE' },
    { key: 'lever', label: 'LEVER' },
    { key: 'workday', label: 'WORKDAY' },
    { key: 'smartrecruiters', label: 'SMARTRECRUITERS' },
  ];

  return (
    <div className={`fixed inset-0 z-50 flex items-center justify-center p-4 transition-opacity duration-300 ${isOpen ? 'opacity-100' : 'opacity-0'}`}>
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/80 backdrop-blur-sm" onClick={onClose} />

      {/* Modal Content */}
      <motion.div 
        initial={{ scale: 0.95, opacity: 0, y: 20 }}
        animate={isOpen ? { scale: 1, opacity: 1, y: 0 } : { scale: 0.95, opacity: 0, y: 20 }}
        className="relative w-full max-w-lg bg-[var(--valo-darker)] tech-border border overflow-visible"
      >
        <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-[var(--valo-cyan)] to-transparent opacity-50" />
        
        <form onSubmit={handleSubmit} className="p-8 overflow-visible">
          <header className="mb-8">
            <div className="flex items-center gap-2 text-[var(--valo-cyan)] text-xs font-bold tracking-widest mb-1">
              <span className="w-2 h-2 bg-[var(--valo-cyan)] rounded-full animate-pulse" />
              NEW INTEL
            </div>
            <h2 className="font-display text-3xl font-bold text-[var(--valo-text)] tracking-wider">MANUAL MISSION ENTRY</h2>
          </header>

          <div className="space-y-6">
            <div>
              <label className={labelClasses}>Mission Title *</label>
              <input 
                type="text" 
                required 
                placeholder="SOFTWARE ENGINEER..." 
                className={inputClasses}
                value={formData.title}
                onChange={e => setFormData({...formData, title: e.target.value})}
                style={{ clipPath: 'polygon(0 0, 100% 0, 100% calc(100% - 10px), calc(100% - 10px) 100%, 0 100%)' }}
              />
            </div>

            <div>
              <label className={labelClasses}>Target Organization *</label>
              <input 
                type="text" 
                required 
                placeholder="RIOT GAMES..." 
                className={inputClasses}
                value={formData.company}
                onChange={e => setFormData({...formData, company: e.target.value})}
                style={{ clipPath: 'polygon(0 0, 100% 0, 100% calc(100% - 10px), calc(100% - 10px) 100%, 0 100%)' }}
              />
            </div>

            <div>
              <label className={labelClasses}>Direct Intel Link (URL) *</label>
              <input 
                type="url" 
                required 
                placeholder="HTTPS://..." 
                className={inputClasses}
                value={formData.url}
                onChange={e => setFormData({...formData, url: e.target.value})}
                style={{ clipPath: 'polygon(0 0, 100% 0, 100% calc(100% - 10px), calc(100% - 10px) 100%, 0 100%)' }}
              />
            </div>

            <div className="grid grid-cols-2 gap-4 relative z-10">
              <div>
                <label className={labelClasses}>Location</label>
                <input 
                  type="text" 
                  placeholder="REMOTE / NYC..." 
                  className={inputClasses}
                  value={formData.location}
                  onChange={e => setFormData({...formData, location: e.target.value})}
                  style={{ clipPath: 'polygon(0 0, 100% 0, 100% calc(100% - 10px), calc(100% - 10px) 100%, 0 100%)' }}
                />
              </div>
              <div className="relative">
                <label className={labelClasses}>Platform Type</label>
                <ValorantDropdown 
                  options={appTypes}
                  value={formData.application_type}
                  onChange={val => setFormData({...formData, application_type: val})}
                  className="w-full"
                />
              </div>
            </div>
          </div>

          <footer className="mt-10 flex justify-end gap-4">
            <button
              type="button"
              onClick={onClose}
              className="px-8 py-3 text-xs font-bold tracking-widest text-[var(--valo-text-dim)] hover:text-white transition-colors"
            >
              ABORT
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className={`
                px-10 py-3 bg-[var(--valo-cyan)] text-black font-bold tracking-widest text-xs
                transition-all transform active:scale-95 shadow-[0_0_20px_rgba(0,255,255,0.2)]
                hover:shadow-[0_0_30px_rgba(0,255,255,0.4)] hover:bg-cyan-400
                disabled:opacity-50 disabled:cursor-not-allowed
              `}
              style={{ clipPath: 'polygon(10% 0, 100% 0, 100% 70%, 90% 100%, 0 100%, 0 30%)' }}
            >
              {isSubmitting ? 'ENCRYPTING...' : 'DECOY DEPLOYED'}
            </button>
          </footer>
        </form>

        <div className="absolute top-0 right-0 w-4 h-4 border-t border-r border-[var(--valo-text-dim)] opacity-30" />
        <div className="absolute bottom-0 left-0 w-4 h-4 border-b border-l border-[var(--valo-text-dim)] opacity-30" />
      </motion.div>
    </div>
  );
}
