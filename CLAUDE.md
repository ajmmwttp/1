# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
pnpm dev                  # dev server, :3000
pnpm build                # production build (Turbopack)
pnpm start -p 3210        # serve the build — the verification scripts expect :3210
pnpm exec tsc --noEmit    # typecheck; the only static gate in the repo
```

There is no test runner, linter, or CI. The two verification scripts below are
the substitute, and both need a built app already being served.

```bash
node responsive-check.mjs             # asserts no horizontal document scroll at 8 widths
SHOTS=1 node responsive-check.mjs     # …and writes full-page PNGs to /tmp/responsive-check
BASE=http://127.0.0.1:3100 node shot.mjs   # dark/light/mobile screenshots + console-error capture
```

**Playwright's bundled Chromium is not installed here.** Never run
`npx playwright install`. Launch with an explicit binary instead:

```js
chromium.launch({ executablePath: "/opt/pw-browsers/chromium-1194/chrome-linux/chrome" })
```

## What this is

A single-page operations console (Japanese UI) for warehouse picking and
packing. Everything on screen argues one point: time is `a × 企業数 + b × 件数`,
so setup (段取り) is paid once per company list, not per item, and ranking
people by 分/個 alone punishes whoever drew many one-item lists.

Picking `a=112.8 s/company`, `b=65.7 s/item`; packing `a=50.0` (provisional),
`b=81.8`. Setup is 42.2% of all picking time. If you change a number on screen,
check it against `lib/data/warehouse.ts` — the figures are real, not filler.

## Architecture

`app/layout.tsx` mounts `AppShell`, **not** `app/page.tsx`. That is deliberate:
it lets `loading.tsx` and `error.tsx` render inside the chrome instead of
replacing the whole screen. `page.tsx` is a server component that composes
client islands.

```
components/ui/       Radix primitives, vendored by hand (see below)
components/shell/    sidebar, top bar, ⌘K palette, mobile drawer
components/kpi/      stat tiles, SVG sparkline, count-up hook
components/charts/   Recharts; every chart wraps ChartFrame
components/table/    the 26-person roster, sorting/filtering
components/states/   skeletons, empty, error
components/motion/   the shared entrance ladder
lib/data/warehouse.ts  generated, typed fixtures — do not hand-edit
```

## Things that will bite you

**shadcn/ui is vendored, and `npx shadcn add` cannot work here.**
`ui.shadcn.com` returns 403 through the proxy. `components/ui/*` is hand-written
Radix + CVA in the shadcn shape. Add new primitives the same way; npm itself is
reachable, so `@radix-ui/*` installs fine.

**Cascade layers are load-bearing in `app/globals.css`.**
Unlayered CSS outranks *every* Tailwind v4 utility regardless of specificity. A
bare `* { border-color }` at the top level silently beat every `border-*`
utility in the app. Base resets must stay inside `@layer base` and helpers
(`.field`, `.tnum`, `.skeleton`) inside `@layer components`. If a utility
mysteriously does nothing, check whether something unlayered is winning.

`.tnum` sets `letter-spacing`, so `tracking-*` utilities lose to it. Override
with an inline style when a numeral needs different tracking.

**`components/states/*` must not be `"use client"`.**
They take a `LucideIcon` as a prop. Functions cannot cross a server→client
boundary, so marking them client breaks `not-found.tsx` passing
`icon={FileQuestion}`. They compile into whichever graph imports them.

**`components/motion/ladder.ts` is separate from `reveal.tsx` on purpose.**
Every export of a `"use client"` module reaches a server component as a client
*reference*, not a value. Importing `REVEAL_STEPS` from `reveal.tsx` yielded
`undefined` and shipped `delay: NaN`. Shared constants go in a plain module.

## Charts

Colour tokens live in `lib/chart-theme.ts`. Three rules are not stylistic:

- **The gold accent is never a data-series colour.** It is interaction and
  emphasis only, so chrome can never be mistaken for data.
- **Categorical hues are capped at three**, assigned in fixed order and never
  cycled. A fourth was measured and fails: yellow↔orange scores CVD ΔE 4.8 and
  normal-vision ΔE 10.6 against a floor of 15. Part-to-whole views use three
  slices plus a neutral remainder.
- **Light-mode aqua is 2.82:1**, under the 3:1 line, so the relief rule applies:
  the donut legend carries hours and share per row and cannot be dropped.

Recharts 3 specifics already worked around — do not undo them:

- Tooltip payload drops null rows by default, which deleted the picking row on
  exactly the days the recording gap matters. `ChartTooltip` builds rows from
  the raw datum instead.
- A `ReferenceArea` whose bounds are absent from a category axis is dropped
  silently. The 記録なし band clamps to dates present in the current range.
- `Pie` lost `activeIndex`; the donut drives hover from local state.
- Default 1500ms series animation fights the card's own reveal. It is off where
  the reveal is already the entrance.
- `usePlotWidth` measures the plot box so charts thin their own ticks. Tick
  density follows available pixels, not the viewport — the same card is 758px
  at xl and 286px on a phone.

## Data

`lib/data/warehouse.ts` is generated. Totals reconcile to the source analysis:
picking 15,942 items / 6,791 companies / 30,275 min; packing 24,449 / 6,977 /
39,147.

`pickEff` is `null` from 2026-04-24 — a **real recording gap**, not a bug and
not sample noise. It is rendered as a hatched, labelled band. Do not "fix" it by
joining the line across it or by filtering those days out.

## Verifying visual work

Typecheck and build passing says nothing about whether the page looks right.
Two defects here typechecked clean and were only caught by screenshotting: a
y-axis 34px wide rendered `126` as `26` (Recharts clips, it does not wrap), and
a legend truncated the text that discharges the contrast relief rule. Render it
and look at it before calling visual work done.
