import type { LeadPriority } from "./types";

export function formatScore(score: number | null | undefined): string {
  if (score === null || score === undefined) return "—";
  return Math.round(score).toString();
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export const PRIORITY_COLORS: Record<LeadPriority, string> = {
  critical: "text-priority-critical border-priority-critical/40 bg-priority-critical/10",
  high: "text-priority-high border-priority-high/40 bg-priority-high/10",
  medium: "text-priority-medium border-priority-medium/40 bg-priority-medium/10",
  low: "text-priority-low border-priority-low/40 bg-priority-low/10",
};

export const PRIORITY_LABELS: Record<LeadPriority, string> = {
  critical: "Critical",
  high: "High",
  medium: "Medium",
  low: "Low",
};

export function scoreToPriorityColor(score: number): string {
  if (score >= 75) return "text-priority-critical";
  if (score >= 55) return "text-priority-high";
  if (score >= 35) return "text-priority-medium";
  return "text-priority-low";
}
