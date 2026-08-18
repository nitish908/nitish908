"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";

export interface CurrentUser {
  id: string;
  email: string;
  full_name: string;
  role: "owner" | "viewer" | string;
}

export function useRequireAuth(): { user: CurrentUser | null; loading: boolean } {
  const router = useRouter();
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    api
      .get<CurrentUser>("/api/auth/me")
      .then((u) => {
        if (!cancelled) setUser(u);
      })
      .catch((err) => {
        if (cancelled) return;
        if (err instanceof ApiError && err.status === 401) {
          router.replace("/login");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [router]);

  return { user, loading };
}
