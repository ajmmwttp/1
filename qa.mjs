/**
 * qa.mjs — measurable acceptance check for the dashboard.
 *
 * Scores criteria 1–6 objectively. Every check returns a number or a list of
 * offending selectors; nothing here is a judgement call.
 *
 *   node qa.mjs                 # score against BASE, write PNGs
 *   BASE=http://127.0.0.1:3300 node qa.mjs
 */
import { chromium } from "playwright";
import { mkdir, writeFile } from "node:fs/promises";

const BASE = process.env.BASE ?? "http://127.0.0.1:3300";
const CHROME =
  process.env.CHROME ?? "/opt/pw-browsers/chromium-1194/chrome-linux/chrome";
const OUT = process.env.OUT ?? "/tmp/qa";
const WIDTHS = [1440, 1024, 768, 390];

await mkdir(OUT, { recursive: true });

const probe = () => {
  const out = {
    overflowPx: 0,
    offenders: [],
    overlaps: [],
    clipped: [],
    gutters: [],
    rowHeightDelta: [],
    offGrid: [],
    fontSizes: {},
    lowContrast: [],
    kpiAboveFold: null,
    tickCounts: [],
    svgZeroSize: [],
    inkCollisions: [],
    hiddenByOpacity: [],
  };

  const doc = document.documentElement;
  out.overflowPx = doc.scrollWidth - doc.clientWidth;

  const vw = doc.clientWidth;
  const nodes = Array.from(document.querySelectorAll("body *"));

  const desc = (el) => {
    const cls = (el.getAttribute("class") || "").split(/\s+/).slice(0, 3).join(".");
    return `${el.tagName.toLowerCase()}${cls ? "." + cls : ""}`;
  };

  // ── 1a. anything painting outside the viewport ──────────────────
  for (const el of nodes) {
    const r = el.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) continue;
    if (r.right > vw + 1 || r.left < -1) {
      // ignore nodes inside a scroll container that is meant to scroll
      let p = el.parentElement,
        inScroller = false;
      while (p && p !== document.body) {
        const s = getComputedStyle(p);
        if (/(auto|scroll)/.test(s.overflowX)) {
          inScroller = true;
          break;
        }
        p = p.parentElement;
      }
      if (!inScroller) out.offenders.push(`${desc(el)} r=${Math.round(r.right)}`);
    }
  }

  // ── 1b. clipped text (scrollWidth beats clientWidth on a leaf) ───
  for (const el of nodes) {
    if (el.children.length) continue;
    const t = (el.textContent || "").trim();
    if (!t) continue;
    // sr-only clips to 1px on purpose — that is not a layout defect.
    if (el.closest(".sr-only")) continue;
    const s = getComputedStyle(el);
    const r0 = el.getBoundingClientRect();
    if (r0.width <= 1 || r0.height <= 1) continue;
    if (s.overflow === "visible" && s.textOverflow !== "ellipsis") continue;
    if (el.scrollWidth > el.clientWidth + 1) out.clipped.push(`${desc(el)} "${t.slice(0, 18)}"`);
  }

  // ── 1c. SVG charts that measured to nothing ─────────────────────
  for (const svg of document.querySelectorAll(".recharts-surface")) {
    const r = svg.getBoundingClientRect();
    if (r.width < 40 || r.height < 40) out.svgZeroSize.push(`${Math.round(r.width)}x${Math.round(r.height)}`);
  }

  // ── 1c-2. SVG ink collisions: does a plotted curve run through a
  //          chart label? A bounding-box test is not enough — sample the
  //          path itself and test containment in the label's box.
  for (const w of document.querySelectorAll(".recharts-wrapper")) {
    const labels = Array.from(w.querySelectorAll("text")).filter((t) => {
      const s = (t.textContent || "").trim();
      return s === "記録なし" || s === "標準";
    });
    if (!labels.length) continue;
    const curves = Array.from(w.querySelectorAll("path.recharts-curve"));
    for (const label of labels) {
      const lb = label.getBoundingClientRect();
      let hits = 0;
      for (const path of curves) {
        let len = 0;
        try {
          len = path.getTotalLength();
        } catch {
          continue;
        }
        if (!len) continue;
        for (let i = 0; i <= 400; i++) {
          const pt = path.getPointAtLength((len * i) / 400);
          const sc = path.ownerSVGElement.getScreenCTM();
          if (!sc) break;
          const x = sc.a * pt.x + sc.c * pt.y + sc.e;
          const y = sc.b * pt.x + sc.d * pt.y + sc.f;
          if (x >= lb.left && x <= lb.right && y >= lb.top && y <= lb.bottom) hits++;
        }
      }
      if (hits > 0)
        out.inkCollisions.push(`"${(label.textContent || "").trim()}" x${hits}`);
    }
  }

  // ── 1d. anything still invisible after hydration ────────────────
  for (const el of document.querySelectorAll("[data-reveal]")) {
    const s = getComputedStyle(el);
    if (parseFloat(s.opacity) < 0.99) out.hiddenByOpacity.push(`${desc(el)} op=${s.opacity}`);
  }

  // ── 2. grid: gutters + equal card heights per row ───────────────
  const cards = Array.from(document.querySelectorAll("[data-card]"));
  const rows = new Map();
  for (const c of cards) {
    const r = c.getBoundingClientRect();
    const key = Math.round(r.top / 4);
    if (!rows.has(key)) rows.set(key, []);
    rows.get(key).push(r);
  }
  for (const [, rs] of rows) {
    if (rs.length < 2) continue;
    rs.sort((a, b) => a.left - b.left);
    for (let i = 1; i < rs.length; i++) out.gutters.push(Math.round(rs[i].left - rs[i - 1].right));
    const hs = rs.map((r) => Math.round(r.height));
    out.rowHeightDelta.push(Math.max(...hs) - Math.min(...hs));
  }

  // ── 2b. 8px baseline on section gaps ───────────────────────────
  for (const el of document.querySelectorAll("[data-section]")) {
    const s = getComputedStyle(el);
    for (const p of ["marginTop", "marginBottom", "paddingTop", "paddingBottom", "gap", "rowGap"]) {
      const v = parseFloat(s[p]);
      if (v > 0 && v % 4 !== 0) out.offGrid.push(`${desc(el)} ${p}=${v}`);
    }
  }

  // ── 4. type scale ──────────────────────────────────────────────
  for (const el of nodes) {
    const t = (el.textContent || "").trim();
    if (!t || el.children.length) continue;
    // Not typography: script/style payloads and the visually-hidden skip link.
    if (/^(script|style|noscript)$/i.test(el.tagName)) continue;
    if (el.closest(".sr-only")) continue;
    const px = Math.round(parseFloat(getComputedStyle(el).fontSize) * 10) / 10;
    out.fontSizes[px] = (out.fontSizes[px] || 0) + 1;
  }

  // ── 5. text contrast (composite over the nearest painted bg) ────
  const lum = (c) => {
    const [r, g, b] = c;
    const f = (v) => {
      v /= 255;
      return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
    };
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b);
  };
  const parse = (s) => (s.match(/[\d.]+/g) || []).map(Number);
  const bgOf = (el) => {
    // SVG nodes have no painted background of their own — walk out to the
    // HTML ancestor that actually fills, otherwise every tick scores against
    // transparent and passes by accident.
    let p = el.ownerSVGElement ? el.ownerSVGElement.parentElement : el;
    while (p && p !== document.documentElement) {
      const c = parse(getComputedStyle(p).backgroundColor);
      if (c.length >= 3 && (c[3] === undefined || c[3] > 0.9)) return c;
      p = p.parentElement;
    }
    return [255, 255, 255];
  };
  for (const el of nodes) {
    if (el.children.length) continue;
    const t = (el.textContent || "").trim();
    if (!t) continue;
    const s = getComputedStyle(el);
    if (parseFloat(s.opacity) < 0.5) continue;
    const r = el.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) continue;
    // SVG text paints with `fill`, not `color`. Reading only `color` scored
    // every chart label as passing against an inherited value it never uses.
    const isSvgText = el.ownerSVGElement != null;
    const fg = parse(isSvgText ? s.fill || s.color : s.color),
      bg = bgOf(el);
    if (fg.length < 3) continue;
    const a = fg[3] === undefined ? 1 : fg[3];
    const mix = [0, 1, 2].map((i) => fg[i] * a + bg[i] * (1 - a));
    const L1 = lum(mix),
      L2 = lum(bg);
    const ratio = (Math.max(L1, L2) + 0.05) / (Math.min(L1, L2) + 0.05);
    const px = parseFloat(s.fontSize);
    const bold = parseInt(s.fontWeight, 10) >= 700;
    const large = px >= 24 || (px >= 18.66 && bold);
    const need = large ? 3 : 4.5;
    if (ratio < need)
      out.lowContrast.push(`${desc(el)} ${ratio.toFixed(2)}:1 ${px}px "${t.slice(0, 16)}"`);
  }

  // ── 6. KPI row inside the first viewport ───────────────────────
  const kpi = document.querySelector("[data-kpi-row]");
  if (kpi) out.kpiAboveFold = Math.round(kpi.getBoundingClientRect().bottom);

  // ── 3. tick counts per chart ───────────────────────────────────
  // Recharts 3 paints axis ticks into their own z-index layers, so they are
  // NOT descendants of the axis <g>. Group them geometrically instead:
  // x-axis ticks share a y coordinate, y-axis ticks share an x coordinate.
  // Only VALUE axes are held to 5±2 — a category axis shows one label per
  // datum, which is the data, not a tick-density choice.
  for (const w of document.querySelectorAll(".recharts-wrapper")) {
    const labels = Array.from(
      w.querySelectorAll(".recharts-cartesian-axis-tick-value"),
    ).map((t) => {
      const r = t.getBoundingClientRect();
      return {
        t: (t.textContent || "").trim(),
        cy: r.top + r.height / 2,
        left: r.left,
        right: r.right,
      };
    });
    if (!labels.length) continue;
    const cluster = (key) => {
      const groups = [];
      for (const l of labels) {
        const g = groups.find((g) => Math.abs(g.v - l[key]) <= 3);
        if (g) g.items.push(l);
        else groups.push({ v: l[key], items: [l] });
      }
      return groups.sort((a, b) => b.items.length - a.items.length)[0];
    };
    const isNum = (arr) =>
      arr.every((l) => {
        const v = l.t.replace(/[,%\s]/g, "");
        return v !== "" && !Number.isNaN(Number(v));
      });
    const xg = cluster("cy"); // one row of labels = the x axis
    // y-axis labels are right-anchored, so their centres differ while an edge
    // stays constant. Take whichever edge clusters more of them.
    const yl = cluster("left");
    const yr = cluster("right");
    const yg =
      (yr ? yr.items.length : 0) >= (yl ? yl.items.length : 0) ? yr : yl;
    const entry = { x: null, y: null };
    if (xg && xg.items.length > 1 && isNum(xg.items)) entry.x = xg.items.length;
    if (yg && yg.items.length > 1 && isNum(yg.items)) entry.y = yg.items.length;
    if (entry.x !== null || entry.y !== null) out.tickCounts.push(entry);
  }

  return out;
};

