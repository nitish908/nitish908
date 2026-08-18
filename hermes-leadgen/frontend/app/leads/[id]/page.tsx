"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/input";
import { TierBadge } from "@/components/ui/badge";
import { useRequireAuth } from "@/lib/auth";
import { api, ApiError } from "@/lib/api";

interface Lead {
  id: string;
  company_name: string;
  website: string | null;
  industry: string | null;
  country: string | null;
  city: string | null;
  description: string | null;
  public_email: string | null;
  contact_page_url: string | null;
  source_name: string | null;
  source_url: string | null;
  score: number;
  tier: string | null;
  stage: string;
  outreach_angle: string | null;
  best_service_package: string | null;
  is_suppressed: boolean;
}

interface Evidence {
  rule_key: string;
  points_awarded: number;
  max_points: number;
  explanation: string;
  source_url: string;
}

interface Finding {
  finding_type: string;
  content: string;
  confidence: string;
  citation_url: string;
}

interface PageFetch {
  url: string;
  page_type: string;
  http_status: string;
  robots_allowed: boolean;
}

interface Note {
  id: string;
  body: string;
  created_at: string;
}

const MESSAGE_TYPES = ["initial_email", "contact_form", "linkedin_draft", "follow_up_1", "follow_up_2", "final_follow_up"];

