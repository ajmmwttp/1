"use client";

import * as React from "react";
import { TriangleAlert } from "lucide-react";
import { Button } from "@/components/ui/button";
import { StateShell } from "@/components/states/state-shell";

export interface ErrorStateProps {
  title?: string;
  description?: string;
  error?: Error & { digest?: string };
  onRetry?: () => void;
  className?: string;
}

/**
 * The user never sees a stack trace — only the digest, which is the string
 * support can actually match against a server log line.
 */
export function ErrorState({
  title = "表示できませんでした",
  description = "一時的な問題の可能性があります。再試行してください。",
  error,
  onRetry,
  className,
}: ErrorStateProps) {
  const digest = error?.digest;

  return (
    <StateShell
      icon={TriangleAlert}
      tone="critical"
      title={title}
      description={description}
      className={className}
    >
      <div className="flex flex-col items-center gap-3">
        <div className="flex flex-wrap items-center justify-center gap-2">
          {onRetry ? (
            <Button size="sm" onClick={onRetry}>
              再試行
            </Button>
          ) : null}
          <Button asChild variant="ghost" size="sm">
            <a href="/">ホームへ</a>
          </Button>
        </div>

        {digest ? (
          <p className="tnum text-[11px] leading-none text-[var(--ink-4)]">
            エラーID: {digest}
          </p>
        ) : null}
      </div>
    </StateShell>
  );
}
