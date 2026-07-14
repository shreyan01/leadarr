"use client";

import { useEffect, useState, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { Menu } from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { Sidebar } from "./Sidebar";

export function AppShell({ children }: { children: ReactNode }) {
  const { user, isLoading } = useAuth();
  const router = useRouter();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    if (!isLoading && !user) {
      router.replace("/login");
    }
  }, [isLoading, user, router]);

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center text-ink-muted">
        Loading…
      </div>
    );
  }

  if (!user) return null;

  return (
    <div className="flex">
      <Sidebar
        collapsed={collapsed}
        onToggleCollapse={() => setCollapsed((c) => !c)}
        mobileOpen={mobileOpen}
        onCloseMobile={() => setMobileOpen(false)}
      />
      <div className="flex min-h-screen flex-1 flex-col">
        {/* Mobile-only top bar with hamburger — the sidebar is an
            off-canvas drawer below the md breakpoint */}
        <div className="flex items-center gap-3 border-b border-border-subtle bg-surface px-4 py-3 md:hidden">
          <button
            onClick={() => setMobileOpen(true)}
            className="text-ink-muted hover:text-ink"
            aria-label="Open menu"
          >
            <Menu size={20} />
          </button>
          <span className="font-display text-base font-semibold">Builderhut.club</span>
        </div>
        <main className="flex-1 overflow-y-auto bg-canvas px-4 py-6 sm:px-6 md:px-8 md:py-8">{children}</main>
      </div>
    </div>
  );
}