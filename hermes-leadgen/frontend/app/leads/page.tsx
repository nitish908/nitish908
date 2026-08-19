"use client";

import { ChangeEvent, useEffect, useState } from "react";
import Link from "next/link";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { TierBadge } from "@/components/ui/badge";
import { useRequireAuth } from "@/lib/auth";
import { api, ApiError } from "@/lib/api";

interface Lead {
  id: string;
  company_name: string;
  industry: string | null;
  country: string | null;
  score: number;
  tier: string | null;
  stage: string;
  source_name: string | null;
}

export default function LeadsPage() {
  const { user } = useRequireAuth();
  const [leads, setLeads] = useState<Lead[]>([]);
  const [q, setQ] = useState("");
  const [stage, setStage] = useState("");
  const [tier, setTier] = useState("");
  const [status, setStatus] = useState<string>("");

  async function load() {
    const params = new URLSearchParams();
    if (q) params.set("q", q);
    if (stage) params.set("stage", stage);
    if (tier) params.set("tier", tier);
    const data = await api.get<Lead[]>(`/api/leads?${params.toString()}`);
    setLeads(data);
  }

  useEffect(() => {
    if (user) load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user, q, stage, tier]);

  async function onImportCsv(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    const form = new FormData();
    form.append("file", file);
    try {
      const result = await api.postForm<{ created: number; duplicates_skipped: number; suppressed_skipped: number; errors: string[] }>(
        "/api/leads/import-csv",
        form
      );
      setStatus(
        `Imported ${result.created} leads (${result.duplicates_skipped} duplicates skipped, ${result.suppressed_skipped} suppressed skipped).` +
          (result.errors.length ? ` ${result.errors.length} row error(s).` : "")
      );
      load();
    } catch (err) {
      setStatus(err instanceof ApiError ? err.message : "Import failed");
    } finally {
      e.target.value = "";
    }
  }

  function exportCsv() {
    window.open(api.downloadUrl("/api/leads/export/csv"), "_blank");
  }

  async function rescore(id: string) {
    await api.post(`/api/leads/${id}/score`);
    load();
  }

  if (!user) return <p className="text-sm text-muted-foreground">Loading...</p>;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-lg font-semibold">Leads</h1>
        <div className="flex flex-wrap gap-2">
          <label className="cursor-pointer">
            <span className="inline-flex h-9 items-center rounded-md border border-border px-4 text-sm font-medium hover:bg-muted">
              Import CSV
            </span>
            <input type="file" accept=".csv" className="hidden" onChange={onImportCsv} />
          </label>
          <Button variant="outline" onClick={exportCsv}>
            Export CSV
          </Button>
        </div>
      </div>

      {status && <p className="text-xs text-muted-foreground">{status}</p>}

      <div className="flex flex-wrap gap-2">
        <Input placeholder="Search company..." value={q} onChange={(e) => setQ(e.target.value)} className="max-w-xs" />
        <select value={stage} onChange={(e) => setStage(e.target.value)} className="h-9 rounded-md border border-border px-2 text-sm">
          <option value="">All stages</option>
          {["discovered", "researching", "qualified", "draft_ready", "approved", "contacted", "replied", "demo_booked", "proposal_sent", "won", "lost", "do_not_contact"].map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
        <select value={tier} onChange={(e) => setTier(e.target.value)} className="h-9 rounded-md border border-border px-2 text-sm">
          <option value="">All tiers</option>
          <option value="hot">Hot</option>
          <option value="warm">Warm</option>
          <option value="cold">Cold</option>
        </select>
      </div>

      <Card>
        <CardContent className="p-0">
          <table className="w-full text-sm">
            <thead className="border-b border-border bg-muted/50 text-left text-xs text-muted-foreground">
              <tr>
                <th className="px-3 py-2">Company</th>
                <th className="px-3 py-2">Industry</th>
                <th className="px-3 py-2">Country</th>
                <th className="px-3 py-2">Score</th>
                <th className="px-3 py-2">Tier</th>
                <th className="px-3 py-2">Stage</th>
                <th className="px-3 py-2">Source</th>
                <th className="px-3 py-2"></th>
              </tr>
            </thead>
            <tbody>
              {leads.map((lead) => (
                <tr key={lead.id} className="border-b border-border last:border-0 hover:bg-muted/30">
                  <td className="px-3 py-2 font-medium">
                    <Link href={`/leads/${lead.id}`} className="hover:underline">
                      {lead.company_name}
                    </Link>
                  </td>
                  <td className="px-3 py-2 text-muted-foreground">{lead.industry || "—"}</td>
                  <td className="px-3 py-2 text-muted-foreground">{lead.country || "—"}</td>
                  <td className="px-3 py-2">{lead.score}</td>
                  <td className="px-3 py-2">
                    <TierBadge tier={lead.tier} />
                  </td>
                  <td className="px-3 py-2 text-muted-foreground">{lead.stage}</td>
                  <td className="px-3 py-2 text-muted-foreground">{lead.source_name || "—"}</td>
                  <td className="px-3 py-2">
                    <Button size="sm" variant="outline" onClick={() => rescore(lead.id)}>
                      Score
                    </Button>
                  </td>
                </tr>
              ))}
              {leads.length === 0 && (
                <tr>
                  <td colSpan={8} className="px-3 py-6 text-center text-muted-foreground">
                    No leads yet. Import a CSV or add one manually.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </CardContent>
      </Card>
    </div>
  );
}
