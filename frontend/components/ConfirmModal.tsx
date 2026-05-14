import { useEffect, useState } from 'react';

interface ConfirmModalProps {
  isOpen: boolean;
  title: string;
  message: string;
  onConfirm: () => void;
  onCancel: () => void;
  isDestructive?: boolean;
}

export default function ConfirmModal({ 
  isOpen, 
  title, 
  message, 
  onConfirm, 
  onCancel,
  isDestructive = false 
}: ConfirmModalProps) {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    if (isOpen) {
      setIsVisible(true);
    } else {
      const timer = setTimeout(() => setIsVisible(false), 300); // Wait for exit animation
      return () => clearTimeout(timer);
    }
  }, [isOpen]);

  if (!isVisible && !isOpen) return null;

  return (
    <div 
      className={`fixed inset-0 z-50 flex items-center justify-center p-4 transition-opacity duration-300 ${isOpen ? 'opacity-100' : 'opacity-0'}`}
    >
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black/80 backdrop-blur-sm"
        onClick={onCancel}
      />

      {/* Modal Content */}
      <div 
        className={`relative w-full max-w-md bg-[var(--valo-darker)] tech-border border transition-all duration-300 transform ${isOpen ? 'scale-100 translate-y-0' : 'scale-95 translate-y-4'}`}
      >
        {/* Header decoration */}
        <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-[var(--valo-red)] to-transparent opacity-50" />
        
        <div className="p-5 sm:p-6">
          <h3 className="font-display text-xl sm:text-2xl font-bold text-[var(--valo-text)] mb-2 flex items-center gap-2">
            {isDestructive && <span className="text-[var(--valo-red)]">⚠️</span>}
            {title}
          </h3>

          <p className="text-sm sm:text-base text-[var(--valo-text-dim)] mb-6 sm:mb-8 leading-relaxed">
            {message}
          </p>

          <div className="flex flex-col-reverse sm:flex-row sm:justify-end gap-2 sm:gap-3">
            <button
              onClick={onCancel}
              className="px-6 py-2 rounded font-semibold text-[var(--valo-text-dim)] hover:text-[var(--valo-text)] hover:bg-[var(--valo-gray)] transition-colors"
            >
              CANCEL
            </button>
            <button
              onClick={onConfirm}
              className={`px-6 py-2 rounded font-semibold text-white transition-all transform active:scale-95 ${
                isDestructive 
                  ? 'bg-[var(--valo-red)] hover:bg-red-600 shadow-lg shadow-red-900/20' 
                  : 'bg-[var(--valo-cyan)] hover:bg-cyan-600 shadow-lg shadow-cyan-900/20 text-black'
              }`}
            >
              {isDestructive ? 'CONFIRM' : 'OK'}
            </button>
          </div>
        </div>
        
        {/* Corner accents */}
        <div className="absolute top-0 right-0 w-2 h-2 border-t border-r border-[var(--valo-text-dim)]" />
        <div className="absolute bottom-0 left-0 w-2 h-2 border-b border-l border-[var(--valo-text-dim)]" />
      </div>
    </div>
  );
}
