import { PRIORITY_COLORS, PRIORITY_LABELS } from "@/lib/format";
import type { LeadPriority } from "@/lib/types";

export function PriorityBadge({ priority }: { priority: LeadPriority }) {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${PRIORITY_COLORS[priority]}`}
    >
      {PRIORITY_LABELS[priority]}
    </span>
  );
}
