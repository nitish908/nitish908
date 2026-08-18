"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useRequireAuth } from "@/lib/auth";
import { api } from "@/lib/api";

interface Overview {
  leads_discovered: number;
  qualified_leads: number;
  drafts_awaiting_approval: number;
  messages_approved: number;
  replies: number;
  meetings_booked: number;
  conversion_rate_percent: number;
  leads_by_industry: Record<string, number>;
  leads_by_source: Record<string, number>;
  leads_by_score_tier: Record<string, number>;
}

export default function ReportsPage() {
  const { user } = useRequireAuth();
  const [overview, setOverview] = useState<Overview | null>(null);

  useEffect(() => {
    if (user) api.get<Overview>("/api/reports/overview").then(setOverview);
  }, [user]);

  if (!user || !overview) return <p className="text-sm text-muted-foreground">Loading...</p>;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold">Reports</h1>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => window.open(api.downloadUrl("/api/leads/export/csv"), "_blank")}>
            Export leads CSV
          </Button>
          <Button variant="outline" onClick={() => window.open(api.downloadUrl("/api/outreach/export/csv?status_filter=all"), "_blank")}>
            Export outreach CSV
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Card>
          <CardContent className="p-4">
            <div className="text-xs text-muted-foreground">Leads discovered</div>
            <div className="mt-1 text-2xl font-semibold">{overview.leads_discovered}</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="text-xs text-muted-foreground">Qualified</div>
            <div className="mt-1 text-2xl font-semibold">{overview.qualified_leads}</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="text-xs text-muted-foreground">Approved messages</div>
            <div className="mt-1 text-2xl font-semibold">{overview.messages_approved}</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="text-xs text-muted-foreground">Conversion rate</div>
            <div className="mt-1 text-2xl font-semibold">{overview.conversion_rate_percent}%</div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        {[
          { title: "By industry", data: overview.leads_by_industry },
          { title: "By source", data: overview.leads_by_source },
          { title: "By score tier", data: overview.leads_by_score_tier },
        ].map(({ title, data }) => (
          <Card key={title}>
            <CardHeader>
              <CardTitle>{title}</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="space-y-1 text-sm">
                {Object.entries(data || {}).map(([k, v]) => (
                  <li key={k} className="flex justify-between">
                    <span>{k}</span>
                    <span className="font-medium">{v}</span>
                  </li>
                ))}
                {Object.keys(data || {}).length === 0 && <p className="text-muted-foreground">No data yet.</p>}
              </ul>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
