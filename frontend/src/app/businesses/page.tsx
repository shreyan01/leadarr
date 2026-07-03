"use client";

import { useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import { Search } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { api, ApiError } from "@/lib/api";
import { formatDate } from "@/lib/format";
import type { Business, BusinessStatus } from "@/lib/types";

const STATUS_LABELS: Record<BusinessStatus, string> = {
  discovered: "Discovered",
  validated: "Validated",
  audited: "Audited",
  archived: "Archived",
};

export default function BusinessesPage() {
  const [businesses, setBusinesses] = useState<Business[]>([]);
  const [total, setTotal] = useState(0);
  const [cityFilter, setCityFilter] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [isLoading, setIsLoading] = useState(true);

  const [discoverCountry, setDiscoverCountry] = useState("");
  const [discoverCity, setDiscoverCity] = useState("");
  const [discoverCategory, setDiscoverCategory] = useState("");
  const [discoveryStatus, setDiscoveryStatus] = useState<string | null>(null);

  async function load() {
    setIsLoading(true);
    try {
      const res = await api.businesses.list({
        city: cityFilter || undefined,
        category: categoryFilter || undefined,
      });
      setBusinesses(res.items);
      setTotal(res.total);
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleFilter(event: FormEvent) {
    event.preventDefault();
    await load();
  }

  async function handleDiscover(event: FormEvent) {
    event.preventDefault();
    setDiscoveryStatus("Starting discovery…");
    try {
      const { task_id } = await api.discovery.search(discoverCountry, discoverCity, discoverCategory);
      setDiscoveryStatus("Discovery running in the background — refresh in a moment.");
      pollDiscovery(task_id);
    } catch (err) {
      setDiscoveryStatus(err instanceof ApiError ? err.message : "Discovery failed to start.");
    }
  }

  function pollDiscovery(taskId: string) {
    const interval = setInterval(async () => {
      const status = await api.discovery.jobStatus(taskId);
      if (status.status === "completed") {
        clearInterval(interval);
        setDiscoveryStatus(`Discovered ${status.discovered_count ?? 0} businesses.`);
        void load();
      } else if (status.status === "failed") {
        clearInterval(interval);
        setDiscoveryStatus(`Discovery failed: ${status.error ?? "unknown error"}`);
      }
    }, 3000);
  }

  return (
    <AppShell>
      <div className="mb-8 flex items-start justify-between">
        <div>
          <h1 className="font-display text-2xl font-semibold text-ink">Businesses</h1>
          <p className="mt-1 text-sm text-ink-muted">{total} tracked</p>
        </div>
      </div>

      <div className="card mb-6 p-5">
        <h2 className="mb-3 font-display text-sm font-semibold text-ink">Discover new businesses</h2>
        <form onSubmit={handleDiscover} className="flex flex-wrap items-end gap-3">
          <div className="space-y-1.5">
            <label className="label">Country</label>
            <input
              className="input w-36"
              required
              value={discoverCountry}
              onChange={(e) => setDiscoverCountry(e.target.value)}
              placeholder="United States"
            />
          </div>
          <div className="space-y-1.5">
            <label className="label">City</label>
            <input
              className="input w-40"
              required
              value={discoverCity}
              onChange={(e) => setDiscoverCity(e.target.value)}
              placeholder="Austin"
            />
          </div>
          <div className="space-y-1.5">
            <label className="label">Category</label>
            <input
              className="input w-40"
              required
              value={discoverCategory}
              onChange={(e) => setDiscoverCategory(e.target.value)}
              placeholder="Roofing"
            />
          </div>
          <button type="submit" className="btn-primary">
            Discover
          </button>
          {discoveryStatus && <p className="text-sm text-ink-muted">{discoveryStatus}</p>}
        </form>
      </div>

      <form onSubmit={handleFilter} className="mb-4 flex items-center gap-3">
        <div className="relative flex-1 max-w-xs">
          <Search size={15} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink-faint" />
          <input
            className="input pl-9"
            placeholder="Filter by city"
            value={cityFilter}
            onChange={(e) => setCityFilter(e.target.value)}
          />
        </div>
        <input
          className="input max-w-xs"
          placeholder="Filter by category"
          value={categoryFilter}
          onChange={(e) => setCategoryFilter(e.target.value)}
        />
        <button type="submit" className="btn-secondary">
          Apply
        </button>
      </form>

      <div className="card overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border-subtle text-left text-xs uppercase tracking-wide text-ink-muted">
              <th className="px-4 py-3 font-medium">Name</th>
              <th className="px-4 py-3 font-medium">City</th>
              <th className="px-4 py-3 font-medium">Category</th>
              <th className="px-4 py-3 font-medium">Rating</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium">Discovered</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-ink-muted">
                  Loading…
                </td>
              </tr>
            ) : businesses.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-ink-muted">
                  No businesses yet — run a discovery search above.
                </td>
              </tr>
            ) : (
              businesses.map((business) => (
                <tr key={business.id} className="border-b border-border-subtle last:border-0 hover:bg-surface-raised">
                  <td className="px-4 py-3">
                    <Link href={`/businesses/${business.id}`} className="font-medium text-ink hover:text-brass">
                      {business.name}
                    </Link>
                    <div className="text-xs text-ink-faint">{business.website_url}</div>
                  </td>
                  <td className="px-4 py-3 text-ink-muted">{business.city}</td>
                  <td className="px-4 py-3 text-ink-muted">{business.category}</td>
                  <td className="px-4 py-3 text-ink-muted">
                    {business.google_rating ? `${business.google_rating.toFixed(1)} ★ (${business.review_count ?? 0})` : "—"}
                  </td>
                  <td className="px-4 py-3">
                    <span className="rounded-full border border-border px-2 py-0.5 text-xs text-ink-muted">
                      {STATUS_LABELS[business.status]}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-ink-muted">{formatDate(business.discovered_at)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </AppShell>
  );
}
