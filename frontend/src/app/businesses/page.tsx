"use client";

import { useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import { Plus, Search, Trash2 } from "lucide-react";
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

  const [showAddForm, setShowAddForm] = useState(false);
  const [newName, setNewName] = useState("");
  const [newCategory, setNewCategory] = useState("");
  const [newCity, setNewCity] = useState("");
  const [newCountry, setNewCountry] = useState("");
  const [newWebsite, setNewWebsite] = useState("");
  const [newPhone, setNewPhone] = useState("");
  const [addStatus, setAddStatus] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

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

  async function handleAddBusiness(event: FormEvent) {
    event.preventDefault();
    setAddStatus("Adding…");
    try {
      await api.businesses.create({
        name: newName,
        category: newCategory,
        city: newCity,
        country: newCountry,
        website_url: newWebsite || undefined,
        phone: newPhone || undefined,
      });
      setAddStatus(null);
      setNewName("");
      setNewCategory("");
      setNewCity("");
      setNewCountry("");
      setNewWebsite("");
      setNewPhone("");
      setShowAddForm(false);
      await load();
    } catch (err) {
      setAddStatus(err instanceof ApiError ? err.message : "Failed to add business.");
    }
  }

  async function handleDelete(businessId: string, name: string) {
    if (!window.confirm(`Delete "${name}"? This also removes its audit history, scores, and emails. This can't be undone.`)) {
      return;
    }
    setDeletingId(businessId);
    try {
      await api.businesses.delete(businessId);
      setBusinesses((prev) => prev.filter((b) => b.id !== businessId));
      setTotal((t) => t - 1);
    } catch {
      window.alert("Failed to delete business.");
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <AppShell>
      <div className="mb-8 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="font-display text-2xl font-semibold text-ink">Businesses</h1>
          <p className="mt-1 text-sm text-ink-muted">{total} tracked</p>
        </div>
        <button onClick={() => setShowAddForm((s) => !s)} className="btn-secondary self-start">
          <Plus size={15} />
          Add business
        </button>
      </div>

      {showAddForm && (
        <form onSubmit={handleAddBusiness} className="card mb-6 grid grid-cols-1 gap-3 p-5 sm:grid-cols-2 lg:grid-cols-3">
          <div className="space-y-1.5">
            <label className="label">Name</label>
            <input className="input" required value={newName} onChange={(e) => setNewName(e.target.value)} />
          </div>
          <div className="space-y-1.5">
            <label className="label">Category</label>
            <input className="input" required value={newCategory} onChange={(e) => setNewCategory(e.target.value)} />
          </div>
          <div className="space-y-1.5">
            <label className="label">City</label>
            <input className="input" required value={newCity} onChange={(e) => setNewCity(e.target.value)} />
          </div>
          <div className="space-y-1.5">
            <label className="label">Country</label>
            <input className="input" required value={newCountry} onChange={(e) => setNewCountry(e.target.value)} />
          </div>
          <div className="space-y-1.5">
            <label className="label">Website (optional)</label>
            <input className="input" value={newWebsite} onChange={(e) => setNewWebsite(e.target.value)} placeholder="https://" />
          </div>
          <div className="space-y-1.5">
            <label className="label">Phone (optional)</label>
            <input className="input" value={newPhone} onChange={(e) => setNewPhone(e.target.value)} />
          </div>
          <div className="col-span-full flex items-center gap-3">
            <button type="submit" className="btn-primary">
              Add
            </button>
            {addStatus && <p className="text-sm text-priority-critical">{addStatus}</p>}
          </div>
        </form>
      )}

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

      <form onSubmit={handleFilter} className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative flex-1 sm:max-w-xs">
          <Search size={15} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink-faint" />
          <input
            className="input pl-9"
            placeholder="Filter by city"
            value={cityFilter}
            onChange={(e) => setCityFilter(e.target.value)}
          />
        </div>
        <input
          className="input sm:max-w-xs"
          placeholder="Filter by category"
          value={categoryFilter}
          onChange={(e) => setCategoryFilter(e.target.value)}
        />
        <button type="submit" className="btn-secondary shrink-0">
          Apply
        </button>
      </form>

      <div className="card overflow-hidden">
        {/* overflow-x-auto so the table scrolls horizontally on narrow
            screens instead of silently clipping columns */}
        <div className="overflow-x-auto">
          <table className="w-full min-w-[720px] text-sm">
            <thead>
              <tr className="border-b border-border-subtle text-left text-xs uppercase tracking-wide text-ink-muted">
                <th className="px-4 py-3 font-medium">Name</th>
                <th className="px-4 py-3 font-medium">City</th>
                <th className="px-4 py-3 font-medium">Category</th>
                <th className="px-4 py-3 font-medium">Rating</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium">Discovered</th>
                <th className="px-4 py-3 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-ink-muted">
                    Loading…
                  </td>
                </tr>
              ) : businesses.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-ink-muted">
                    No businesses yet — run a discovery search above, or add one manually.
                  </td>
                </tr>
              ) : (
                businesses.map((business) => (
                  <tr key={business.id} className="border-b border-border-subtle last:border-0 hover:bg-surface-raised">
                    <td className="px-4 py-3">
                      <Link href={`/businesses/${business.id}`} className="font-medium text-ink hover:text-brass">
                        {business.name}
                      </Link>
                      {business.website_url ? (
                        <div className="text-xs text-ink-faint">{business.website_url}</div>
                      ) : business.is_social_only_lead ? (
                        <div className="mt-1 inline-flex items-center gap-1 rounded-full border border-brass/40 bg-brass/10 px-2 py-0.5 text-xs text-brass">
                          No website — {business.facebook_url ? "Facebook" : business.instagram_url ? "Instagram" : "phone"} only
                        </div>
                      ) : null}
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
                    <td className="px-4 py-3 text-right">
                      <button
                        onClick={() => handleDelete(business.id, business.name)}
                        disabled={deletingId === business.id}
                        className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs text-ink-faint transition-colors hover:bg-priority-critical/10 hover:text-priority-critical disabled:opacity-50"
                        aria-label={`Delete ${business.name}`}
                      >
                        <Trash2 size={14} />
                        {deletingId === business.id ? "Deleting…" : "Delete"}
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </AppShell>
  );
}