"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { Mail, Play, ShieldCheck, ShieldAlert } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { BusinessEditForm } from "@/components/BusinessEditForm";
import { ContactChannels } from "@/components/ContactChannels";
import { OutreachEmailCard } from "@/components/OutreachEmailCard";
import { ScoreGauge } from "@/components/ScoreGauge";
import { PriorityBadge } from "@/components/PriorityBadge";
import { api, ApiError } from "@/lib/api";
import type {
  AccessibilityFinding,
  AIReport,
  AuditJob,
  Business,
  LeadScore,
  LighthouseReport,
  OutreachEmail,
  Screenshot,
  SecurityFinding,
  TechnicalFinding,
} from "@/lib/types";

export default function BusinessDetailPage() {
  const params = useParams<{ id: string }>();
  const businessId = params.id;

  const [business, setBusiness] = useState<Business | null>(null);
  const [auditJob, setAuditJob] = useState<AuditJob | null>(null);
  const [leadScore, setLeadScore] = useState<LeadScore | null>(null);
  const [lighthouse, setLighthouse] = useState<LighthouseReport | null>(null);
  const [accessibility, setAccessibility] = useState<AccessibilityFinding | null>(null);
  const [security, setSecurity] = useState<SecurityFinding | null>(null);
  const [technical, setTechnical] = useState<TechnicalFinding | null>(null);
  const [screenshots, setScreenshots] = useState<Screenshot[]>([]);
  const [report, setReport] = useState<AIReport | null>(null);
  const [emails, setEmails] = useState<OutreachEmail[]>([]);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  async function loadBusiness() {
    const b = await api.businesses.get(businessId);
    setBusiness(b);
    const emailList = await api.emails.list(businessId).catch(() => []);
    setEmails(emailList);
    try {
      const score = await api.leads.score(businessId);
      setLeadScore(score);
      await loadAuditDetails(score.audit_job_id);
    } catch {
      // no score yet — no completed audit
    }
  }

  async function loadAuditDetails(auditJobId: string) {
    const job = await api.audits.get(auditJobId);
    setAuditJob(job);
    const [lh, a11y, sec, tech, shots, rep] = await Promise.all([
      api.audits.lighthouse(auditJobId).catch(() => null),
      api.audits.accessibility(auditJobId).catch(() => null),
      api.audits.security(auditJobId).catch(() => null),
      api.audits.technical(auditJobId).catch(() => null),
      api.audits.screenshots(auditJobId).catch(() => []),
      api.audits.report(auditJobId).catch(() => null),
    ]);
    setLighthouse(lh);
    setAccessibility(a11y);
    setSecurity(sec);
    setTechnical(tech);
    setScreenshots(shots);
    setReport(rep);
  }

  useEffect(() => {
    void loadBusiness();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [businessId]);

  async function handleStartAudit() {
    setStatusMessage("Starting audit pipeline…");
    try {
      const { audit_job_id } = await api.audits.start(businessId);
      setStatusMessage("Audit running — this can take a few minutes.");
      pollAudit(audit_job_id);
    } catch (err) {
      setStatusMessage(err instanceof ApiError ? err.message : "Failed to start audit.");
    }
  }

  function pollAudit(auditJobId: string) {
    const interval = setInterval(async () => {
      const job = await api.audits.get(auditJobId);
      setAuditJob(job);
      if (job.status === "completed") {
        clearInterval(interval);
        setStatusMessage("Audit complete.");
        await loadBusiness();
      } else if (job.status === "failed") {
        clearInterval(interval);
        setStatusMessage(`Audit failed at stage "${job.failed_stage}": ${job.error_message}`);
      }
    }, 4000);
  }

  async function handleDraftEmail() {
    setStatusMessage("Drafting outreach email…");
    try {
      const email = await api.emails.draft(businessId);
      setEmails((prev) => [email, ...prev]);
      setStatusMessage("Draft ready — review it below before sending.");
    } catch (err) {
      setStatusMessage(err instanceof ApiError ? err.message : "Failed to draft email.");
    }
  }

  if (!business) {
    return (
      <AppShell>
        <div className="text-ink-muted">Loading…</div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="font-display text-2xl font-semibold text-ink">{business.name}</h1>
          <p className="mt-1 text-sm text-ink-muted">
            {business.category} · {business.city}, {business.country}
          </p>
          {business.website_url && (
            <a href={business.website_url} target="_blank" rel="noreferrer" className="text-sm text-brass hover:text-brass-bright">
              {business.website_url}
            </a>
          )}
          <ContactChannels business={business} draftMessage={emails[0]?.body_text} />
          <BusinessEditForm business={business} onUpdated={setBusiness} />
        </div>
        <div className="flex items-center gap-3">
          {leadScore && (
            <div className="flex items-center gap-3">
              <ScoreGauge score={leadScore.overall_score} size={56} />
              <PriorityBadge priority={leadScore.priority} />
            </div>
          )}
          <button onClick={handleStartAudit} className="btn-primary">
            <Play size={15} />
            {auditJob?.status === "running" ? "Auditing…" : "Run audit"}
          </button>
        </div>
      </div>

      {statusMessage && <div className="mb-6 card px-4 py-3 text-sm text-ink-muted">{statusMessage}</div>}

      {auditJob && auditJob.status !== "completed" && (
        <div className="mb-6 card p-5">
          <h2 className="mb-3 font-display text-sm font-semibold text-ink">Pipeline status: {auditJob.status}</h2>
          <ol className="space-y-2">
            {auditJob.events.map((event, i) => (
              <li key={i} className="flex items-center justify-between text-sm">
                <span className="text-ink-muted">{event.stage}</span>
                <span
                  className={
                    event.status === "failed"
                      ? "text-priority-critical"
                      : event.status === "succeeded"
                        ? "text-priority-low"
                        : "text-ink-muted"
                  }
                >
                  {event.status} {event.duration_ms ? `· ${event.duration_ms}ms` : ""}
                </span>
              </li>
            ))}
          </ol>
        </div>
      )}

      {lighthouse && (
        <div className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
          <MetricCard label="Performance" value={lighthouse.performance_score} />
          <MetricCard label="Accessibility" value={lighthouse.accessibility_score} />
          <MetricCard label="SEO" value={lighthouse.seo_score} />
          <MetricCard label="Best Practices" value={lighthouse.best_practices_score} />
        </div>
      )}

      {screenshots.length > 0 && (
        <div className="mb-6 card p-5">
          <h2 className="mb-3 font-display text-sm font-semibold text-ink">Screenshots</h2>
          <div className="flex flex-wrap gap-4">
            {screenshots.map((shot) => (
              <div key={shot.device} className="text-center">
                <div className="mb-1 h-32 w-24 rounded-md border border-border bg-surface-raised" />
                <span className="text-xs text-ink-faint capitalize">{shot.device}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {security && (
        <div className="mb-6 card p-5">
          <div className="mb-3 flex items-center gap-2">
            {security.https ? (
              <ShieldCheck size={16} className="text-priority-low" />
            ) : (
              <ShieldAlert size={16} className="text-priority-critical" />
            )}
            <h2 className="font-display text-sm font-semibold text-ink">
              Security hygiene — {security.hygiene_score ?? "—"}/100
            </h2>
          </div>
          <div className="grid grid-cols-2 gap-2 text-sm sm:grid-cols-3">
            <FindingRow label="HTTPS" ok={!!security.https} />
            <FindingRow label="HSTS" ok={!!security.hsts} />
            <FindingRow label="CSP configured" ok={!!security.csp} />
            <FindingRow label="No mixed content" ok={!security.mixed_content} />
            <FindingRow label="No directory listing" ok={!security.directory_listing_exposed} />
            <FindingRow label="X-Frame-Options set" ok={!!security.x_frame_options} />
          </div>
        </div>
      )}

      {technical && (
        <div className="mb-6 card p-5">
          <h2 className="mb-3 font-display text-sm font-semibold text-ink">
            Technical & SEO — {technical.technical_score ?? "—"}/100
          </h2>
          {technical.page_load_time_ms !== null && (
            <p className="mb-3 text-sm text-ink-muted">
              Page loaded in <span className="font-mono text-ink">{(technical.page_load_time_ms / 1000).toFixed(1)}s</span>
            </p>
          )}
          <div className="grid grid-cols-2 gap-2 text-sm sm:grid-cols-3">
            <FindingRow label="sitemap.xml present" ok={!!technical.sitemap_present} />
            <FindingRow label="robots.txt present" ok={!!technical.robots_present} />
            <FindingRow label="Favicon present" ok={!!technical.favicon_present} />
            <FindingRow label="Schema markup" ok={!!technical.schema_markup_present} />
            <FindingRow label="OpenGraph tags" ok={!!technical.open_graph_present} />
            <FindingRow label="Twitter Card tags" ok={!!technical.twitter_card_present} />
            <FindingRow label="No broken links" ok={!technical.broken_links_count} />
            <FindingRow label="No oversized images" ok={!technical.oversized_images_count} />
          </div>
          {(technical.broken_links_count ?? 0) > 0 && (
            <p className="mt-3 text-xs text-priority-critical">
              {technical.broken_links_count} broken link{technical.broken_links_count === 1 ? "" : "s"} found
            </p>
          )}
          {(technical.oversized_images_count ?? 0) > 0 && (
            <p className="mt-1 text-xs text-priority-high">
              {technical.oversized_images_count} uncompressed/oversized image{technical.oversized_images_count === 1 ? "" : "s"}
            </p>
          )}
          {technical.google_business_link && (
            <p className="mt-1 text-xs text-ink-muted">Links to Google Business profile ✓</p>
          )}
        </div>
      )}

      {accessibility && (
        <div className="mb-6 card p-5">
          <h2 className="mb-3 font-display text-sm font-semibold text-ink">
            Accessibility — {accessibility.accessibility_score ?? "—"}/100
          </h2>
          <p className="text-sm text-ink-muted">{accessibility.missing_alt_count ?? 0} images missing alt text</p>
        </div>
      )}

      {report && (
        <div className="mb-6 card p-5">
          <h2 className="mb-3 font-display text-sm font-semibold text-ink">Audit report</h2>
          <p className="mb-3 text-sm text-ink">{report.executive_summary}</p>
          {report.top_improvements?.items && report.top_improvements.items.length > 0 && (
            <ul className="space-y-1.5 text-sm text-ink-muted">
              {report.top_improvements.items.map((item, i) => (
                <li key={i}>
                  <span className="font-medium text-ink">{item.title}</span> — {item.detail}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      <div className="card p-5">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="font-display text-sm font-semibold text-ink">Outreach emails</h2>
          <button
            onClick={handleDraftEmail}
            className="btn-secondary text-xs"
            disabled={!report && !!business.website_url}
            title={!report && business.website_url ? "Run an audit first to draft a grounded email" : undefined}
          >
            <Mail size={14} />
            Draft new
          </button>
        </div>
        {emails.length === 0 ? (
          <p className="text-sm text-ink-muted">No drafts yet. Run an audit, then draft an outreach email.</p>
        ) : (
          <div className="space-y-3">
            {emails.map((email) => (
              <OutreachEmailCard
                key={email.id}
                email={email}
                defaultRecipient={business.email}
                onUpdated={(updated) => setEmails((prev) => prev.map((e) => (e.id === updated.id ? updated : e)))}
                onDeleted={(emailId) => setEmails((prev) => prev.filter((e) => e.id !== emailId))}
              />
            ))}
          </div>
        )}
      </div>
    </AppShell>
  );
}

function MetricCard({ label, value }: { label: string; value: number | null }) {
  return (
    <div className="card p-4">
      <div className="label">{label}</div>
      <div className="mt-1 font-mono text-2xl font-semibold text-ink">{value ?? "—"}</div>
    </div>
  );
}

function FindingRow({ label, ok }: { label: string; ok: boolean }) {
  return (
    <div className="flex items-center gap-2">
      <span className={`h-1.5 w-1.5 rounded-full ${ok ? "bg-priority-low" : "bg-priority-critical"}`} />
      <span className="text-ink-muted">{label}</span>
    </div>
  );
}