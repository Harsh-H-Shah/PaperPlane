'use client';

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';

interface AuthContextType {
  isAdmin: boolean;
  isLoading: boolean;
  login: (token: string) => Promise<boolean>;
  logout: () => void;
  token: string | null;
}

const AuthContext = createContext<AuthContextType>({
  isAdmin: false,
  isLoading: true,
  login: async () => false,
  logout: () => {},
  token: null,
});

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [isAdmin, setIsAdmin] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';

  const verifyToken = useCallback(async (t: string): Promise<boolean> => {
    try {
      const res = await fetch(`${API_BASE}/api/auth/verify`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${t}` },
      });
      return res.ok;
    } catch {
      return false;
    }
  }, [API_BASE]);

  // Check for stored token on mount
  useEffect(() => {
    const stored = localStorage.getItem('paperplane_admin_token');
    if (stored) {
      verifyToken(stored).then((valid) => {
        if (valid) {
          setToken(stored);
          setIsAdmin(true);
        } else {
          localStorage.removeItem('paperplane_admin_token');
        }
        setIsLoading(false);
      });
    } else {
      setIsLoading(false);
    }
  }, [verifyToken]);

  const login = async (newToken: string): Promise<boolean> => {
    const valid = await verifyToken(newToken);
    if (valid) {
      setToken(newToken);
      setIsAdmin(true);
      localStorage.setItem('paperplane_admin_token', newToken);
      return true;
    }
    return false;
  };

  const logout = () => {
    setToken(null);
    setIsAdmin(false);
    localStorage.removeItem('paperplane_admin_token');
  };

  return (
    <AuthContext.Provider value={{ isAdmin, isLoading, login, logout, token }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
