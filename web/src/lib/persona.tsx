"use client";
import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import type { User } from "@/lib/types";
import { api, setToken } from "@/lib/api";

interface PersonaContextValue {
  user: User;
  setUser: (u: User) => void;
  users: User[];
}

const PersonaCtx = createContext<PersonaContextValue | null>(null);

export function PersonaProvider({ children }: { children: ReactNode }) {
  const [user, setUserState] = useState<User | null>(null);
  const [users, setUsers] = useState<User[]>([]);
  const [error, setError] = useState("");

  async function loginAs(id: number) {
    const r = await api.login(id);
    setToken(r.access_token);
    setUserState(r.user as unknown as User);
  }

  useEffect(() => {
    api.personas().then((p) => setUsers(p as unknown as User[])).catch(() => {});
    loginAs(2).catch((e) => setError(String(e)));
  }, []);

  const setUser = (u: User) => {
    const id = (u as unknown as { id: number }).id;
    loginAs(id).catch((e) => setError(String(e)));
  };

  if (!user) {
    return <div className="p-6 text-slate-400">{error || "Connecting to TRACE API..."}</div>;
  }
  return <PersonaCtx.Provider value={{ user, setUser, users }}>{children}</PersonaCtx.Provider>;
}

export function usePersona() {
  const ctx = useContext(PersonaCtx);
  if (!ctx) throw new Error("usePersona must be used within PersonaProvider");
  return ctx;
}