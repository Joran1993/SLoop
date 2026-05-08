import { cn } from "@/lib/utils";

interface ScoreBadgeProps {
  score: number | null;
  className?: string;
}

export function ScoreBadge({ score, className }: ScoreBadgeProps) {
  if (score == null) {
    return (
      <span
        className={cn(
          "inline-flex items-center rounded px-1.5 py-0.5 text-xs font-medium bg-muted text-muted-foreground tabular-nums",
          className
        )}
      >
        —
      </span>
    );
  }

  const tier =
    score >= 70 ? "high" : score >= 40 ? "mid" : "low";

  return (
    <span
      className={cn(
        "inline-flex items-center rounded px-1.5 py-0.5 text-xs font-medium tabular-nums",
        tier === "high" && "bg-emerald-100 text-emerald-800",
        tier === "mid" && "bg-amber-100 text-amber-800",
        tier === "low" && "bg-red-100 text-red-800",
        className
      )}
    >
      {Math.round(score)}
    </span>
  );
}
