"use client";

import * as React from "react";
import { dataWindow, recordGap } from "@/lib/data/warehouse";
import { shortDate } from "@/lib/format";
import {
  Bell,
  CalendarCheck,
  TrendingDown,
  TriangleAlert,
  type LucideIcon,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

type Tone = "warning" | "serious" | "good";

interface Note {
  id: string;
  icon: LucideIcon;
  tone: Tone;
  title: React.ReactNode;
  /** Colour never travels alone — every tone carries this word and an icon. */
  status: string;
  time: React.ReactNode;
}

const TONE_TEXT: Record<Tone, string> = {
  warning: "text-[color-mix(in_srgb,var(--warning)_78%,var(--ink))]",
  serious: "text-[var(--serious)]",
  good: "text-[var(--good)]",
};

const NOTES: Note[] = [
  {
    id: "gap",
    icon: TriangleAlert,
    tone: "warning",
    status: "要確認",
    title: recordGap ? (
      <>
        <span className="tnum">{shortDate(recordGap.start)}</span>
        以降のPK実働時間が未記録です
      </>
    ) : (
      <>
        PK実働時間は<span className="tnum">{dataWindow.totalDays}</span>日ぶん全て記録されています
      </>
    ),
    time: (
      <>
        <span className="tnum">2</span>時間前
      </>
    ),
  },
  {
    id: "morimoto",
    icon: TrendingDown,
    tone: "serious",
    status: "支援対象",
    title: (
      <>
        森本久美さんの効率が<span className="tnum">2</span>週連続で下限を下回りました
      </>
    ),
    time: <>昨日</>,
  },
  {
    id: "plan",
    icon: CalendarCheck,
    tone: "good",
    status: "確定",
    title: (
      <>
        <span className="tnum">4</span>月の要員計画が確定しました
      </>
    ),
    time: (
      <>
        <span className="tnum">3</span>日前
      </>
    ),
  },
];

export function Notifications() {
  return (
    <DropdownMenu>
      <Tooltip>
        <TooltipTrigger asChild>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              size="icon-sm"
              aria-label={`通知 ${NOTES.length}件`}
              className="relative pointer-coarse:size-10"
            >
              <Bell />
              <span
                aria-hidden
                // Follows the glyph, not the box: the button grows to 40 on
                // touch but the bell stays 14px, so the dot re-centres on it.
                className="absolute right-1 top-1 size-1.5 rounded-full bg-[var(--accent)] ring-2 ring-[var(--page)] pointer-coarse:top-2.5 pointer-coarse:right-2.5"
              />
            </Button>
          </DropdownMenuTrigger>
        </TooltipTrigger>
        <TooltipContent>通知</TooltipContent>
      </Tooltip>

      <DropdownMenuContent align="end" className="w-[336px] p-0">
        <div className="flex items-center justify-between px-1 pt-1">
          <DropdownMenuLabel>通知</DropdownMenuLabel>
          <span className="px-2 text-[12px] text-[var(--ink-4)]">
            <span className="tnum">{NOTES.length}</span>件未読
          </span>
        </div>
        <DropdownMenuSeparator className="mx-0" />
        <div className="p-1">
          {NOTES.map((note) => {
            const Icon = note.icon;
            return (
              <DropdownMenuItem
                key={note.id}
                className="items-start gap-2.5 px-2 py-2"
              >
                <Icon className={`mt-px ${TONE_TEXT[note.tone]}`} />
                <span className="flex min-w-0 flex-col gap-1">
                  <span className="text-[12px] leading-[1.45] text-[var(--ink-2)]">
                    {note.title}
                  </span>
                  <span className="flex items-center gap-1.5 text-[12px] text-[var(--ink-4)]">
                    <span className={TONE_TEXT[note.tone]}>{note.status}</span>
                    <span aria-hidden>·</span>
                    {note.time}
                  </span>
                </span>
              </DropdownMenuItem>
            );
          })}
        </div>
        <DropdownMenuSeparator className="mx-0" />
        <div className="p-1">
          <DropdownMenuItem className="justify-center text-[12px] text-[var(--ink-3)]">
            すべての通知を見る
          </DropdownMenuItem>
        </div>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
