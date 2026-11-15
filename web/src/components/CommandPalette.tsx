"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Command } from "cmdk";
import { Dialog, DialogContent, DialogTitle } from "@radix-ui/react-dialog";
import {
  AlertTriangle,
  BarChart3,
  Bell,
  ClipboardList,
  GitBranch,
  LayoutDashboard,
  Search,
  ShieldCheck,
  Upload,
} from "lucide-react";

const COMMANDS = [
  { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { label: "Non-Conformances", href: "/ncs", icon: AlertTriangle },
  { label: "Failure Graph", href: "/graph", icon: GitBranch },
  { label: "Approvals", href: "/approvals", icon: ShieldCheck },
  { label: "Risk Plan", href: "/plan", icon: BarChart3 },
  { label: "Upload Plan", href: "/upload", icon: Upload },
  { label: "Search", href: "/search", icon: Search },
  { label: "Audit Log", href: "/audit-log", icon: ClipboardList },
  { label: "Notifications", href: "/notifications", icon: Bell },
  { label: "Proof", href: "/proof", icon: BarChart3 },
];

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const router = useRouter();

  useEffect(() => {
    function handleShortcut(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setOpen((current) => !current);
      }
    }
    window.addEventListener("keydown", handleShortcut);
    return () => window.removeEventListener("keydown", handleShortcut);
  }, []);

  function navigate(href: string) {
    setOpen(false);
    router.push(href);
  }

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="flex min-w-0 items-center gap-2 rounded-lg border border-white/10 bg-slate-900/70 px-3 py-2 text-sm text-slate-400 transition-colors hover:border-electric/40 hover:text-slate-200 sm:w-64"
        aria-label="Search pages and actions"
      >
        <Search size={14} aria-hidden="true" />
        <span className="flex-1 text-left">Jump to…</span>
        <kbd className="hidden rounded border border-white/10 px-1.5 py-0.5 font-mono text-[10px] text-slate-500 sm:inline">⌘K</kbd>
      </button>
      <Dialog open={open} onOpenChange={setOpen}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 z-[99] bg-black/65 backdrop-blur-sm" />
          <DialogContent className="fixed left-1/2 top-[18%] z-[100] w-[min(92vw,36rem)] -translate-x-1/2 overflow-hidden rounded-xl border border-white/10 bg-slate-950 p-0 shadow-2xl shadow-black/60">
            <DialogTitle className="sr-only">Navigate TRACE</DialogTitle>
            <Command label="Navigate TRACE" className="text-slate-200">
            <Command.Input
              autoFocus
              placeholder="Search pages…"
              className="h-12 w-full border-b border-white/10 bg-transparent px-4 text-sm text-white outline-none placeholder:text-slate-500"
            />
            <Command.List className="max-h-[min(60vh,24rem)] overflow-y-auto p-2">
              <Command.Empty className="px-3 py-8 text-center text-sm text-slate-500">No matching pages.</Command.Empty>
              <Command.Group heading="Go to" className="px-1 text-[10px] font-semibold uppercase tracking-wider text-slate-500 [&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:py-2">
                {COMMANDS.map(({ label, href, icon: Icon }) => (
                  <Command.Item
                    key={href}
                    value={label}
                    onSelect={() => navigate(href)}
                    className="flex cursor-pointer items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-slate-300 aria-selected:bg-electric/10 aria-selected:text-electric"
                  >
                    <Icon size={15} aria-hidden="true" />
                    {label}
                  </Command.Item>
                ))}
              </Command.Group>
            </Command.List>
            <div className="border-t border-white/10 px-4 py-2 text-[10px] text-slate-500">↑↓ to navigate · Enter to open · Esc to close</div>
            </Command>
          </DialogContent>
        </Dialog.Portal>
      </Dialog>
    </>
  );
}
