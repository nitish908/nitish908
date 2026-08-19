"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useRequireAuth } from "@/lib/auth";
import { api } from "@/lib/api";

interface FollowUp {
  id: string;
  company_name: string;
  next_follow_up_at: string;
  stage: string;
}

interface Task {
  id: string;
  lead_id: string;
  title: string;
  due_date: string | null;
  status: string;
}

export default function FollowUpsPage() {
  const { user } = useRequireAuth();
  const [followUps, setFollowUps] = useState<FollowUp[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);

  useEffect(() => {
    if (!user) return;
    api.get<FollowUp[]>("/api/crm/follow-ups-due").then(setFollowUps);
    api.get<Task[]>("/api/crm/tasks").then(setTasks);
  }, [user]);

  if (!user) return <p className="text-sm text-muted-foreground">Loading...</p>;

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-lg font-semibold">Follow-ups</h1>
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Follow-ups due</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2 text-sm">
              {followUps.map((f) => (
                <li key={f.id} className="flex justify-between border-b border-border pb-2 last:border-0">
                  <Link href={`/leads/${f.id}`} className="hover:underline">
                    {f.company_name}
                  </Link>
                  <span className="text-muted-foreground">{f.next_follow_up_at}</span>
                </li>
              ))}
              {followUps.length === 0 && <p className="text-muted-foreground">Nothing due.</p>}
            </ul>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Open tasks</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2 text-sm">
              {tasks.map((t) => (
                <li key={t.id} className="flex justify-between border-b border-border pb-2 last:border-0">
                  <Link href={`/leads/${t.lead_id}`} className="hover:underline">
                    {t.title}
                  </Link>
                  <span className="text-muted-foreground">{t.due_date || "no due date"}</span>
                </li>
              ))}
              {tasks.length === 0 && <p className="text-muted-foreground">No open tasks.</p>}
            </ul>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
