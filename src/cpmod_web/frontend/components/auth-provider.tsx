'use client';

import { createContext, useContext, useEffect, useMemo, useState } from 'react';

import { supabase } from '../lib/supabase';

type AuthContextValue = {
  loading: boolean;
  isAuthed: boolean;
  userEmail: string | null;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [loading, setLoading] = useState(true);
  const [isAuthed, setIsAuthed] = useState(false);
  const [userEmail, setUserEmail] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;

    async function loadSession() {
      const { data } = await supabase.auth.getSession();
      if (!mounted) return;
      const session = data.session;
      const token = session?.access_token ?? null;
      if (token) {
        localStorage.setItem('cpmod-access-token', token);
      } else {
        localStorage.removeItem('cpmod-access-token');
      }
      setIsAuthed(Boolean(token));
      setUserEmail(session?.user?.email ?? null);
      setLoading(false);
    }

    void loadSession();

    const { data } = supabase.auth.onAuthStateChange((_event, session) => {
      const token = session?.access_token ?? null;
      if (token) {
        localStorage.setItem('cpmod-access-token', token);
      } else {
        localStorage.removeItem('cpmod-access-token');
      }
      setIsAuthed(Boolean(token));
      setUserEmail(session?.user?.email ?? null);
      setLoading(false);
    });

    return () => {
      mounted = false;
      data.subscription.unsubscribe();
    };
  }, []);

  async function logout() {
    await supabase.auth.signOut();
    localStorage.removeItem('cpmod-access-token');
    setIsAuthed(false);
    setUserEmail(null);
  }

  const value = useMemo<AuthContextValue>(
    () => ({ loading, isAuthed, userEmail, logout }),
    [loading, isAuthed, userEmail],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used inside AuthProvider');
  }
  return ctx;
}
