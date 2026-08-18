"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useRequireAuth } from "@/lib/auth";
import { api } from "@/lib/api";

interface Overview {
  leads_discovered: number;
  qualified_leads: number;
  drafts_awaiting_approval: number;
  messages_approved: number;
  replies: number;
  positive_replies: number | null;
  meetings_booked: number;
  conversion_rate_percent: number;
  estimated_acquisition_cost: number | null;
  leads_by_industry: Record<string, number>;
  leads_by_source: Record<string, number>;
  leads_by_score_tier: Record<string, number>;
}

interface DailySummary {
  new_leads: number;
  hot_leads: number;
  warm_leads: number;
  drafts_awaiting_approval: number;
  replies_requiring_attention: number;
}

function Metric({ label, value }: { label: string; value: string | number | null }) {
  return (
    <Card>
      <CardContent className="p-4">
        <div className="text-xs text-muted-foreground">{label}</div>
        <div className="mt-1 text-2xl font-semibold">{value ?? "—"}</div>
      </CardContent>
    </Card>
  );
}

function BreakdownCard({ title, data }: { title: string; data: Record<string, number> }) {
  const entries = Object.entries(data || {});
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>
        {entries.length === 0 && <p className="text-xs text-muted-foreground">No data yet.</p>}
        <ul className="space-y-1 text-sm">
          {entries.map(([key, count]) => (
            <li key={key} className="flex justify-between">
              <span>{key}</span>
              <span className="font-medium">{count}</span>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}

export default function OverviewPage() {
  const { user, loading: authLoading } = useRequireAuth();
  const [overview, setOverview] = useState<Overview | null>(null);
  const [daily, setDaily] = useState<DailySummary | null>(null);

  useEffect(() => {
    if (!user) return;
    api.get<Overview>("/api/reports/overview").then(setOverview);
    api.get<DailySummary>("/api/reports/daily-summary").then(setDaily);
  }, [user]);

  if (authLoading || !user) return <p className="text-sm text-muted-foreground">Loading...</p>;

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-lg font-semibold">Overview</h1>
        <p className="text-sm text-muted-foreground">Welcome back, {user.full_name || user.email}.</p>
      </div>

      {daily && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
          <Metric label="New leads (24h)" value={daily.new_leads} />
          <Metric label="Hot (24h)" value={daily.hot_leads} />
          <Metric label="Warm (24h)" value={daily.warm_leads} />
          <Metric label="Drafts awaiting approval" value={daily.drafts_awaiting_approval} />
          <Metric label="Replies needing attention" value={daily.replies_requiring_attention} />
        </div>
      )}

      {overview && (
        <>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Metric label="Leads discovered" value={overview.leads_discovered} />
            <Metric label="Qualified leads" value={overview.qualified_leads} />
            <Metric label="Messages approved" value={overview.messages_approved} />
            <Metric label="Meetings booked" value={overview.meetings_booked} />
            <Metric label="Replies" value={overview.replies} />
            <Metric label="Positive replies" value={overview.positive_replies} />
            <Metric label="Conversion rate" value={`${overview.conversion_rate_percent}%`} />
            <Metric label="Est. acquisition cost" value={overview.estimated_acquisition_cost} />
          </div>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <BreakdownCard title="Leads by industry" data={overview.leads_by_industry} />
            <BreakdownCard title="Leads by source" data={overview.leads_by_source} />
            <BreakdownCard title="Leads by score tier" data={overview.leads_by_score_tier} />
          </div>
        </>
      )}
    </div>
  );
}
