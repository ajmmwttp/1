"use client";

import * as React from "react";
import { motion, useReducedMotion } from "framer-motion";

import { REVEAL_DURATION, REVEAL_EASE, revealDelay } from "./ladder";

/* ──────────────────────────────────────────────────────────────
   Reveal — the one entrance in the console.

   opacity 0→1 + translateY 8px→0, 320ms on the expo-out curve that
   --ease-out-expo already uses for every other transition here.

   The page is a server component, so there is no parent orchestrator:
   each section owns its own step on a shared ladder and reveals itself.
   Steps are hard-coded at the call site (see REVEAL_STEPS in ./ladder)
   rather than discovered through context — a dashboard has a fixed
   reading order, and a context would only make that order harder to
   read in the source.

   Runs once, on mount. Never on scroll: `initial`/`animate` fire on the
   first commit and nothing re-triggers them, so scrolling back up never
   replays the page.

   REDUCED MOTION — two independent guards, because this is the one thing
   that must not depend on a single mechanism working:
     1. `useReducedMotion()` here collapses the transition to 0s, so the
        element is at its final state on the first animation frame.
        No translate, no fade — just present.
     2. `MotionConfig reducedMotion="user"` in app-shell strips transform
        animations from every descendant regardless of what we pass.
   `initial` stays identical in both branches so the server HTML and the
   first client render agree on the markup.
   ────────────────────────────────────────────────────────────── */

export interface RevealProps {
  /** Position on the shared ladder. See REVEAL_STEPS. */
  step: number;
  className?: string;
  children: React.ReactNode;
}

export function Reveal({ step, className, children }: RevealProps) {
  const reduceMotion = useReducedMotion();

  return (
    <motion.div
      // Makes the ladder inspectable — in devtools, and in the harness that
      // measures the choreography rather than trusting it.
      data-reveal={step}
      className={className}
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={
        reduceMotion
          ? { duration: 0 }
          : {
              duration: REVEAL_DURATION,
              delay: revealDelay(step),
              ease: REVEAL_EASE,
            }
      }
    >
      {children}
    </motion.div>
  );
}
