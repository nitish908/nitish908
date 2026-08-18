"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useRequireAuth } from "@/lib/auth";
import { api, ApiError } from "@/lib/api";

interface Rule {
  id: string;
  key: string;
  label: string;
  description: string;
  max_points: number;
  is_enabled: boolean;
  hot_threshold: number;
  warm_threshold: number;
}

export default function ScoringPage() {
  const { user } = useRequireAuth();
  const [rules, setRules] = useState<Rule[]>([]);
  const [status, setStatus] = useState("");

  async function load() {
    setRules(await api.get<Rule[]>("/api/scoring/rules"));
  }

  useEffect(() => {
    if (user) load();
  }, [user]);

  async function save(rule: Rule) {
    try {
      await api.patch(`/api/scoring/rules/${rule.id}`, {
        max_points: rule.max_points,
        is_enabled: rule.is_enabled,
        hot_threshold: rule.hot_threshold,
        warm_threshold: rule.warm_threshold,
      });
      setStatus(`Saved "${rule.label}".`);
      load();
    } catch (err) {
      setStatus(err instanceof ApiError ? err.message : "Save failed (owner role required)");
    }
  }

  function updateRule(id: string, patch: Partial<Rule>) {
    setRules((rs) => rs.map((r) => (r.id === id ? { ...r, ...patch } : r)));
  }

  if (!user) return <p className="text-sm text-muted-foreground">Loading...</p>;

  const total = rules.reduce((sum, r) => sum + r.max_points, 0);

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-lg font-semibold">Scoring configuration</h1>
      <p className="text-sm text-muted-foreground">
        Total possible points: <span className="font-medium">{total}</span> (should sum to 100). Owner role required to save changes.
      </p>
      {status && <p className="text-xs text-muted-foreground">{status}</p>}

      <div className="flex flex-col gap-3">
        {rules.map((rule) => (
          <Card key={rule.id}>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span>{rule.label}</span>
                <label className="flex items-center gap-1 text-xs font-normal">
                  <input type="checkbox" checked={rule.is_enabled} onChange={(e) => updateRule(rule.id, { is_enabled: e.target.checked })} />
                  Enabled
                </label>
              </CardTitle>
            </CardHeader>
            <CardContent className="flex flex-wrap items-end gap-3 text-sm">
              <p className="w-full text-muted-foreground">{rule.description}</p>
              <label className="flex flex-col gap-1">
                <span className="text-xs text-muted-foreground">Max points</span>
                <Input type="number" className="w-24" value={rule.max_points} onChange={(e) => updateRule(rule.id, { max_points: Number(e.target.value) })} />
              </label>
              <label className="flex flex-col gap-1">
                <span className="text-xs text-muted-foreground">Hot threshold</span>
                <Input type="number" className="w-24" value={rule.hot_threshold} onChange={(e) => updateRule(rule.id, { hot_threshold: Number(e.target.value) })} />
              </label>
              <label className="flex flex-col gap-1">
                <span className="text-xs text-muted-foreground">Warm threshold</span>
                <Input type="number" className="w-24" value={rule.warm_threshold} onChange={(e) => updateRule(rule.id, { warm_threshold: Number(e.target.value) })} />
              </label>
              <Button size="sm" onClick={() => save(rule)}>
                Save
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
