import type { LucideIcon } from "lucide-react";

interface StatCardProps {
  label: string;
  value: string | number;
  icon?: LucideIcon;
  hint?: string;
}

export function StatCard({ label, value, icon: Icon, hint }: StatCardProps) {
  return (
    <div className="card p-5">
      <div className="flex items-start justify-between">
        <span className="label">{label}</span>
        {Icon && <Icon size={16} className="text-brass" />}
      </div>
      <div className="mt-2 font-display text-3xl font-semibold text-ink">{value}</div>
      {hint && <div className="mt-1 text-xs text-ink-muted">{hint}</div>}
    </div>
  );
}
