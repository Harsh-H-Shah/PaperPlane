'use client';

import { useState, useEffect, useCallback } from 'react';
import { AuthProvider } from '@/lib/auth';
import LoadingScreen from '@/components/LoadingScreen';

export default function ClientLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [showLoading, setShowLoading] = useState(false);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    // Only show loading screen once per browser session
    const hasLoaded = sessionStorage.getItem('pp_loaded');
    if (!hasLoaded) {
      setShowLoading(true);
    } else {
      setReady(true);
    }
  }, []);

  const handleComplete = useCallback(() => {
    sessionStorage.setItem('pp_loaded', '1');
    setShowLoading(false);
    setReady(true);
  }, []);

  return (
    <AuthProvider>
      {showLoading && <LoadingScreen onComplete={handleComplete} />}
      <div style={{ opacity: ready ? 1 : 0, transition: 'opacity 0.3s ease' }}>
        {children}
      </div>
    </AuthProvider>
  );
}
