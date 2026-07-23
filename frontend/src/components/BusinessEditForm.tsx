"use client";

import { useState } from "react";
import { Pencil, X } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import type { Business } from "@/lib/types";

interface BusinessEditFormProps {
  business: Business;
  onUpdated: (business: Business) => void;
}

export function BusinessEditForm({ business, onUpdated }: BusinessEditFormProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [name, setName] = useState(business.name);
  const [category, setCategory] = useState(business.category);
  const [websiteUrl, setWebsiteUrl] = useState(business.website_url ?? "");
  const [phone, setPhone] = useState(business.phone ?? "");
  const [email, setEmail] = useState(business.email ?? "");
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSave() {
    setIsSaving(true);
    setError(null);
    try {
      const updated = await api.businesses.update(business.id, {
        name,
        category,
        website_url: websiteUrl || undefined,
        phone: phone || undefined,
        email: email || undefined,
      });
      onUpdated(updated);
      setIsEditing(false);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save changes.");
    } finally {
      setIsSaving(false);
    }
  }

  function handleCancel() {
    setName(business.name);
    setCategory(business.category);
    setWebsiteUrl(business.website_url ?? "");
    setPhone(business.phone ?? "");
    setEmail(business.email ?? "");
    setError(null);
    setIsEditing(false);
  }

  if (!isEditing) {
    return (
      <button
        onClick={() => setIsEditing(true)}
        className="mt-1 inline-flex items-center gap-1 text-xs text-ink-faint transition-colors hover:text-brass"
      >
        <Pencil size={12} />
        {business.website_url ? "Edit details" : "Add website / contact info"}
      </button>
    );
  }

  return (
    <div className="card mt-3 max-w-md space-y-3 p-4">
      <div className="flex items-center justify-between">
        <span className="label">Edit business details</span>
        <button onClick={handleCancel} className="text-ink-faint hover:text-ink">
          <X size={16} />
        </button>
      </div>

      <div className="space-y-1.5">
        <label className="label">Name</label>
        <input className="input" value={name} onChange={(e) => setName(e.target.value)} />
      </div>
      <div className="space-y-1.5">
        <label className="label">Category</label>
        <input className="input" value={category} onChange={(e) => setCategory(e.target.value)} />
      </div>
      <div className="space-y-1.5">
        <label className="label">Website URL</label>
        <input
          className="input"
          value={websiteUrl}
          onChange={(e) => setWebsiteUrl(e.target.value)}
          placeholder="https://theirsite.example.com"
        />
        <p className="text-xs text-ink-faint">
          Adding a website here validates it immediately and makes this business auditable.
        </p>
      </div>
      <div className="space-y-1.5">
        <label className="label">Phone</label>
        <input className="input" value={phone} onChange={(e) => setPhone(e.target.value)} />
      </div>
      <div className="space-y-1.5">
        <label className="label">Email</label>
        <input className="input" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
      </div>

      {error && <p className="text-xs text-priority-critical">{error}</p>}

      <div className="flex items-center gap-2">
        <button onClick={handleSave} disabled={isSaving} className="btn-primary text-xs">
          {isSaving ? "Saving…" : "Save"}
        </button>
        <button onClick={handleCancel} className="btn-secondary text-xs">
          Cancel
        </button>
      </div>
    </div>
  );
}