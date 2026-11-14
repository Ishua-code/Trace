"use client";
import { Bell, ChevronDown } from "lucide-react";
import { usePersona } from "@/lib/persona";
import { StatusBadge } from "@/components/StatusBadge";
import type { User } from "@/lib/types";

interface HeaderProps {
  title?: string;
}

const ROLE_LABEL: Record<string, string> = {
  auditing_head: "Auditing Head",
  auditor: "Auditor",
  auditee: "Auditee",
  admin: "Admin",
};

export function Header({ title }: HeaderProps) {
  const { user, users, setUser } = usePersona();

  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-white/5 bg-slate-950/80 px-6 backdrop-blur">
      {/* Page title */}
      <h1 className="text-sm font-semibold text-slate-200">{title ?? "TRACE"}</h1>

      <div className="flex items-center gap-3">
        {/* Persona switcher */}
        <div className="relative group">
          <button
            id="persona-switcher"
            className="flex items-center gap-2 rounded-lg border border-white/10 bg-slate-800/60 px-3 py-1.5 text-sm text-slate-300 transition-all hover:border-electric/40 hover:text-white"
            aria-label="Switch demo persona"
          >
            <span className="h-2 w-2 rounded-full bg-electric" />
            <span>{user.name}</span>
            <StatusBadge value={user.role} className="text-[10px] px-1.5 py-0 hidden sm:inline-flex" />
            <ChevronDown size={12} className="text-slate-500" />
          </button>

          {/* dropdown */}
          <div className="absolute right-0 top-full z-50 mt-1 hidden w-56 rounded-xl border border-white/10 bg-slate-900 p-1 shadow-xl group-focus-within:block group-hover:block">
            <p className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-widest text-slate-500">
              Demo Personas
            </p>
            {users.map((u: User) => (
              <button
                key={u.id}
                onClick={() => setUser(u)}
                className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-sm text-slate-300 hover:bg-slate-800"
              >
                <span
                  className={`h-2 w-2 rounded-full ${u.id === user.id ? "bg-electric" : "bg-slate-600"}`}
                />
                <div>
                  <div className="font-medium">{u.name}</div>
                  <div className="text-xs text-slate-500">{ROLE_LABEL[u.role]}</div>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Notifications bell */}
        <button
          id="notifications-bell"
          aria-label="Notifications"
          className="relative rounded-lg p-2 text-slate-400 transition-colors hover:bg-slate-800 hover:text-slate-200"
        >
          <Bell size={16} />
          <span className="absolute right-1.5 top-1.5 h-1.5 w-1.5 rounded-full bg-red-500" />
        </button>
      </div>
    </header>
  );
}
