"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useRequireAuth } from "@/lib/auth";
import { api } from "@/lib/api";

interface KanbanLead {
  id: string;
  company_name: string;
  score: number;
  tier: string | null;
}

type Board = Record<string, KanbanLead[]>;

const STAGE_ORDER = [
  "discovered", "researching", "qualified", "draft_ready", "approved", "contacted",
  "replied", "demo_booked", "proposal_sent", "won", "lost", "do_not_contact",
];

export default function CampaignsPage() {
  const { user } = useRequireAuth();
  const [board, setBoard] = useState<Board>({});

  useEffect(() => {
    if (user) api.get<Board>("/api/crm/kanban").then(setBoard);
  }, [user]);

  if (!user) return <p className="text-sm text-muted-foreground">Loading...</p>;

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-lg font-semibold">Campaigns — CRM board</h1>
      <div className="flex gap-3 overflow-x-auto pb-4">
        {STAGE_ORDER.map((stage) => (
          <Card key={stage} className="w-64 flex-shrink-0">
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span>{stage.replace(/_/g, " ")}</span>
                <span className="text-xs text-muted-foreground">{board[stage]?.length ?? 0}</span>
              </CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-2">
              {(board[stage] || []).map((lead) => (
                <Link
                  key={lead.id}
                  href={`/leads/${lead.id}`}
                  className="block rounded-md border border-border p-2 text-sm hover:bg-muted"
                >
                  <p className="font-medium">{lead.company_name}</p>
                  <p className="text-xs text-muted-foreground">
                    Score {lead.score} {lead.tier ? `· ${lead.tier}` : ""}
                  </p>
                </Link>
              ))}
              {(!board[stage] || board[stage].length === 0) && <p className="text-xs text-muted-foreground">Empty</p>}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
