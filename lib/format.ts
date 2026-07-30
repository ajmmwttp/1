const JP = "ja-JP";

export const int = (n: number) => new Intl.NumberFormat(JP).format(Math.round(n));

export const dec = (n: number, d = 1) =>
  new Intl.NumberFormat(JP, { minimumFractionDigits: d, maximumFractionDigits: d }).format(n);

export const pct = (n: number, d = 1) => `${dec(n, d)}%`;

/** Always signed — a delta of exactly 0 still reads "±0.0%". */
export const signedPct = (n: number, d = 1) => {
  if (Math.abs(n) < 10 ** -d / 2) return `±${dec(0, d)}%`;
  return `${n > 0 ? "+" : "−"}${dec(Math.abs(n), d)}%`;
};

export const hours = (n: number) => `${dec(n, 1)}h`;

export const minutesToHours = (m: number) => m / 60;

/** "2026-04-08" → "4/8" */
export const shortDate = (iso: string) => {
  const [, m, d] = iso.split("-");
  return `${Number(m)}/${Number(d)}`;
};

/** "2026-04-08" → "4月8日(水)" */
export const longDate = (iso: string) => {
  const dt = new Date(`${iso}T00:00:00+09:00`);
  const w = ["日", "月", "火", "水", "木", "金", "土"][dt.getUTCDay()];
  return `${dt.getUTCMonth() + 1}月${dt.getUTCDate()}日(${w})`;
};

export const compact = (n: number) =>
  n >= 10000 ? `${dec(n / 10000, 1)}万` : int(n);
