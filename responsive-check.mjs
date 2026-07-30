/**
 * responsive-check.mjs — breakpoint audit for the Ledger dashboard.
 *
 * Loads the page at every width we care about and asserts the DOCUMENT never
 * scrolls horizontally. Also reports, per width, which elements are wider than
 * their own scroll container (the usual culprit) and a handful of layout facts
 * that are easy to regress: KPI columns, chart heights, sticky table column.
 *
 * The bundled Chromium download is absent in this environment, so the binary is
 * passed explicitly. Override with CHROME=… if it ever moves.
 *
 *   node responsive-check.mjs                    # audit against BASE
 *   BASE=http://127.0.0.1:3210 node responsive-check.mjs
 *   SHOTS=1 node responsive-check.mjs            # also write full-page PNGs
 */
import { chromium } from "playwright";
import { mkdir } from "node:fs/promises";

const BASE = process.env.BASE ?? "http://127.0.0.1:3210";
const CHROME =
  process.env.CHROME ?? "/opt/pw-browsers/chromium-1194/chrome-linux/chrome";
const SHOT_DIR = process.env.SHOT_DIR ?? "/tmp/responsive-check";
const WANT_SHOTS = process.env.SHOTS === "1";

/** coarse: emulate a touch pointer so `pointer-coarse:` rules apply. */
const WIDTHS = [
  { w: 360, h: 800, coarse: true },
  { w: 390, h: 844, coarse: true },
  { w: 640, h: 900, coarse: true },
  { w: 768, h: 1024, coarse: true },
  { w: 1024, h: 900, coarse: false },
  { w: 1280, h: 900, coarse: false },
  { w: 1512, h: 950, coarse: false },
  { w: 1920, h: 1080, coarse: false },
];

/** Anything interactive must clear this in its smallest dimension on touch. */
const TOUCH_MIN = 40;

const failures = [];
const rows = [];

if (WANT_SHOTS) await mkdir(SHOT_DIR, { recursive: true });

const browser = await chromium.launch({ executablePath: CHROME });

