"use client";

import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import type { Role } from "./types";

export interface Session {
  role: Role;
  actorId: string; // investor id or fund manager id
  actorName: string;
}

interface SessionContextValue {
  session: Session | null;
  ready: boolean;
  setSession: (session: Session) => void;
  clearSession: () => void;
}

const SessionContext = createContext<SessionContextValue | null>(null);
const STORAGE_KEY = "truss.session";

// No real auth in v1 — a role/actor picked on "/" and kept in localStorage.
export function SessionProvider({ children }: { children: ReactNode }) {
  const [session, setSessionState] = useState<Session | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      if (raw) setSessionState(JSON.parse(raw));
    } catch {
      // ignore
    }
    setReady(true);
  }, []);

  const value = useMemo<SessionContextValue>(
    () => ({
      session,
      ready,
      setSession: (s) => {
        setSessionState(s);
        try {
          window.localStorage.setItem(STORAGE_KEY, JSON.stringify(s));
        } catch {
          // ignore
        }
      },
      clearSession: () => {
        setSessionState(null);
        try {
          window.localStorage.removeItem(STORAGE_KEY);
        } catch {
          // ignore
        }
      },
    }),
    [session, ready]
  );

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession() {
  const ctx = useContext(SessionContext);
  if (!ctx) throw new Error("useSession must be used within SessionProvider");
  return ctx;
}