const browser = await chromium.launch({ executablePath: CHROME });
const report = {};

for (const w of WIDTHS) {
  const ctx = await browser.newContext({
    viewport: { width: w, height: 900 },
    deviceScaleFactor: 1,
    colorScheme: "dark",
  });
  const page = await ctx.newPage();
  const errs = [];
  page.on("pageerror", (e) => errs.push(e.message));
  page.on("console", (m) => m.type() === "error" && errs.push(m.text()));
  await page.goto(BASE, { waitUntil: "load", timeout: 45000 });
  await page.waitForTimeout(2000);
  const r = await page.evaluate(probe);
  r.consoleErrors = errs.filter((e) => !/favicon|404/.test(e));
  report[w] = r;
  await page.screenshot({ path: `${OUT}/w${w}.png`, fullPage: true });
  await ctx.close();
}
await browser.close();

// ── score ────────────────────────────────────────────────────────
const lines = [];
const mark = (ok) => (ok ? "◯" : "×");
const score = {};

const allW = WIDTHS;
const c1 = allW.every(
  (w) =>
    report[w].overflowPx <= 1 &&
    report[w].offenders.length === 0 &&
    report[w].clipped.length === 0 &&
    report[w].svgZeroSize.length === 0 &&
    report[w].inkCollisions.length === 0 &&
    report[w].hiddenByOpacity.length === 0,
);
const c2 = allW.every((w) => {
  const g = report[w].gutters;
  return (
    (g.length === 0 || new Set(g).size === 1) &&
    report[w].rowHeightDelta.every((d) => d <= 1) &&
    report[w].offGrid.length === 0
  );
});
const sizes = new Set();
for (const w of allW) Object.keys(report[w].fontSizes).forEach((s) => sizes.add(s));
const c4 = sizes.size <= 4; // 11 / 13 meta+body, 22 / 30 display
const c5 = allW.every((w) => report[w].lowContrast.length === 0);
const c6 = allW.every(
  (w) => report[w].kpiAboveFold !== null && report[w].kpiAboveFold <= 900,
);
const c3 = allW.every((w) =>
  report[w].tickCounts.every(
    (t) => (t.x === null || (t.x >= 3 && t.x <= 7)) && (t.y === null || (t.y >= 3 && t.y <= 7)),
  ),
);

