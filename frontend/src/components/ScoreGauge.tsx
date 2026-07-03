import { scoreToPriorityColor } from "@/lib/format";

interface ScoreGaugeProps {
  score: number;
  size?: number;
  label?: string;
}

/**
 * Circular gauge rendering a 0-100 opportunity score. This is the
 * dashboard's signature element — it recurs on business cards, the lead
 * board, and the detail view, so the "score" concept always reads the same
 * way at a glance regardless of context.
 */
export function ScoreGauge({ score, size = 64, label }: ScoreGaugeProps) {
  const clamped = Math.max(0, Math.min(100, score));
  const radius = size / 2 - 4;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - clamped / 100);
  const colorClass = scoreToPriorityColor(clamped);

  return (
    <div className="inline-flex flex-col items-center gap-1">
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="-rotate-90">
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke="currentColor"
            strokeWidth={4}
            className="text-border"
          />
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke="currentColor"
            strokeWidth={4}
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="round"
            className={colorClass}
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className={`font-mono font-semibold ${colorClass}`} style={{ fontSize: size * 0.28 }}>
            {Math.round(clamped)}
          </span>
        </div>
      </div>
      {label && <span className="label">{label}</span>}
    </div>
  );
}
