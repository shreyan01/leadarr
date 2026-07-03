"use client";

import { useEffect, useState } from "react";
import { Building2, Mail, Target, TrendingUp } from "lucide-react";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from "recharts";
import { AppShell } from "@/components/AppShell";
import { StatCard } from "@/components/StatCard";
import { api } from "@/lib/api";
import type { LeadListItem } from "@/lib/types";

const PRIORITY_CHART_COLORS: Record<string, string> = {
  critical: "#E5484D",
  high: "#E0932F",
  medium: "#4C8DFF",
  low: "#5B6478",
};

export default function OverviewPage() {
  const [leads, setLeads] = useState<LeadListItem[]>([]);
  const [totalBusinesses, setTotalBusinesses] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [leadsRes, businessesRes] = await Promise.all([
          api.leads.list({ page: 1 }),
          api.businesses.list({ page: 1 }),
        ]);
        setLeads(leadsRes.items);
        setTotalBusinesses(businessesRes.total);
      } finally {
        setIsLoading(false);
      }
    }
    void load();
  }, []);

  const priorityCounts = leads.reduce<Record<string, number>>((acc, lead) => {
    acc[lead.priority] = (acc[lead.priority] ?? 0) + 1;
    return acc;
  }, {});
  const chartData = Object.entries(priorityCounts).map(([priority, count]) => ({ name: priority, value: count }));
  const avgScore = leads.length ? leads.reduce((sum, l) => sum + l.overall_score, 0) / leads.length : 0;
  const criticalCount = priorityCounts.critical ?? 0;

  return (
    <AppShell>
      <div className="mb-8">
        <h1 className="font-display text-2xl font-semibold text-ink">Overview</h1>
        <p className="mt-1 text-sm text-ink-muted">Where your pipeline stands right now.</p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Businesses tracked" value={totalBusinesses ?? "—"} icon={Building2} />
        <StatCard label="Scored leads" value={leads.length} icon={Target} />
        <StatCard label="Avg. opportunity score" value={leads.length ? Math.round(avgScore) : "—"} icon={TrendingUp} />
        <StatCard label="Critical priority" value={criticalCount} icon={Mail} hint="Ready for outreach" />
      </div>

      <div className="mt-6 card p-6">
        <h2 className="mb-4 font-display text-base font-semibold text-ink">Lead priority distribution</h2>
        {isLoading ? (
          <div className="py-12 text-center text-sm text-ink-muted">Loading…</div>
        ) : chartData.length === 0 ? (
          <div className="py-12 text-center text-sm text-ink-muted">
            No scored leads yet. Discover and audit businesses to see them here.
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={280}>
            <PieChart>
              <Pie data={chartData} dataKey="value" nameKey="name" innerRadius={60} outerRadius={100} paddingAngle={2}>
                {chartData.map((entry) => (
                  <Cell key={entry.name} fill={PRIORITY_CHART_COLORS[entry.name] ?? "#5B6478"} stroke="none" />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{ background: "#181D29", border: "1px solid #242B3A", borderRadius: 8 }}
                labelStyle={{ color: "#E7E9EE" }}
              />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        )}
      </div>
    </AppShell>
  );
}