export default function LeadDetailPage() {
  const params = useParams<{ id: string }>();
  const { user } = useRequireAuth();
  const [lead, setLead] = useState<Lead | null>(null);
  const [evidence, setEvidence] = useState<Evidence[]>([]);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [pages, setPages] = useState<PageFetch[]>([]);
  const [notes, setNotes] = useState<Note[]>([]);
  const [noteBody, setNoteBody] = useState("");
  const [status, setStatus] = useState("");

  async function load() {
    const id = params.id;
    const l = await api.get<Lead>(`/api/leads/${id}`);
    setLead(l);
    setEvidence(await api.get<Evidence[]>(`/api/scoring/leads/${id}/evidence`));
    const research = await api.get<{ findings: Finding[]; pages_fetched: PageFetch[] }>(`/api/leads/${id}/research`);
    setFindings(research.findings);
    setPages(research.pages_fetched);
    setNotes(await api.get<Note[]>(`/api/leads/${id}/notes`));
  }

  useEffect(() => {
    if (user && params.id) load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user, params.id]);

  async function runResearch() {
    setStatus("Researching permitted pages...");
    try {
      const result = await api.post<{ findings_count: number }>(`/api/leads/${params.id}/research`);
      setStatus(`Research complete: ${result.findings_count} finding(s).`);
      load();
    } catch (err) {
      setStatus(err instanceof ApiError ? err.message : "Research failed");
    }
  }

  async function rescore() {
    await api.post(`/api/leads/${params.id}/score`);
    load();
  }

  async function generateDraft(messageType: string) {
    setStatus(`Generating ${messageType} draft...`);
    try {
      await api.post(`/api/outreach/leads/${params.id}/drafts`, { message_type: messageType });
      setStatus(`Draft created and added to the approval queue.`);
    } catch (err) {
      setStatus(err instanceof ApiError ? err.message : "Draft generation failed");
    }
  }

  async function addNote() {
    if (!noteBody.trim()) return;
    await api.post(`/api/leads/${params.id}/notes`, { body: noteBody });
    setNoteBody("");
    load();
  }

  if (!user || !lead) return <p className="text-sm text-muted-foreground">Loading...</p>;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold">{lead.company_name}</h1>
          <p className="text-sm text-muted-foreground">
            {lead.industry || "Unknown industry"} · {[lead.city, lead.country].filter(Boolean).join(", ") || "Unknown location"}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <TierBadge tier={lead.tier} />
          <span className="text-sm font-medium">{lead.score}/100</span>
        </div>
      </div>

      {status && <p className="text-xs text-muted-foreground">{status}</p>}
      {lead.is_suppressed && <p className="text-xs font-medium text-destructive">This lead is suppressed / do-not-contact.</p>}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="flex flex-col gap-4 lg:col-span-2">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>Company facts</CardTitle>
              <div className="flex gap-2">
                <Button size="sm" variant="outline" onClick={runResearch} disabled={!lead.website}>
                  Research website
                </Button>
                <Button size="sm" variant="outline" onClick={rescore}>
                  Re-score
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-1 text-sm">
              <p>
                <span className="text-muted-foreground">Website:</span>{" "}
                {lead.website ? (
                  <a href={lead.website} target="_blank" rel="noreferrer" className="hover:underline">
                    {lead.website}
                  </a>
                ) : (
                  "—"
                )}
              </p>
              <p>
                <span className="text-muted-foreground">Public email:</span> {lead.public_email || "not published"}
              </p>
              <p>
                <span className="text-muted-foreground">Contact page:</span> {lead.contact_page_url || "—"}
              </p>
              <p>
                <span className="text-muted-foreground">Description:</span> {lead.description || "—"}
              </p>
              <p>
                <span className="text-muted-foreground">Source:</span> {lead.source_name || "—"}{" "}
                {lead.source_url && (
                  <a href={lead.source_url} target="_blank" rel="noreferrer" className="hover:underline">
                    ({lead.source_url})
                  </a>
                )}
              </p>
              <p>
                <span className="text-muted-foreground">Stage:</span> {lead.stage}
              </p>
              <p>
                <span className="text-muted-foreground">Suggested package:</span> {lead.best_service_package || "—"}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Score evidence</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2 text-sm">
                {evidence.map((e) => (
                  <li key={e.rule_key} className="flex justify-between gap-4 border-b border-border pb-2 last:border-0">
                    <div>
                      <p className="font-medium">{e.rule_key.replace(/_/g, " ")}</p>
                      <p className="text-muted-foreground">{e.explanation}</p>
                    </div>
                    <span className="whitespace-nowrap font-medium">
                      {e.points_awarded}/{e.max_points}
                    </span>
                  </li>
                ))}
                {evidence.length === 0 && <p className="text-muted-foreground">Not scored yet.</p>}
              </ul>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Research findings</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2 text-sm">
                {findings.map((f, i) => (
                  <li key={i} className="border-b border-border pb-2 last:border-0">
                    <p>
                      <span className="font-medium">{f.finding_type}</span>{" "}
                      <span className={f.confidence === "assumption" ? "text-amber-600" : "text-emerald-600"}>
                        ({f.confidence})
                      </span>
                    </p>
                    <p>{f.content}</p>
                    {f.citation_url && (
                      <a href={f.citation_url} target="_blank" rel="noreferrer" className="text-xs text-muted-foreground hover:underline">
                        Source: {f.citation_url}
                      </a>
                    )}
                  </li>
                ))}
                {findings.length === 0 && <p className="text-muted-foreground">No research yet.</p>}
              </ul>
              {pages.length > 0 && (
                <div className="mt-3 border-t border-border pt-2">
                  <p className="mb-1 text-xs font-medium text-muted-foreground">Pages fetched</p>
                  <ul className="space-y-1 text-xs text-muted-foreground">
                    {pages.map((p, i) => (
                      <li key={i}>
                        {p.url} — {p.http_status || "?"} {p.robots_allowed ? "" : "(blocked by robots.txt)"}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        <div className="flex flex-col gap-4">
          <Card>
            <CardHeader>
              <CardTitle>Generate outreach draft</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-wrap gap-2">
              {MESSAGE_TYPES.map((mt) => (
                <Button key={mt} size="sm" variant="outline" onClick={() => generateDraft(mt)}>
                  {mt.replace(/_/g, " ")}
                </Button>
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Notes</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex gap-2">
                <Textarea value={noteBody} onChange={(e) => setNoteBody(e.target.value)} placeholder="Add a note..." rows={2} />
                <Button size="sm" onClick={addNote}>
                  Add
                </Button>
              </div>
              <ul className="space-y-2 text-sm">
                {notes.map((n) => (
                  <li key={n.id} className="border-b border-border pb-2 last:border-0">
                    {n.body}
                  </li>
                ))}
                {notes.length === 0 && <p className="text-muted-foreground">No notes yet.</p>}
              </ul>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
