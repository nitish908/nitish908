"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";

const LINKS = [
  { href: "/overview", label: "Overview" },
  { href: "/discovery", label: "Lead discovery" },
  { href: "/leads", label: "Leads" },
  { href: "/approval-queue", label: "Approval queue" },
  { href: "/campaigns", label: "Campaigns" },
  { href: "/follow-ups", label: "Follow-ups" },
  { href: "/reports", label: "Reports" },
  { href: "/sources", label: "Lead sources" },
  { href: "/templates", label: "Message templates" },
  { href: "/scoring", label: "Scoring config" },
  { href: "/compliance", label: "Compliance" },
  { href: "/settings", label: "Settings" },
];

export function NavBar() {
  const pathname = usePathname();
  const router = useRouter();

  async function logout() {
    try {
      await api.post("/api/auth/logout");
    } finally {
      router.replace("/login");
    }
  }

  if (pathname === "/login") return null;

  return (
    <div className="border-b border-border bg-card">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-2">
        <div className="text-sm font-semibold">Hermes Lead-Gen</div>
        <button onClick={logout} className="text-xs text-muted-foreground hover:underline">
          Log out
        </button>
      </div>
      <nav className="mx-auto flex max-w-7xl flex-wrap gap-1 px-4 pb-2">
        {LINKS.map((link) => (
          <Link
            key={link.href}
            href={link.href}
            className={cn(
              "rounded-md px-2.5 py-1 text-xs font-medium text-muted-foreground hover:bg-muted",
              pathname?.startsWith(link.href) && "bg-muted text-foreground"
            )}
          >
            {link.label}
          </Link>
        ))}
      </nav>
    </div>
  );
}
