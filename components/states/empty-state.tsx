"use client";

import * as React from "react";
import { CalendarOff, Inbox, type LucideIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { StateShell } from "@/components/states/state-shell";

export interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
  className?: string;
}

export function EmptyState({
  icon = Inbox,
  title,
  description,
  actionLabel,
  onAction,
  className,
}: EmptyStateProps) {
  return (
    <StateShell
      icon={icon}
      title={title}
      description={description}
      className={className}
    >
      {actionLabel ? (
        <Button variant="outline" size="sm" onClick={onAction}>
          {actionLabel}
        </Button>
      ) : null}
    </StateShell>
  );
}

export type NoRecordsEmptyProps = Omit<
  EmptyStateProps,
  "icon" | "title" | "description"
> &
  Partial<Pick<EmptyStateProps, "title" | "description">>;

/**
 * 記録が 0 日の担当者・期間はランキングにも平均にも入らないので、
 * 「データが無い」ではなく「対象から外れている」と伝える。
 */
export function NoRecordsEmpty({
  title = "この期間の記録がありません",
  description = "記録日数が0日の担当者は評価対象から外れます。",
  ...props
}: NoRecordsEmptyProps) {
  return (
    <EmptyState
      icon={CalendarOff}
      title={title}
      description={description}
      {...props}
    />
  );
}