score["1 崩れゼロ"] = c1;
score["2 グリッド整合"] = c2;
score["3 目盛5±2"] = c3;
score["4 タイポ"] = c4;
score["5 コントラスト"] = c5;
score["6 情報階層"] = c6;

for (const [k, v] of Object.entries(score)) lines.push(`${mark(v)} ${k}`);
lines.push("");
for (const w of allW) {
  const r = report[w];
  lines.push(`── ${w}px ──`);
  lines.push(`  overflow=${r.overflowPx}px  offenders=${r.offenders.length}  clipped=${r.clipped.length}`);
  lines.push(`  svgZero=${r.svgZeroSize.length}  inkCollision=${r.inkCollisions.length}  invisible=${r.hiddenByOpacity.length}  consoleErrors=${r.consoleErrors.length}`);
  if (r.inkCollisions.length) lines.push(`   ! ink: ${r.inkCollisions.join(" | ")}`);
  lines.push(`  gutters=[${[...new Set(r.gutters)].join(",")}]  rowHeightDelta=[${r.rowHeightDelta.join(",")}]  offGrid=${r.offGrid.length}`);
  lines.push(`  ticks=${JSON.stringify(r.tickCounts)}`);
  lines.push(`  lowContrast=${r.lowContrast.length}  kpiBottom=${r.kpiAboveFold}`);
  if (r.offenders.length) lines.push(`   ! overflow: ${r.offenders.slice(0, 6).join(" | ")}`);
  if (r.clipped.length) lines.push(`   ! clipped: ${r.clipped.slice(0, 6).join(" | ")}`);
  if (r.hiddenByOpacity.length) lines.push(`   ! invisible: ${r.hiddenByOpacity.slice(0, 4).join(" | ")}`);
  if (r.offGrid.length) lines.push(`   ! offGrid: ${r.offGrid.slice(0, 6).join(" | ")}`);
  if (r.lowContrast.length) lines.push(`   ! contrast: ${r.lowContrast.slice(0, 8).join(" | ")}`);
}
lines.push("");
lines.push(`font sizes in use (${sizes.size}): ${[...sizes].sort((a, b) => a - b).join(", ")}`);

const text = lines.join("\n");
console.log(text);
await writeFile(`${OUT}/report.txt`, text);
await writeFile(`${OUT}/report.json`, JSON.stringify(report, null, 1));
process.exitCode = Object.values(score).every(Boolean) ? 0 : 1;
