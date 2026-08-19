"use client";

import { FormEvent, useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useRequireAuth } from "@/lib/auth";
import { api, ApiError } from "@/lib/api";

interface Provider {
  source_type: string;
  display_name: string;
  is_configured: boolean;
  requires: string[];
}

interface Source {
  id: string;
  name: string;
  source_type: string;
  is_enabled: boolean;
  config: Record<string, unknown>;
}

export default function SourcesPage() {
  const { user } = useRequireAuth();
  const [providers, setProviders] = useState<Provider[]>([]);
  const [sources, setSources] = useState<Source[]>([]);
  const [org, setOrg] = useState("");
  const [status, setStatus] = useState("");

  async function load() {
    setProviders(await api.get<Provider[]>("/api/sources/providers"));
    setSources(await api.get<Source[]>("/api/sources"));
  }

  useEffect(() => {
    if (user) load();
  }, [user]);

  async function createGithubSource(e: FormEvent) {
    e.preventDefault();
    if (!org.trim()) return;
    const created = await api.post<{ id: string }>("/api/sources", {
      name: `GitHub org: ${org}`,
      source_type: "github_org",
      config: { org },
    });
    setStatus(`Created source for GitHub org "${org}".`);
    setOrg("");
    load();
    return created;
  }

  async function runSource(id: string) {
    setStatus("Running source...");
    try {
      const result = await api.post<{ created: number; duplicates_skipped: number; suppressed_skipped: number }>(`/api/sources/${id}/run`);
      setStatus(`Created ${result.created} lead(s), skipped ${result.duplicates_skipped} duplicate(s) and ${result.suppressed_skipped} suppressed.`);
    } catch (err) {
      setStatus(err instanceof ApiError ? err.message : "Run failed");
    }
  }

  if (!user) return <p className="text-sm text-muted-foreground">Loading...</p>;

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-lg font-semibold">Lead sources</h1>

      <Card>
        <CardHeader>
          <CardTitle>Provider status</CardTitle>
        </CardHeader>
        <CardContent>
          <table className="w-full text-sm">
            <thead className="text-left text-xs text-muted-foreground">
              <tr>
                <th className="py-1">Provider</th>
                <th className="py-1">Status</th>
                <th className="py-1">Requires</th>
              </tr>
            </thead>
            <tbody>
              {providers.map((p) => (
                <tr key={p.source_type} className="border-t border-border">
                  <td className="py-2">{p.display_name}</td>
                  <td className="py-2">
                    {p.is_configured ? (
                      <span className="text-emerald-600">Configured</span>
                    ) : (
                      <span className="text-amber-600">Not configured</span>
                    )}
                  </td>
                  <td className="py-2 text-muted-foreground">{p.requires.join(", ") || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Add a GitHub organization source</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={createGithubSource} className="flex gap-2">
            <Input placeholder="GitHub org login, e.g. acme-inc" value={org} onChange={(e) => setOrg(e.target.value)} />
            <Button type="submit">Add source</Button>
          </form>
        </CardContent>
      </Card>

      {status && <p className="text-xs text-muted-foreground">{status}</p>}

      <Card>
        <CardHeader>
          <CardTitle>Configured sources</CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="space-y-2 text-sm">
            {sources.map((s) => (
              <li key={s.id} className="flex items-center justify-between border-b border-border pb-2 last:border-0">
                <div>
                  <p className="font-medium">{s.name}</p>
                  <p className="text-xs text-muted-foreground">{s.source_type}</p>
                </div>
                <Button size="sm" variant="outline" onClick={() => runSource(s.id)}>
                  Run now
                </Button>
              </li>
            ))}
            {sources.length === 0 && <p className="text-muted-foreground">No sources configured yet.</p>}
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
