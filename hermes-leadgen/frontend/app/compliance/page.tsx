"use client";

import { FormEvent, useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useRequireAuth } from "@/lib/auth";
import { api, ApiError } from "@/lib/api";

interface SuppressionEntry {
  id: string;
  value: string;
  value_type: string;
  reason: string;
  added_at: string;
}

interface AuditEntry {
  id: string;
  action: string;
  object_type: string;
  object_id: string;
  detail: string;
  created_at: string;
}

interface Settings {
  lead_data_retention_days: number;
}

export default function CompliancePage() {
  const { user } = useRequireAuth();
  const [suppression, setSuppression] = useState<SuppressionEntry[]>([]);
  const [audit, setAudit] = useState<AuditEntry[]>([]);
  const [settings, setSettings] = useState<Settings | null>(null);
  const [value, setValue] = useState("");
  const [valueType, setValueType] = useState("email");
  const [status, setStatus] = useState("");

  async function load() {
    setSuppression(await api.get<SuppressionEntry[]>("/api/crm/suppression-list"));
    setSettings(await api.get<Settings>("/api/settings"));
    try {
      setAudit(await api.get<AuditEntry[]>("/api/crm/audit-log?limit=100"));
    } catch {
      setAudit([]); // viewer role can't see the audit log; not an error to surface loudly
    }
  }

  useEffect(() => {
    if (user) load();
  }, [user]);

  async function addSuppression(e: FormEvent) {
    e.preventDefault();
    if (!value.trim()) return;
    try {
      await api.post("/api/crm/suppression-list", { value, value_type: valueType, reason: "manually added" });
      setStatus(`Added ${value} to the suppression list.`);
      setValue("");
      load();
    } catch (err) {
      setStatus(err instanceof ApiError ? err.message : "Failed to add");
    }
  }

  if (!user) return <p className="text-sm text-muted-foreground">Loading...</p>;

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-lg font-semibold">Compliance &amp; suppression list</h1>

      <Card>
        <CardContent className="p-4 text-sm text-muted-foreground">
          <p className="font-medium text-foreground">This platform does not guarantee legal compliance.</p>
          <p className="mt-1">
            Anti-spam and privacy rules (CAN-SPAM, GDPR, PECR, India&apos;s DPDP Act, and others) vary by where your
            recipients are located and how you use this tool. Get advice from a qualified lawyer for your target
            market before sending outreach at scale. See <span className="font-mono text-xs">docs/COMPLIANCE_CHECKLIST.md</span> for
            the operator checklist that ships with this repo.
          </p>
          {settings && <p className="mt-2">Configured lead-data retention period: {settings.lead_data_retention_days} days.</p>}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Suppression list</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <form onSubmit={addSuppression} className="flex flex-wrap gap-2">
            <Input placeholder="Email or domain" value={value} onChange={(e) => setValue(e.target.value)} className="max-w-xs" />
            <select value={valueType} onChange={(e) => setValueType(e.target.value)} className="h-9 rounded-md border border-border px-2 text-sm">
              <option value="email">email</option>
              <option value="domain">domain</option>
            </select>
            <Button type="submit">Add</Button>
          </form>
          {status && <p className="text-xs text-muted-foreground">{status}</p>}
          <ul className="space-y-1 text-sm">
            {suppression.map((s) => (
              <li key={s.id} className="flex justify-between border-b border-border pb-1 last:border-0">
                <span>
                  {s.value} <span className="text-xs text-muted-foreground">({s.value_type})</span>
                </span>
                <span className="text-xs text-muted-foreground">{s.reason}</span>
              </li>
            ))}
            {suppression.length === 0 && <p className="text-muted-foreground">No suppressed contacts yet.</p>}
          </ul>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Audit log (owner only)</CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="max-h-96 space-y-1 overflow-y-auto text-xs">
            {audit.map((a) => (
              <li key={a.id} className="flex justify-between border-b border-border py-1 last:border-0">
                <span>
                  {a.action} {a.object_type ? `(${a.object_type})` : ""} {a.detail}
                </span>
                <span className="whitespace-nowrap text-muted-foreground">{a.created_at}</span>
              </li>
            ))}
            {audit.length === 0 && <p className="text-muted-foreground">No entries visible.</p>}
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
