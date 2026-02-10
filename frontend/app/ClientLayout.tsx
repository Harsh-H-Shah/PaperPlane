'use client';

import { useState, useCallback } from 'react';
import { AuthProvider } from '@/lib/auth';
import LoadingScreen from '@/components/LoadingScreen';

export default function ClientLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [showLoading, setShowLoading] = useState(true);
  const [ready, setReady] = useState(false);

  const handleComplete = useCallback(() => {
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
