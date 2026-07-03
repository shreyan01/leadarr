"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { AppShell } from "@/components/AppShell";
import { ScoreGauge } from "@/components/ScoreGauge";
import { PriorityBadge } from "@/components/PriorityBadge";
import { api } from "@/lib/api";
import { formatDate } from "@/lib/format";
import type { LeadPriority, LeadListItem, Business } from "@/lib/types";

const PRIORITY_OPTIONS: (LeadPriority | "all")[] = ["all", "critical", "high", "medium", "low"];

export default function LeadsPage() {
  const [leads, setLeads] = useState<LeadListItem[]>([]);
  const [businessNames, setBusinessNames] = useState<Record<string, Business>>({});
  const [priorityFilter, setPriorityFilter] = useState<LeadPriority | "all">("all");
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function load() {
      setIsLoading(true);
      try {
        const res = await api.leads.list({ priority: priorityFilter === "all" ? undefined : priorityFilter });
        setLeads(res.items);
        const businesses = await Promise.all(res.items.map((l) => api.businesses.get(l.business_id).catch(() => null)));
        const map: Record<string, Business> = {};
        businesses.forEach((b) => {
          if (b) map[b.id] = b;
        });
        setBusinessNames(map);
      } finally {
        setIsLoading(false);
      }
    }
    void load();
  }, [priorityFilter]);

  return (
    <AppShell>
      <div className="mb-6">
        <h1 className="font-display text-2xl font-semibold text-ink">Leads</h1>
        <p className="mt-1 text-sm text-ink-muted">Ranked by opportunity score.</p>
      </div>

      <div className="mb-5 flex gap-2">
        {PRIORITY_OPTIONS.map((option) => (
          <button
            key={option}
            onClick={() => setPriorityFilter(option)}
            className={`rounded-full border px-3 py-1 text-xs font-medium capitalize transition-colors ${
              priorityFilter === option
                ? "border-brass bg-brass/10 text-brass"
                : "border-border text-ink-muted hover:text-ink"
            }`}
          >
            {option}
          </button>
        ))}
      </div>

      {isLoading ? (
        <div className="py-12 text-center text-ink-muted">Loading…</div>
      ) : leads.length === 0 ? (
        <div className="card py-12 text-center text-ink-muted">No leads scored yet.</div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {leads.map((lead) => {
            const business = businessNames[lead.business_id];
            return (
              <Link
                key={lead.business_id}
                href={`/businesses/${lead.business_id}`}
                className="card flex items-center gap-4 p-4 transition-colors hover:border-brass-dim"
              >
                <ScoreGauge score={lead.overall_score} size={52} />
                <div className="min-w-0 flex-1">
                  <div className="truncate font-medium text-ink">{business?.name ?? "—"}</div>
                  <div className="truncate text-xs text-ink-muted">
                    {business?.city}
                    {business?.category ? ` · ${business.category}` : ""}
                  </div>
                  <div className="mt-2 flex items-center gap-2">
                    <PriorityBadge priority={lead.priority} />
                    <span className="text-xs text-ink-faint">{formatDate(lead.scored_at)}</span>
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </AppShell>
  );
}
