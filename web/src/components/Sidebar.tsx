"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  ClipboardList,
  AlertTriangle,
  GitBranch,
  CheckSquare,
  BarChart3,
  Bell,
  Search,
  Settings,
  ShieldCheck,
  Calendar,
  Upload,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { usePersona } from "@/lib/persona";
import type { Role } from "@/lib/types";

interface NavItem {
  href: string;
  label: string;
  icon: React.ElementType;
  roles: Role[];
  badge?: number;
}

const NAV_ITEMS: NavItem[] = [
  {
    href: "/dashboard",
    label: "Dashboard",
    icon: LayoutDashboard,
    roles: ["admin", "auditing_head", "auditor", "auditee"],
  },
  {
    href: "/schedule",
    label: "Schedule",
    icon: Calendar,
    roles: ["admin", "auditing_head", "auditor"],
  },
  {
    href: "/ncs",
    label: "Non-Conformances",
    icon: AlertTriangle,
    roles: ["admin", "auditing_head", "auditor", "auditee"],
  },
  {
    href: "/checklist",
    label: "Audit Checklist",
    icon: ClipboardList,
    roles: ["auditor"],
  },
  {
    href: "/actions",
    label: "My Actions",
    icon: CheckSquare,
    roles: ["auditee"],
  },
  {
    href: "/approvals",
    label: "Approvals",
    icon: ShieldCheck,
    roles: ["auditing_head", "admin"],
  },
  {
    href: "/graph",
    label: "Failure Graph",
    icon: GitBranch,
    roles: ["admin", "auditing_head", "auditor"],
  },
  {
    href: "/plan",
    label: "Risk Plan",
    icon: BarChart3,
    roles: ["admin", "auditing_head"],
  },
  {
    href: "/upload",
    label: "Upload Plan",
    icon: Upload,
    roles: ["admin", "auditing_head"],
  },
  {
    href: "/search",
    label: "Search",
    icon: Search,
    roles: ["admin", "auditing_head", "auditor", "auditee"],
  },
  {
    href: "/proof",
    label: "Proof",
    icon: BarChart3,
    roles: ["admin", "auditing_head"],
  },
  {
    href: "/audit-log",
    label: "Audit Log",
    icon: ShieldCheck,
    roles: ["admin", "auditing_head"],
  },
  {
    href: "/notifications",
    label: "Notifications",
    icon: Bell,
    roles: ["admin", "auditing_head", "auditor", "auditee"],
  },
];

export function Sidebar() {
  const pathname = usePathname();
  const { user } = usePersona();

  const visible = NAV_ITEMS.filter((item) => item.roles.includes(user.role));

  return (
    <aside className="flex h-screen w-60 shrink-0 flex-col border-r border-white/5 bg-slate-950">
      {/* Logo */}
      <div className="flex items-center gap-2.5 border-b border-white/5 px-5 py-4">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-electric/20 ring-1 ring-electric/40">
          <span className="text-sm font-black text-electric">T</span>
        </div>
        <div>
          <span className="text-sm font-bold tracking-tight text-white">TRACE</span>
          <p className="text-[10px] text-slate-500">Audit Intelligence</p>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto px-3 py-4">
        <ul className="flex flex-col gap-0.5">
          {visible.map((item) => {
            const active = pathname === item.href || pathname.startsWith(item.href + "/");
            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  className={cn(
                    "group flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-all duration-150",
                    active
                      ? "bg-electric/10 text-electric"
                      : "text-slate-400 hover:bg-slate-800/60 hover:text-slate-200"
                  )}
                >
                  <item.icon
                    size={16}
                    className={cn(
                      "shrink-0 transition-colors",
                      active ? "text-electric" : "text-slate-500 group-hover:text-slate-300"
                    )}
                  />
                  <span>{item.label}</span>
                  {item.badge != null && item.badge > 0 && (
                    <span className="ml-auto flex h-4 min-w-4 items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-bold text-white">
                      {item.badge}
                    </span>
                  )}
                  {active && (
                    <span className="ml-auto h-1.5 w-1.5 rounded-full bg-electric" />
                  )}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      {/* Bottom: settings */}
      <div className="border-t border-white/5 px-3 py-3">
        <Link
          href="/settings"
          className="flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-slate-500 hover:bg-slate-800/60 hover:text-slate-300"
        >
          <Settings size={16} />
          Settings
        </Link>
      </div>
    </aside>
  );
}
