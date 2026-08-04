"use client";

import * as React from "react";
import { usePathname } from "next/navigation";
import { MotionConfig } from "framer-motion";
import { TooltipProvider } from "@/components/ui/tooltip";
import { CommandPalette } from "./command-palette";
import { MobileNav } from "./mobile-nav";
import { Sidebar } from "./sidebar";
import { TopBar } from "./top-bar";

const STORAGE_KEY = "ledger-sidebar";

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [active, setActive] = React.useState(pathname || "/");
  const [collapsed, setCollapsed] = React.useState(false);
  const [restored, setRestored] = React.useState(false);
  const [mobileOpen, setMobileOpen] = React.useState(false);
  const [paletteOpen, setPaletteOpen] = React.useState(false);

  React.useEffect(() => {
    setActive(pathname || "/");
  }, [pathname]);

  // Restore the collapse state after mount — the server has no localStorage,
  // so the first paint is always the expanded rail and the correction lands
  // before `restored` unlocks the transition.
  React.useEffect(() => {
    try {
      if (window.localStorage.getItem(STORAGE_KEY) === "collapsed") {
        setCollapsed(true);
      }
    } catch {
      // storage can be blocked; the default is a fine answer
    }
    const frame = window.requestAnimationFrame(() => setRestored(true));
    return () => window.cancelAnimationFrame(frame);
  }, []);

  React.useEffect(() => {
    if (!restored) return;
    try {
      window.localStorage.setItem(
        STORAGE_KEY,
        collapsed ? "collapsed" : "expanded",
      );
    } catch {
      // ignore
    }
  }, [collapsed, restored]);

  React.useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setPaletteOpen((open) => !open);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  const handleNavigate = React.useCallback((href: string) => {
    setActive(href);
    setMobileOpen(false);
  }, []);

  return (
    <TooltipProvider delayDuration={200}>
      <MotionConfig reducedMotion="user">
        <a
          href="#main"
          className="sr-only focus:not-sr-only focus:fixed focus:left-3 focus:top-3 focus:z-[60] focus:flex focus:h-8 focus:items-center focus:rounded-[8px] focus:border focus:border-[var(--accent-line)] focus:bg-[var(--card)] focus:px-3 focus:text-[12px] focus:font-medium focus:text-[var(--ink)] focus:shadow-[var(--shadow-pop)]"
        >
          本文へスキップ
        </a>

        <div className="flex min-h-dvh w-full">
          <Sidebar
            collapsed={collapsed}
            onToggle={() => setCollapsed((value) => !value)}
            active={active}
            onNavigate={handleNavigate}
            animated={restored}
          />

          <MobileNav
            open={mobileOpen}
            onOpenChange={setMobileOpen}
            active={active}
            onNavigate={handleNavigate}
          />

          <div className="flex min-w-0 flex-1 flex-col">
            <TopBar
              active={active}
              onOpenMobileNav={() => setMobileOpen(true)}
              onOpenPalette={() => setPaletteOpen(true)}
            />
            <main
              id="main"
              tabIndex={-1}
              className="mx-auto w-full max-w-[1440px] flex-1 px-4 py-6 outline-none sm:px-6 lg:px-8"
            >
              {children}
            </main>
          </div>
        </div>

        <CommandPalette
          open={paletteOpen}
          onOpenChange={setPaletteOpen}
          onNavigate={handleNavigate}
        />
      </MotionConfig>
    </TooltipProvider>
  );
}
