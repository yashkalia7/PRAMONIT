/** Session state: who is signed in, and the actions that change that. */

import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';

import { loadTokens, saveTokens } from '@/api/client';
import { endpoints } from '@/api/endpoints';
import type { AuthResponse, CoachRegisterPayload, Me, StudentRegisterPayload } from '@/api/types';

type AuthState = {
  user: Me | null;
  ready: boolean;
  signingIn: boolean;
  login: (email: string, password: string) => Promise<Me>;
  registerStudent: (payload: StudentRegisterPayload) => Promise<Me>;
  registerCoach: (payload: CoachRegisterPayload) => Promise<Me>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
};

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<Me | null>(null);
  const [ready, setReady] = useState(false);
  const [signingIn, setSigningIn] = useState(false);

  // On boot, a stored refresh token is enough to restore the session — the
  // client refreshes the access token transparently on the first 401.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const tokens = await loadTokens();
        if (tokens?.access_token) {
          const me = await endpoints.me();
          if (!cancelled) setUser(me);
        }
      } catch {
        await saveTokens(null);
      } finally {
        if (!cancelled) setReady(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const adopt = useCallback(async (response: AuthResponse) => {
    await saveTokens(response.tokens);
    setUser(response.user);
    return response.user;
  }, []);

  const login = useCallback(
    async (email: string, password: string) => {
      setSigningIn(true);
      try {
        return await adopt(await endpoints.login(email, password));
      } finally {
        setSigningIn(false);
      }
    },
    [adopt],
  );

  const registerStudent = useCallback(
    async (payload: StudentRegisterPayload) => {
      setSigningIn(true);
      try {
        return await adopt(await endpoints.registerStudent(payload));
      } finally {
        setSigningIn(false);
      }
    },
    [adopt],
  );

  const registerCoach = useCallback(
    async (payload: CoachRegisterPayload) => {
      setSigningIn(true);
      try {
        return await adopt(await endpoints.registerCoach(payload));
      } finally {
        setSigningIn(false);
      }
    },
    [adopt],
  );

  const logout = useCallback(async () => {
    await saveTokens(null);
    setUser(null);
  }, []);

  const refreshUser = useCallback(async () => {
    try {
      setUser(await endpoints.me());
    } catch {
      /* leave the current user in place; the next request will surface it */
    }
  }, []);

  const value = useMemo(
    () => ({ user, ready, signingIn, login, registerStudent, registerCoach, logout, refreshUser }),
    [user, ready, signingIn, login, registerStudent, registerCoach, logout, refreshUser],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used inside <AuthProvider>');
  return context;
}
