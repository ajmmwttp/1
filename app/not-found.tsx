import Link from "next/link";
import { FileQuestion } from "lucide-react";
import { EmptyState } from "@/components/states/empty-state";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <Card>
      <EmptyState
        icon={FileQuestion}
        title="ページが見つかりません"
        description="URL が変更されたか、削除された可能性があります。概要ダッシュボードからお探しください。"
      >
        <Button asChild size="sm">
          <Link href="/">概要へ戻る</Link>
        </Button>
      </EmptyState>
    </Card>
  );
}
