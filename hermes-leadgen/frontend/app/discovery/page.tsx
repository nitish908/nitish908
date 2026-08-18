"use client";

import { ChangeEvent, FormEvent, useState } from "react";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input, Textarea } from "@/components/ui/input";
import { useRequireAuth } from "@/lib/auth";
import { api, ApiError } from "@/lib/api";

const emptyForm = {
  company_name: "", website: "", industry: "", country: "", city: "",
  description: "", public_email: "", contact_page_url: "", estimated_company_size: "",
};

export default function DiscoveryPage() {
  const { user } = useRequireAuth();
  const [form, setForm] = useState(emptyForm);
  const [status, setStatus] = useState("");

  function update<K extends keyof typeof emptyForm>(key: K, value: string) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  async function onImportCsv(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    const data = new FormData();
    data.append("file", file);
    try {
      const result = await api.postForm<{ created: number; duplicates_skipped: number; suppressed_skipped: number; errors: string[] }>(
        "/api/leads/import-csv",
        data
      );
      setStatus(`Imported ${result.created} leads (${result.duplicates_skipped} duplicates, ${result.suppressed_skipped} suppressed skipped).`);
    } catch (err) {
      setStatus(err instanceof ApiError ? err.message : "Import failed");
    } finally {
      e.target.value = "";
    }
  }

  async function onManualSubmit(e: FormEvent) {
    e.preventDefault();
    try {
      await api.post("/api/leads", {
        ...form,
        source_name: "manual_entry",
      });
      setStatus(`Added ${form.company_name}.`);
      setForm(emptyForm);
    } catch (err) {
      setStatus(err instanceof ApiError ? err.message : "Failed to add lead");
    }
  }

  if (!user) return <p className="text-sm text-muted-foreground">Loading...</p>;

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-lg font-semibold">Lead discovery</h1>
      <p className="text-sm text-muted-foreground">
        Bring in leads from a CSV file, manual entry, or a configured{" "}
        <Link href="/sources" className="hover:underline">
          lead source
        </Link>
        . All sources are checked against your suppression list and deduplicated automatically.
      </p>
      {status && <p className="text-xs text-muted-foreground">{status}</p>}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>CSV upload</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <p className="text-sm text-muted-foreground">
              Columns: company_name (required), website, industry, country, city, description, public_email,
              contact_page_url, estimated_company_size, source_url.
            </p>
            <label className="cursor-pointer">
              <span className="inline-flex h-9 items-center rounded-md border border-border px-4 text-sm font-medium hover:bg-muted">
                Choose CSV file
              </span>
              <input type="file" accept=".csv" className="hidden" onChange={onImportCsv} />
            </label>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Manual entry</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={onManualSubmit} className="grid grid-cols-2 gap-2">
              <Input placeholder="Company name *" required value={form.company_name} onChange={(e) => update("company_name", e.target.value)} className="col-span-2" />
              <Input placeholder="Website" value={form.website} onChange={(e) => update("website", e.target.value)} />
              <Input placeholder="Industry" value={form.industry} onChange={(e) => update("industry", e.target.value)} />
              <Input placeholder="Country" value={form.country} onChange={(e) => update("country", e.target.value)} />
              <Input placeholder="City" value={form.city} onChange={(e) => update("city", e.target.value)} />
              <Input placeholder="Public email (only if published)" value={form.public_email} onChange={(e) => update("public_email", e.target.value)} className="col-span-2" />
              <Input placeholder="Contact page URL" value={form.contact_page_url} onChange={(e) => update("contact_page_url", e.target.value)} className="col-span-2" />
              <Input placeholder="Estimated size, e.g. 1-10" value={form.estimated_company_size} onChange={(e) => update("estimated_company_size", e.target.value)} className="col-span-2" />
              <Textarea placeholder="Description" value={form.description} onChange={(e) => update("description", e.target.value)} className="col-span-2" rows={3} />
              <Button type="submit" className="col-span-2">
                Add lead
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
