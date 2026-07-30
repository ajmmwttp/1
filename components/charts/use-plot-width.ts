"use client";

import * as React from "react";

/**
 * Measures the plot box so a chart can thin its own axis instead of letting
 * Recharts overlap labels.
 *
 * Tick density is a function of the pixels available, not of the viewport: the
 * same card is 758px wide at xl and 286px wide on a phone, and at md it is
 * full-bleed while the donut beside it is not. A media query cannot see that.
 *
 * Returns 0 until the first measurement lands — server render and the first
 * client commit agree on 0, and callers treat 0 as "assume the roomy layout"
 * so nothing flashes on desktop.
 */
export function usePlotWidth(): [React.RefObject<HTMLDivElement | null>, number] {
  const ref = React.useRef<HTMLDivElement | null>(null);
  const [width, setWidth] = React.useState(0);

  React.useEffect(() => {
    const node = ref.current;
    if (!node) return;

    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (entry) setWidth(entry.contentRect.width);
    });
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  return [ref, width];
}
