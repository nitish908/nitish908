import { HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

export function Badge({ className, ...props }: HTMLAttributes<HTMLSpanElement>) {
  return (
    <span
      className={cn("inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium bg-muted text-muted-foreground", className)}
      {...props}
    />
  );
}

export function TierBadge({ tier }: { tier: string | null | undefined }) {
  if (!tier) return <Badge>unscored</Badge>;
  const cls = tier === "hot" ? "badge-hot" : tier === "warm" ? "badge-warm" : "badge-cold";
  return <Badge className={cn("rounded-full", cls)}>{tier}</Badge>;
}
