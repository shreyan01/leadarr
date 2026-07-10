"use client";

import { useState } from "react";
import { Pencil, Send, Trash2, X } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import type { OutreachEmail } from "@/lib/types";

interface OutreachEmailCardProps {
  email: OutreachEmail;
  defaultRecipient?: string | null;
  onUpdated: (email: OutreachEmail) => void;
  onDeleted: (emailId: string) => void;
}

export function OutreachEmailCard({ email, defaultRecipient, onUpdated, onDeleted }: OutreachEmailCardProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [subject, setSubject] = useState(email.subject);
  const [bodyText, setBodyText] = useState(email.body_text);
  const [isSaving, setIsSaving] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [showSendForm, setShowSendForm] = useState(false);
  const [recipient, setRecipient] = useState(defaultRecipient ?? "");
  const [error, setError] = useState<string | null>(null);

  async function handleSave() {
    setIsSaving(true);
    setError(null);
    try {
      const updated = await api.emails.update(email.id, { subject, body_text: bodyText });
      onUpdated(updated);
      setIsEditing(false);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save changes.");
    } finally {
      setIsSaving(false);
    }
  }

  async function handleDelete() {
    if (!window.confirm("Delete this draft? This can't be undone.")) return;
    setIsDeleting(true);
    try {
      await api.emails.delete(email.id);
      onDeleted(email.id);
    } catch {
      setError("Failed to delete draft.");
      setIsDeleting(false);
    }
  }

  async function handleSend() {
    if (!recipient.trim()) {
      setError("Enter a recipient email address.");
      return;
    }
    setIsSending(true);
    setError(null);
    try {
      const updated = await api.emails.send(email.id, recipient.trim());
      onUpdated(updated);
      setShowSendForm(false);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to send email.");
    } finally {
      setIsSending(false);
    }
  }

  const isSent = email.status === "sent";

  return (
    <div className="rounded-md border border-border-subtle p-4">
      <div className="mb-2 flex items-start justify-between gap-3">
        {isEditing ? (
          <input
            className="input flex-1 font-medium"
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
          />
        ) : (
          <span className="font-medium text-ink">{email.subject}</span>
        )}
        <span
          className={`shrink-0 rounded-full border px-2 py-0.5 text-xs uppercase ${
            isSent
              ? "border-priority-low/40 bg-priority-low/10 text-priority-low"
              : "border-border text-ink-faint"
          }`}
        >
          {email.status}
        </span>
      </div>

      {isEditing ? (
        <textarea
          className="input min-h-[160px] w-full resize-y font-sans text-sm"
          value={bodyText}
          onChange={(e) => setBodyText(e.target.value)}
        />
      ) : (
        <p className="whitespace-pre-line text-sm text-ink-muted">{email.body_text}</p>
      )}

      <p className="mt-2 text-xs text-ink-faint">{formatDateTime(email.created_at)}</p>

      {error && <p className="mt-2 text-xs text-priority-critical">{error}</p>}

      {showSendForm && !isSent && (
        <div className="mt-3 flex items-center gap-2 rounded-md border border-border-subtle bg-surface-raised p-2">
          <input
            type="email"
            className="input flex-1"
            placeholder="recipient@example.com"
            value={recipient}
            onChange={(e) => setRecipient(e.target.value)}
          />
          <button onClick={handleSend} disabled={isSending} className="btn-primary text-xs">
            {isSending ? "Sending…" : "Confirm send"}
          </button>
          <button onClick={() => setShowSendForm(false)} className="text-ink-faint hover:text-ink">
            <X size={16} />
          </button>
        </div>
      )}

      <div className="mt-3 flex items-center gap-2">
        {isEditing ? (
          <>
            <button onClick={handleSave} disabled={isSaving} className="btn-primary text-xs">
              {isSaving ? "Saving…" : "Save"}
            </button>
            <button
              onClick={() => {
                setIsEditing(false);
                setSubject(email.subject);
                setBodyText(email.body_text);
              }}
              className="btn-secondary text-xs"
            >
              Cancel
            </button>
          </>
        ) : (
          <>
            {!isSent && (
              <button onClick={() => setIsEditing(true)} className="btn-secondary text-xs">
                <Pencil size={13} />
                Edit
              </button>
            )}
            {!isSent && (
              <button onClick={() => setShowSendForm((s) => !s)} className="btn-primary text-xs">
                <Send size={13} />
                Send
              </button>
            )}
            <button
              onClick={handleDelete}
              disabled={isDeleting}
              className="ml-auto inline-flex items-center gap-1 text-xs text-ink-faint transition-colors hover:text-priority-critical disabled:opacity-50"
            >
              <Trash2 size={13} />
              {isDeleting ? "Deleting…" : "Delete"}
            </button>
          </>
        )}
      </div>
    </div>
  );
}