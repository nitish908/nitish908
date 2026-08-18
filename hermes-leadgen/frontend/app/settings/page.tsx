"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useRequireAuth } from "@/lib/auth";
import { api } from "@/lib/api";

interface Settings {
  app_env: string;
  outreach_live_send_enabled: boolean;
  ai_provider_configured: boolean;
  openai_model: string | null;
  sender_name: string;
  sender_company: string;
  sender_contact_email: string;
  lead_data_retention_days: number;
  daily_discovery_lead_limit: number;
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex justify-between border-b border-border py-2 text-sm last:border-0">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium">{value}</span>
    </div>
  );
}

export default function SettingsPage() {
  const { user } = useRequireAuth();
  const [settings, setSettings] = useState<Settings | null>(null);

  useEffect(() => {
    if (user) api.get<Settings>("/api/settings").then(setSettings);
  }, [user]);

  if (!user || !settings) return <p className="text-sm text-muted-foreground">Loading...</p>;

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-lg font-semibold">Settings</h1>
      <p className="text-sm text-muted-foreground">
        Read-only: these values come from the backend&apos;s environment configuration (see{" "}
        <span className="font-mono text-xs">.env.example</span>) and are never exposed to the frontend if secret.
      </p>

      <Card>
        <CardHeader>
          <CardTitle>Account</CardTitle>
        </CardHeader>
        <CardContent>
          <Row label="Signed in as" value={user.email} />
          <Row label="Role" value={user.role} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Sending &amp; providers</CardTitle>
        </CardHeader>
        <CardContent>
          <Row label="Environment" value={settings.app_env} />
          <Row label="Live outreach sending" value={settings.outreach_live_send_enabled ? "Enabled" : "Disabled (draft + CSV export only)"} />
          <Row label="AI provider configured" value={settings.ai_provider_configured ? `Yes (${settings.openai_model})` : "No — rule-based fallback in use"} />
          <Row label="Sender name" value={settings.sender_name || "(not set)"} />
          <Row label="Sender company" value={settings.sender_company} />
          <Row label="Sender contact email" value={settings.sender_contact_email || "(not set)"} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Workflow</CardTitle>
        </CardHeader>
        <CardContent>
          <Row label="Lead data retention" value={`${settings.lead_data_retention_days} days`} />
          <Row label="Daily discovery lead limit" value={settings.daily_discovery_lead_limit} />
        </CardContent>
      </Card>
    </div>
  );
}
