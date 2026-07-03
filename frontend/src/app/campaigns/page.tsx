"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { AppShell } from "@/components/AppShell";
import { api } from "@/lib/api";
import type { Campaign, CampaignStage } from "@/lib/types";

const STAGES: { key: CampaignStage; label: string }[] = [
  { key: "discovered", label: "Discovered" },
  { key: "audited", label: "Audited" },
  { key: "email_drafted", label: "Drafted" },
  { key: "sent", label: "Sent" },
  { key: "opened", label: "Opened" },
  { key: "clicked", label: "Clicked" },
  { key: "responded", label: "Responded" },
  { key: "meeting_scheduled", label: "Meeting" },
  { key: "closed_won", label: "Won" },
  { key: "closed_lost", label: "Lost" },
];

export default function CampaignsPage() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function load() {
      setIsLoading(true);
      try {
        const res = await api.campaigns.list();
        setCampaigns(res);
      } finally {
        setIsLoading(false);
      }
    }
    void load();
  }, []);

  async function moveCampaign(campaignId: string, stage: CampaignStage) {
    const updated = await api.campaigns.setStage(campaignId, stage);
    setCampaigns((prev) => prev.map((c) => (c.id === campaignId ? updated : c)));
  }

  const byStage = STAGES.map(({ key, label }) => ({
    key,
    label,
    items: campaigns.filter((c) => c.stage === key),
  }));

  return (
    <AppShell>
      <div className="mb-6">
        <h1 className="font-display text-2xl font-semibold text-ink">Campaigns</h1>
        <p className="mt-1 text-sm text-ink-muted">Track every lead from discovery through close.</p>
      </div>

      {isLoading ? (
        <div className="py-12 text-center text-ink-muted">Loading…</div>
      ) : (
        <div className="flex gap-4 overflow-x-auto pb-4">
          {byStage.map((column) => (
            <div key={column.key} className="w-64 shrink-0">
              <div className="mb-2 flex items-center justify-between px-1">
                <h2 className="text-xs font-semibold uppercase tracking-wide text-ink-muted">{column.label}</h2>
                <span className="text-xs text-ink-faint">{column.items.length}</span>
              </div>
              <div className="space-y-2">
                {column.items.map((campaign) => (
                  <div key={campaign.id} className="card p-3">
                    <Link href={`/businesses/${campaign.business_id}`} className="text-sm font-medium text-ink hover:text-brass">
                      {campaign.name}
                    </Link>
                    {campaign.next_follow_up_at && (
                      <div className="mt-1 text-xs text-ink-faint">
                        Follow up {new Date(campaign.next_follow_up_at).toLocaleDateString()}
                      </div>
                    )}
                    <select
                      className="mt-2 w-full rounded-md border border-border bg-surface-raised px-2 py-1 text-xs text-ink"
                      value={campaign.stage}
                      onChange={(e) => moveCampaign(campaign.id, e.target.value as CampaignStage)}
                    >
                      {STAGES.map((s) => (
                        <option key={s.key} value={s.key}>
                          {s.label}
                        </option>
                      ))}
                      <option value="archived">Archived</option>
                    </select>
                  </div>
                ))}
                {column.items.length === 0 && (
                  <div className="rounded-card border border-dashed border-border-subtle px-3 py-6 text-center text-xs text-ink-faint">
                    Empty
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </AppShell>
  );
}
