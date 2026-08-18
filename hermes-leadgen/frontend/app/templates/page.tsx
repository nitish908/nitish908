"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useRequireAuth } from "@/lib/auth";

const TEMPLATES = [
  { type: "initial_email", label: "Initial email", channel: "email", note: "First outreach. Includes a cited company detail, one problem, one use case, and an opt-out line." },
  { type: "contact_form", label: "Contact-form message", channel: "contact form", note: "Shorter version for submitting through a company's own contact form." },
  { type: "linkedin_draft", label: "LinkedIn draft", channel: "manual use only", note: "Never sent automatically — always copy/pasted by a human, since LinkedIn has no send API here." },
  { type: "follow_up_1", label: "Follow-up 1", channel: "email", note: "Gentle first follow-up referencing the earlier note." },
  { type: "follow_up_2", label: "Follow-up 2", channel: "email", note: "Second follow-up, offers to close out if not interested." },
  { type: "final_follow_up", label: "Final follow-up", channel: "email", note: "Explicit last message; states no further contact will follow." },
];

export default function TemplatesPage() {
  const { user } = useRequireAuth();
  if (!user) return <p className="text-sm text-muted-foreground">Loading...</p>;

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-lg font-semibold">Message templates</h1>
      <p className="text-sm text-muted-foreground">
        The MVP composes every draft from these six system templates using only verified lead/research fields — no
        AI paraphrasing of facts, so nothing can drift from what was actually verified. Templates are generated
        per-lead from <span className="font-mono text-xs">app/services/outreach/templates.py</span> on the backend;
        a dashboard-editable template library is on the roadmap (see docs/ROADMAP.md).
      </p>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {TEMPLATES.map((t) => (
          <Card key={t.type}>
            <CardHeader>
              <CardTitle>{t.label}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-1 text-sm">
              <p className="text-muted-foreground">Channel: {t.channel}</p>
              <p>{t.note}</p>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
