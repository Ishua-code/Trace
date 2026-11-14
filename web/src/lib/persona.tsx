"use client";
import { createContext, useContext, useState, type ReactNode } from "react";
import type { User } from "@/lib/types";
import { MOCK_USERS } from "@/lib/mock-data";

interface PersonaContextValue {
  user: User;
  setUser: (u: User) => void;
  users: User[];
}

const PersonaCtx = createContext<PersonaContextValue | null>(null);

export function PersonaProvider({ children }: { children: ReactNode }) {
  // Default to auditing_head so the management dashboard is the first view
  const [user, setUser] = useState<User>(MOCK_USERS[0]);
  return (
    <PersonaCtx.Provider value={{ user, setUser, users: MOCK_USERS }}>
      {children}
    </PersonaCtx.Provider>
  );
}

export function usePersona() {
  const ctx = useContext(PersonaCtx);
  if (!ctx) throw new Error("usePersona must be used within PersonaProvider");
  return ctx;
}