for (const { w, h, coarse } of WIDTHS) {
  const ctx = await browser.newContext({
    viewport: { width: w, height: h },
    deviceScaleFactor: 1,
    colorScheme: "dark",
    hasTouch: coarse,
    isMobile: false, // keep layout viewport === visual viewport, no page zoom
  });
  const page = await ctx.newPage();
  page.on("pageerror", (e) => failures.push(`${w}px pageerror: ${e.message}`));
  page.on("console", (m) => {
    if (m.type() === "error") failures.push(`${w}px console: ${m.text()}`);
  });

  const res = await page.goto(BASE, { waitUntil: "load", timeout: 60000 });
  if (!res || !res.ok()) failures.push(`${w}px HTTP ${res?.status()}`);
  // Recharts draws its axes only after ResponsiveContainer has measured, and
  // the reveal ladder staggers the cards in — wait for the last axis, then let
  // the entrance settle before taking any geometry.
  await page
    .waitForFunction(
      () => document.querySelectorAll(".recharts-cartesian-axis-tick-value").length > 20,
      null,
      { timeout: 60000 },
    )
    .catch(() => failures.push(`${w}px: charts never finished drawing`));
  await page.waitForTimeout(2000);

  const report = await page.evaluate(
    ({ TOUCH_MIN, coarse }) => {
      const de = document.documentElement;
      const overflow = de.scrollWidth - de.clientWidth;

      /* Which elements actually stick out past the viewport? Ignore anything
         living inside a legitimately scrollable ancestor — that is by design. */
      const scrollableAncestor = (el) => {
        for (let n = el.parentElement; n; n = n.parentElement) {
          const s = getComputedStyle(n);
          if (
            (s.overflowX === "auto" || s.overflowX === "scroll") &&
            n.scrollWidth > n.clientWidth + 1
          ) {
            return n;
          }
        }
        return null;
      };
      const culprits = [];
      if (overflow > 1) {
        for (const el of document.querySelectorAll("body *")) {
          const r = el.getBoundingClientRect();
          if (r.width === 0 && r.height === 0) continue;
          if (r.right <= de.clientWidth + 1 && r.left >= -1) continue;
          if (scrollableAncestor(el)) continue;
          culprits.push(
            `${el.tagName.toLowerCase()}.${String(el.className).slice(0, 60)} ` +
              `[${Math.round(r.left)}…${Math.round(r.right)}]`,
          );
          if (culprits.length >= 6) break;
        }
      }

      /* Touch targets. Only real controls, only when visible. */
      const small = [];
      if (coarse) {
        const sel = 'a[href], button, input, [role="button"], [tabindex="0"]';
        for (const el of document.querySelectorAll(sel)) {
          if (el.closest("[hidden]") || el.hasAttribute("disabled")) continue;
          if (el.closest(".sr-only") || el.classList.contains("sr-only")) continue;
          const s = getComputedStyle(el);
          if (s.display === "none" || s.visibility === "hidden") continue;
          const r = el.getBoundingClientRect();
          if (r.width === 0 || r.height === 0) continue;
          // tr rows are big surfaces, not tap chips
          if (el.tagName === "TR") continue;
          const min = Math.min(r.width, r.height);
          if (min < TOUCH_MIN - 0.5) {
            small.push(
              `${el.tagName.toLowerCase()}"${(el.getAttribute("aria-label") || el.textContent || "").trim().slice(0, 14)}" ${Math.round(r.width)}×${Math.round(r.height)}`,
            );
          }
        }
      }

      /* Layout facts worth pinning. */
      const kpiGrid = document.querySelector('[aria-label="主要指標"] .grid');
      const kpiCols = kpiGrid
        ? getComputedStyle(kpiGrid).gridTemplateColumns.split(" ").length
        : 0;

      const heightOf = (label) => {
        const card = [...document.querySelectorAll("h3")].find((n) =>
          n.textContent?.includes(label),
        );
        const plot = card
          ?.closest("div.relative, div[class*='rounded-[12px]']")
          ?.querySelector(".recharts-wrapper");
        return plot ? Math.round(plot.getBoundingClientRect().height) : null;
      };

      const scroller = document.querySelector(
        '[aria-label="担当者ランキング"] [class*="overflow-auto"]',
      );
      const table = scroller?.querySelector("table");
      const firstBodyCell = table?.querySelector("tbody tr td");
      const nameCell = firstBodyCell?.nextElementSibling;
      const sticky = firstBodyCell
        ? getComputedStyle(firstBodyCell).position === "sticky" &&
          getComputedStyle(nameCell).position === "sticky"
        : false;

      /* Do the two sticky cells tile exactly? (offset === rank width) */
      let stickySeam = null;
      if (sticky && firstBodyCell && nameCell) {
        const gap =
          parseFloat(getComputedStyle(nameCell).left) -
          firstBodyCell.getBoundingClientRect().width;
        stickySeam = Math.round(gap * 10) / 10;
      }

      /* Overlap check: does anything in a chart collide with a sibling label? */
      const tickOverlap = (wrapperSelector) => {
        const w = document.querySelector(wrapperSelector);
        if (!w) return null;
        const ticks = [
          ...w.querySelectorAll(
            ".recharts-xAxis .recharts-cartesian-axis-tick-value",
          ),
        ];
        let worst = Infinity;
        for (let i = 1; i < ticks.length; i++) {
          const a = ticks[i - 1].getBoundingClientRect();
          const b = ticks[i].getBoundingClientRect();
          worst = Math.min(worst, b.left - a.right);
        }
        return ticks.length < 2 ? null : Math.round(worst);
      };

      const wrappers = [...document.querySelectorAll(".recharts-wrapper")];
      const clippedYLabels = (() => {
        // vertical bar chart: category labels must not be cut by the axis width
        const bar = wrappers.find((n) =>
          n.querySelector(".recharts-bar-rectangle"),
        );
        if (!bar) return null;
        const labels = [
          ...bar.querySelectorAll(
            ".recharts-yAxis .recharts-cartesian-axis-tick-value",
          ),
        ];
        const wr = bar.getBoundingClientRect();
        let clipped = 0;
        for (const l of labels) {
          const r = l.getBoundingClientRect();
          if (r.left < wr.left - 0.5) clipped++;
        }
        return `${clipped}/${labels.length}`;
      })();

      return {
        overflow,
        docScrollWidth: de.scrollWidth,
        clientWidth: de.clientWidth,
        culprits,
        small: [...new Set(small)],
        kpiCols,
        throughputH: heightOf("日次の効率推移"),
        mixH: heightOf("ピッキング時間の内訳"),
        speedH: heightOf("ピッキング速度"),
        sticky,
        stickySeam,
        xTickGapThroughput: tickOverlap(".recharts-wrapper"),
        clippedYLabels,
      };
    },
    { TOUCH_MIN, coarse },
  );

  if (report.overflow > 1) {
    failures.push(
      `${w}px: document overflows by ${report.overflow}px ` +
        `(scrollWidth ${report.docScrollWidth} > clientWidth ${report.clientWidth})` +
        (report.culprits.length ? `\n    culprits: ${report.culprits.join("\n              ")}` : ""),
    );
  }
  if (report.small.length) {
    failures.push(`${w}px: touch targets under ${TOUCH_MIN}px → ${report.small.join(", ")}`);
  }

  rows.push({ w, coarse, ...report });

  if (WANT_SHOTS) {
    await page.screenshot({ path: `${SHOT_DIR}/w${w}.png`, fullPage: true });
  }
  await ctx.close();
}

await browser.close();

const pad = (v, n) => String(v).padStart(n);
console.log(
  "\nwidth  scrollW  clientW  overflow  kpiCols  throughput  mix  speed  sticky  seam  xTickGap  clippedNames",
);
for (const r of rows) {
  console.log(
    [
      pad(r.w, 5),
      pad(r.docScrollWidth, 8),
      pad(r.clientWidth, 8),
      pad(r.overflow, 9),
      pad(r.kpiCols, 8),
      pad(r.throughputH ?? "-", 11),
      pad(r.mixH ?? "-", 4),
      pad(r.speedH ?? "-", 6),
      pad(r.sticky ? "yes" : "NO", 7),
      pad(r.stickySeam ?? "-", 5),
      pad(r.xTickGapThroughput ?? "-", 9),
      pad(r.clippedYLabels ?? "-", 13),
    ].join(""),
  );
}

if (failures.length) {
  console.log("\nFAILURES:\n- " + failures.join("\n- "));
  process.exitCode = 1;
} else {
  console.log("\nOK — no horizontal document overflow, no undersized touch targets.");
}
