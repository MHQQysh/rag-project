"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";

export function DemoLogin() {
  const [enabled, setEnabled] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    void fetch("/api/v1/auth/demo-status", {
      cache: "no-store",
      signal: controller.signal,
    })
      .then(async (response) => {
        if (response.ok) {
          const data = (await response.json()) as { enabled?: boolean };
          setEnabled(data.enabled === true);
        }
      })
      .catch(() => undefined);
    return () => controller.abort();
  }, []);

  if (!enabled) return null;

  async function enterDemo() {
    setLoading(true);
    setError("");
    try {
      const response = await fetch("/api/v1/auth/login/demo", {
        method: "POST",
        credentials: "include",
      });
      if (!response.ok) throw new Error("Demo unavailable");
      // Reload the auth provider from the new HttpOnly session cookie.
      window.location.assign("/workspace/chats/new");
    } catch {
      setError("暂时无法进入演示，请稍后重试。");
      setLoading(false);
    }
  }

  return (
    <div className="space-y-3 rounded-xl border p-4">
      <Button className="w-full" disabled={loading} onClick={enterDemo}>
        {loading ? "正在进入…" : "进入演示"}
      </Button>
      <p className="text-muted-foreground text-center text-xs">
        无需注册。演示对话和文件由访客共享，请勿上传私人资料。
      </p>
      {error && (
        <p role="alert" className="text-sm text-red-500">
          {error}
        </p>
      )}
    </div>
  );
}
