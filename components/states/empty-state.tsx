import type { ReactNode } from "react";
import { CalendarOff, Inbox, type LucideIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { StateShell } from "@/components/states/state-shell";

/* No "use client" on purpose. lucide-react ships no client boundary, so a
   LucideIcon prop cannot be serialised across a server→client edge. Left
   universal, this renders on the server when a server page passes `icon`,
   and compiles into the client bundle when a client parent passes
   `onAction`. Both callers work; neither throws. */

export interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
  /** Extra actions — use this for links, which `onAction` cannot express. */
  children?: ReactNode;
  className?: string;
}

export function EmptyState({
  icon = Inbox,
  title,
  description,
  actionLabel,
  onAction,
  children,
  className,
}: EmptyStateProps) {
  const hasActions = Boolean(actionLabel) || Boolean(children);

  return (
    <StateShell
      icon={icon}
      title={title}
      description={description}
      className={className}
    >
      {hasActions ? (
        <>
          {actionLabel ? (
            <Button variant="outline" size="sm" onClick={onAction}>
              {actionLabel}
            </Button>
          ) : null}
          {children}
        </>
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
