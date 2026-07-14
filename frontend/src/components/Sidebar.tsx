"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Building2, ChevronLeft, ChevronRight, Kanban, LayoutDashboard, LogOut, Target, X } from "lucide-react";
import { useAuth } from "@/lib/auth-context";

const NAV_ITEMS = [
  { href: "/", label: "Overview", icon: LayoutDashboard },
  { href: "/businesses", label: "Businesses", icon: Building2 },
  { href: "/leads", label: "Leads", icon: Target },
  { href: "/campaigns", label: "Campaigns", icon: Kanban },
];

interface SidebarProps {
  collapsed: boolean;
  onToggleCollapse: () => void;
  mobileOpen: boolean;
  onCloseMobile: () => void;
}

export function Sidebar({ collapsed, onToggleCollapse, mobileOpen, onCloseMobile }: SidebarProps) {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  return (
    <>
      {/* Mobile backdrop — click to close the drawer */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/60 md:hidden"
          onClick={onCloseMobile}
          aria-hidden="true"
        />
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-40 flex h-screen flex-col border-r border-border-subtle bg-surface
          transition-transform duration-200 md:static md:translate-x-0
          ${mobileOpen ? "translate-x-0" : "-translate-x-full"}
          ${collapsed ? "md:w-16" : "md:w-60"} w-60`}
      >
        <div className="flex items-center justify-between px-4 py-5">
          <div className="flex items-center gap-2 overflow-hidden">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/logo.png" alt="Builderhut.club" className="h-7 w-7 shrink-0 rounded-md object-cover" />
            {!collapsed && (
              <span className="truncate font-display text-lg font-semibold tracking-tight">Builderhut.club</span>
            )}
          </div>
          <button onClick={onCloseMobile} className="text-ink-muted hover:text-ink md:hidden" aria-label="Close menu">
            <X size={18} />
          </button>
        </div>

        <nav className="flex-1 space-y-1 px-3">
          {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
            const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
            return (
              <Link
                key={href}
                href={href}
                onClick={onCloseMobile}
                title={collapsed ? label : undefined}
                className={`flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors ${
                  active
                    ? "bg-surface-raised text-ink border border-border"
                    : "text-ink-muted hover:bg-surface-raised hover:text-ink"
                } ${collapsed ? "md:justify-center md:px-0" : ""}`}
              >
                <Icon size={16} className={`shrink-0 ${active ? "text-brass" : ""}`} />
                <span className={collapsed ? "md:hidden" : ""}>{label}</span>
              </Link>
            );
          })}
        </nav>

        {/* Desktop-only collapse toggle */}
        <button
          onClick={onToggleCollapse}
          className="mx-3 mb-2 hidden items-center justify-center gap-2 rounded-md border border-border-subtle py-1.5 text-xs text-ink-faint transition-colors hover:bg-surface-raised hover:text-ink md:flex"
        >
          {collapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
          {!collapsed && "Collapse"}
        </button>

        <div className="border-t border-border-subtle px-3 py-4">
          {!collapsed && (
            <div className="mb-2 px-3">
              <div className="truncate text-sm text-ink">{user?.full_name}</div>
              <div className="truncate text-xs text-ink-faint">{user?.email}</div>
            </div>
          )}
          <button
            onClick={logout}
            title={collapsed ? "Sign out" : undefined}
            className={`flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm text-ink-muted transition-colors hover:bg-surface-raised hover:text-ink ${
              collapsed ? "md:justify-center md:px-0" : ""
            }`}
          >
            <LogOut size={16} className="shrink-0" />
            <span className={collapsed ? "md:hidden" : ""}>Sign out</span>
          </button>
        </div>
      </aside>
    </>
  );
}