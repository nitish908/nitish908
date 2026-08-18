"use client";

import { useEffect, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/input";
import { TierBadge } from "@/components/ui/badge";
import { useRequireAuth } from "@/lib/auth";
import { api, ApiError } from "@/lib/api";

interface QueueItem {
  approval_id: string;
  message_id: string;
  lead_id: string;
  company_name: string;
  score: number;
  tier: string | null;
  message_type: string;
  channel: string;
  status: string;
  subject: string | null;
  body: string;
  cited_company_detail: string;
  scheduled_send_at: string | null;
}

export default function ApprovalQueuePage() {
  const { user } = useRequireAuth();
  const [items, setItems] = useState<QueueItem[]>([]);
  const [statusFilter, setStatusFilter] = useState("pending");
  const [edits, setEdits] = useState<Record<string, string>>({});
  const [message, setMessage] = useState("");

  async function load() {
    const data = await api.get<QueueItem[]>(`/api/outreach/approval-queue?status_filter=${statusFilter}`);
    setItems(data);
  }

  useEffect(() => {
    if (user) load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user, statusFilter]);

  async function saveEdit(item: QueueItem) {
    const body = edits[item.message_id];
    if (body === undefined) return;
    await api.patch(`/api/outreach/messages/${item.message_id}`, { body_edited: body });
    setMessage("Edit saved.");
    load();
  }

  async function approve(item: QueueItem) {
    try {
      await api.post(`/api/outreach/approvals/${item.approval_id}/approve`, {});
      setMessage(`Approved outreach to ${item.company_name}.`);
      load();
    } catch (err) {
      setMessage(err instanceof ApiError ? err.message : "Approve failed");
    }
  }

  async function reject(item: QueueItem, preventFutureContact: boolean) {
    const reason = window.prompt("Reason for rejecting (optional):") || "";
    await api.post(`/api/outreach/approvals/${item.approval_id}/reject`, { reason, prevent_future_contact: preventFutureContact });
    setMessage(`Rejected outreach to ${item.company_name}.`);
    load();
  }

  async function send(item: QueueItem) {
    try {
      await api.post(`/api/outreach/approvals/${item.approval_id}/send`);
      setMessage(`Sent to ${item.company_name}.`);
      load();
    } catch (err) {
      setMessage(err instanceof ApiError ? err.message : "Send failed");
    }
  }

  function exportCsv() {
    window.open(api.downloadUrl(`/api/outreach/export/csv?status_filter=${statusFilter}`), "_blank");
  }

  if (!user) return <p className="text-sm text-muted-foreground">Loading...</p>;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-lg font-semibold">Approval queue</h1>
        <div className="flex gap-2">
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="h-9 rounded-md border border-border px-2 text-sm">
            {["pending", "approved", "scheduled", "sent", "rejected", "all"].map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
          <Button variant="outline" onClick={exportCsv}>
            Export CSV
          </Button>
        </div>
      </div>

      <p className="text-xs text-muted-foreground">
        Nothing is ever sent automatically. Review each draft, verify the cited source, edit if needed, then approve. Sending stays
        disabled until an operator explicitly turns it on in the backend configuration.
      </p>
      {message && <p className="text-xs text-muted-foreground">{message}</p>}

      <div className="flex flex-col gap-3">
        {items.map((item) => (
          <Card key={item.approval_id}>
            <CardContent className="flex flex-col gap-3 p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium">{item.company_name}</p>
                  <p className="text-xs text-muted-foreground">
                    {item.message_type.replace(/_/g, " ")} · {item.channel} · status: {item.status}
                  </p>
                </div>
                <TierBadge tier={item.tier} />
              </div>
              {item.subject && <p className="text-sm font-medium">Subject: {item.subject}</p>}
              <Textarea
                rows={8}
                defaultValue={item.body}
                onChange={(e) => setEdits((prev) => ({ ...prev, [item.message_id]: e.target.value }))}
              />
              <p className="text-xs text-muted-foreground">Cited detail: {item.cited_company_detail || "none"}</p>
              <div className="flex flex-wrap gap-2">
                <Button size="sm" variant="outline" onClick={() => saveEdit(item)}>
                  Save edit
                </Button>
                {item.status === "pending" && (
                  <>
                    <Button size="sm" onClick={() => approve(item)}>
                      Approve
                    </Button>
                    <Button size="sm" variant="destructive" onClick={() => reject(item, false)}>
                      Reject
                    </Button>
                    <Button size="sm" variant="destructive" onClick={() => reject(item, true)}>
                      Reject &amp; do not contact
                    </Button>
                  </>
                )}
                {(item.status === "approved" || item.status === "scheduled") && (
                  <Button size="sm" onClick={() => send(item)}>
                    Send now
                  </Button>
                )}
              </div>
            </CardContent>
          </Card>
        ))}
        {items.length === 0 && <p className="text-sm text-muted-foreground">Nothing in this view.</p>}
      </div>
    </div>
  );
}
