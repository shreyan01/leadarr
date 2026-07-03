"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Building2, Kanban, LayoutDashboard, LogOut, Target } from "lucide-react";
import { useAuth } from "@/lib/auth-context";

const NAV_ITEMS = [
  { href: "/", label: "Overview", icon: LayoutDashboard },
  { href: "/businesses", label: "Businesses", icon: Building2 },
  { href: "/leads", label: "Leads", icon: Target },
  { href: "/campaigns", label: "Campaigns", icon: Kanban },
];

export function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  return (
    <aside className="flex h-screen w-60 flex-col border-r border-border-subtle bg-surface">
      <div className="flex items-center gap-2 px-5 py-5">
        <div className="flex h-7 w-7 items-center justify-center rounded-md bg-brass text-sm font-bold text-canvas">
          L
        </div>
        <span className="font-display text-lg font-semibold tracking-tight">LeadForge</span>
      </div>

      <nav className="flex-1 space-y-1 px-3">
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
          const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={`flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors ${
                active
                  ? "bg-surface-raised text-ink border border-border"
                  : "text-ink-muted hover:bg-surface-raised hover:text-ink"
              }`}
            >
              <Icon size={16} className={active ? "text-brass" : ""} />
              {label}
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-border-subtle px-3 py-4">
        <div className="mb-2 px-3">
          <div className="truncate text-sm text-ink">{user?.full_name}</div>
          <div className="truncate text-xs text-ink-faint">{user?.email}</div>
        </div>
        <button
          onClick={logout}
          className="flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm text-ink-muted transition-colors hover:bg-surface-raised hover:text-ink"
        >
          <LogOut size={16} />
          Sign out
        </button>
      </div>
    </aside>
  );
}
