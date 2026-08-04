"use client";

import { useEffect } from "react";
import { ErrorState } from "@/components/states/error-state";
import { Card } from "@/components/ui/card";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // In production this is where the report goes to the error tracker.
    console.error(error);
  }, [error]);

  return (
    <Card>
      <ErrorState
        title="ダッシュボードを表示できませんでした"
        description="集計データの読み込みに失敗しました。一時的な問題の可能性があります。再試行しても直らない場合は、エラーIDを添えて情報システム課へご連絡ください。"
        error={error}
        onRetry={reset}
      />
    </Card>
  );
}
