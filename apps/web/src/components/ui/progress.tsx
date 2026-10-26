import { cn } from "@/lib/utils";

interface ProgressProps {
  /** 0..100. Omit for an indeterminate bar (work with no measurable progress). */
  value?: number;
  label: string;
  className?: string;
}

export function Progress({ value, label, className }: ProgressProps) {
  const indeterminate = value === undefined;
  return (
    <div
      role="progressbar"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={indeterminate ? undefined : Math.round(value)}
      className={cn("bg-muted h-2 w-full overflow-hidden rounded-full", className)}
    >
      <div
        className={cn(
          "bg-primary h-full rounded-full transition-[width]",
          indeterminate && "w-1/3 animate-pulse",
        )}
        style={indeterminate ? undefined : { width: `${Math.min(100, Math.max(0, value))}%` }}
      />
    </div>
  );
}
