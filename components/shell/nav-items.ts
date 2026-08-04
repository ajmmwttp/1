import {
  Box,
  CalendarRange,
  FileText,
  LayoutDashboard,
  PackageSearch,
  Users,
  type LucideIcon,
} from "lucide-react";

export interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
  /** Section header this item sits under in the sidebar. */
  group: "オペレーション" | "管理";
  /**
   * Whether the route is actually mounted in the app. Only "/" exists today, so
   * the other destinations move the active rail client-side instead of routing
   * into a 404. Flip to true when the route ships and the Link navigates for real.
   */
  ready: boolean;
  /** Latin fallbacks so ⌘K works without switching to an IME. */
  keywords: string[];
}

export const NAV_ITEMS: NavItem[] = [
  {
    href: "/",
    label: "概要",
    icon: LayoutDashboard,
    group: "オペレーション",
    ready: true,
    keywords: ["gaiyou", "overview", "dashboard", "summary"],
  },
  {
    href: "/picking",
    label: "ピッキング",
    icon: PackageSearch,
    group: "オペレーション",
    ready: false,
    keywords: ["picking", "pick", "pk"],
  },
  {
    href: "/packing",
    label: "梱包",
    icon: Box,
    group: "オペレーション",
    ready: false,
    keywords: ["konpou", "packing", "pack"],
  },
  {
    href: "/workers",
    label: "担当者",
    icon: Users,
    group: "管理",
    ready: false,
    keywords: ["tantousha", "workers", "staff", "members"],
  },
  {
    href: "/planning",
    label: "要員計画",
    icon: CalendarRange,
    group: "管理",
    ready: false,
    keywords: ["youin", "keikaku", "planning", "roster", "shift"],
  },
  {
    href: "/notes",
    label: "分析ノート",
    icon: FileText,
    group: "管理",
    ready: false,
    keywords: ["bunseki", "note", "analysis", "report"],
  },
];

export const NAV_GROUPS: NavItem["group"][] = ["オペレーション", "管理"];
