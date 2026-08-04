// 自動生成 — mkwarehouse.py が dash.json から書き出す。手で編集しない。
// 出典: 月次実績表を IE 標準時間モデル T = a×企業数 + b×件数 で評価したもの。
//   ピッキング a=92.1 秒/社, b=75.6 秒/件
//   梱包       a=92.1 秒/社, b=69.5 秒/件
// 梱包の a は統計的に 0 と区別できない（95%CI が 0 を挟む）。値そのものより
// 不安定さのほうが情報で、詳しくは報告書の付録Cを参照。

export type Verdict = "上位" | "標準" | "要支援";
export type Role = "staff" | "parttime";

export interface ProcessStats {
  items: number;            // 件数
  minutes: number;          // 実測時間（分）
  companies: number;        // 企業数＝リスト枚数
  days: number;             // 記録日数
  itemsPerCompany: number;  // 件/社
  rawSecPerItem: number;    // 素の秒/件（従来指標）
  pureSecPerItem: number;   // 段取りを除いた純速度
  setupHours: number;       // 段取り時間
  efficiency: number;       // 効率 %
  shrunk: number;           // 縮小後効率 %（順位づけ用）
  lo: number;               // 95% 下限
  hi: number;               // 95% 上限
  fairTarget: number;       // 公平目標 分/個
  verdict: Verdict;
}

export interface Worker {
  name: string;
  role: Role;
  pick: ProcessStats | null;
  pack: ProcessStats | null;
}

export interface DayPoint {
  date: string;
  pickItems: number; pickMinutes: number; pickCompanies: number;
  pickEff: number | null; pickSetup: number;
  packItems: number; packMinutes: number; packCompanies: number;
  packEff: number | null; packSetup: number;
  setupMinutes: number; totalItems: number; totalHours: number;
}

export interface MixSlice { label: string; detail: string; hours: number }

/** 標準時間モデルの係数。画面に式を出すときは必ずここから取る。 */
export const model = {
  pick: { a: 92.1, b: 75.6 },
  pack: { a: 92.1, b: 69.5 },
} as const;

/**
 * 散布図①②の相関。① は素の秒/件、② は段取りを除いた純速度で、
 * どちらも横軸は 社/件（リストの組み方）。
 */
export const scatterStats = {
  raw: {
  "r": 0.432,
  "p": 0.019,
  "n": 29
},
  pure: {
  "r": 0.089,
  "p": 0.646,
  "n": 29
},
} as const;

export const days: DayPoint[] = [
  {
    "date": "2026-04-01",
    "pickItems": 1192,
    "pickMinutes": 2066,
    "pickCompanies": 521,
    "pickEff": 111.4,
    "pickSetup": 799,
    "packItems": 1224,
    "packMinutes": 1866,
    "packCompanies": 321,
    "packEff": 102.4,
    "packSetup": 492,
    "setupMinutes": 1291,
    "totalItems": 2416,
    "totalHours": 65.5
  },
  {
    "date": "2026-04-02",
    "pickItems": 1159,
    "pickMinutes": 2021,
    "pickCompanies": 490,
    "pickEff": 109.5,
    "pickSetup": 752,
    "packItems": 1139,
    "packMinutes": 1825,
    "packCompanies": 316,
    "packEff": 98.8,
    "packSetup": 484,
    "setupMinutes": 1236,
    "totalItems": 2298,
    "totalHours": 64.1
  },
  {
    "date": "2026-04-03",
    "pickItems": 1330,
    "pickMinutes": 1905,
    "pickCompanies": 526,
    "pickEff": 130.3,
    "pickSetup": 807,
    "packItems": 1339,
    "packMinutes": 1798,
    "packCompanies": 394,
    "packEff": 119.9,
    "packSetup": 605,
    "setupMinutes": 1412,
    "totalItems": 2669,
    "totalHours": 61.7
  },
  {
    "date": "2026-04-06",
    "pickItems": 1351,
    "pickMinutes": 2428,
    "pickCompanies": 576,
    "pickEff": 106.5,
    "pickSetup": 884,
    "packItems": 1412,
    "packMinutes": 2216,
    "packCompanies": 419,
    "packEff": 102.8,
    "packSetup": 643,
    "setupMinutes": 1527,
    "totalItems": 2763,
    "totalHours": 77.4
  },
  {
    "date": "2026-04-07",
    "pickItems": 1217,
    "pickMinutes": 2114,
    "pickCompanies": 494,
    "pickEff": 108.4,
    "pickSetup": 758,
    "packItems": 1260,
    "packMinutes": 1875,
    "packCompanies": 353,
    "packEff": 106.7,
    "packSetup": 541,
    "setupMinutes": 1299,
    "totalItems": 2477,
    "totalHours": 66.5
  },
  {
    "date": "2026-04-08",
    "pickItems": 1371,
    "pickMinutes": 2064,
    "pickCompanies": 580,
    "pickEff": 126.8,
    "pickSetup": 890,
    "packItems": 1322,
    "packMinutes": 2027,
    "packCompanies": 356,
    "packEff": 102.5,
    "packSetup": 547,
    "setupMinutes": 1437,
    "totalItems": 2693,
    "totalHours": 68.2
  },
  {
    "date": "2026-04-09",
    "pickItems": 1137,
    "pickMinutes": 1995,
    "pickCompanies": 487,
    "pickEff": 109.3,
    "pickSetup": 747,
    "packItems": 1215,
    "packMinutes": 1690,
    "packCompanies": 362,
    "packEff": 116.2,
    "packSetup": 556,
    "setupMinutes": 1303,
    "totalItems": 2352,
    "totalHours": 61.4
  },
  {
    "date": "2026-04-10",
    "pickItems": 770,
    "pickMinutes": 1544,
    "pickCompanies": 328,
    "pickEff": 95.5,
    "pickSetup": 504,
    "packItems": 1225,
    "packMinutes": 1942,
    "packCompanies": 358,
    "packEff": 101.4,
    "packSetup": 550,
    "setupMinutes": 1054,
    "totalItems": 1995,
    "totalHours": 58.1
  },
  {
    "date": "2026-04-13",
    "pickItems": 641,
    "pickMinutes": 1563,
    "pickCompanies": 277,
    "pickEff": 78.9,
    "pickSetup": 425,
    "packItems": 1471,
    "packMinutes": 2591,
    "packCompanies": 418,
    "packEff": 90.5,
    "packSetup": 641,
    "setupMinutes": 1066,
    "totalItems": 2112,
    "totalHours": 69.2
  },
  {
    "date": "2026-04-14",
    "pickItems": 692,
    "pickMinutes": 1563,
    "pickCompanies": 291,
    "pickEff": 84.4,
    "pickSetup": 447,
    "packItems": 1031,
    "packMinutes": 1913,
    "packCompanies": 309,
    "packEff": 87.2,
    "packSetup": 474,
    "setupMinutes": 921,
    "totalItems": 1723,
    "totalHours": 57.9
  },
  {
    "date": "2026-04-15",
    "pickItems": 805,
    "pickMinutes": 1794,
    "pickCompanies": 344,
    "pickEff": 86.0,
    "pickSetup": 528,
    "packItems": 863,
    "packMinutes": 1416,
    "packCompanies": 254,
    "packEff": 98.2,
    "packSetup": 391,
    "setupMinutes": 919,
    "totalItems": 1668,
    "totalHours": 53.5
  },
  {
    "date": "2026-04-16",
    "pickItems": 571,
    "pickMinutes": 1335,
    "pickCompanies": 254,
    "pickEff": 83.1,
    "pickSetup": 390,
    "packItems": 1011,
    "packMinutes": 1657,
    "packCompanies": 301,
    "packEff": 98.6,
    "packSetup": 462,
    "setupMinutes": 852,
    "totalItems": 1582,
    "totalHours": 49.9
  },
  {
    "date": "2026-04-17",
    "pickItems": 562,
    "pickMinutes": 1117,
    "pickCompanies": 239,
    "pickEff": 96.3,
    "pickSetup": 368,
    "packItems": 1031,
    "packMinutes": 1616,
    "packCompanies": 303,
    "packEff": 102.7,
    "packSetup": 465,
    "setupMinutes": 833,
    "totalItems": 1593,
    "totalHours": 45.5
  },
  {
    "date": "2026-04-20",
    "pickItems": 649,
    "pickMinutes": 1717,
    "pickCompanies": 293,
    "pickEff": 73.9,
    "pickSetup": 451,
    "packItems": 905,
    "packMinutes": 1503,
    "packCompanies": 269,
    "packEff": 97.2,
    "packSetup": 413,
    "setupMinutes": 864,
    "totalItems": 1554,
    "totalHours": 53.7
  },
  {
    "date": "2026-04-21",
    "pickItems": 1107,
    "pickMinutes": 2256,
    "pickCompanies": 489,
    "pickEff": 95.1,
    "pickSetup": 751,
    "packItems": 1127,
    "packMinutes": 1907,
    "packCompanies": 340,
    "packEff": 95.8,
    "packSetup": 521,
    "setupMinutes": 1272,
    "totalItems": 2234,
    "totalHours": 69.4
  },
  {
    "date": "2026-04-22",
    "pickItems": 891,
    "pickMinutes": 1786,
    "pickCompanies": 384,
    "pickEff": 95.9,
    "pickSetup": 590,
    "packItems": 926,
    "packMinutes": 1520,
    "packCompanies": 255,
    "packEff": 96.3,
    "packSetup": 391,
    "setupMinutes": 981,
    "totalItems": 1817,
    "totalHours": 55.1
  },
  {
    "date": "2026-04-23",
    "pickItems": 829,
    "pickMinutes": 1679,
    "pickCompanies": 349,
    "pickEff": 94.1,
    "pickSetup": 535,
    "packItems": 1001,
    "packMinutes": 1767,
    "packCompanies": 291,
    "packEff": 90.9,
    "packSetup": 446,
    "setupMinutes": 981,
    "totalItems": 1830,
    "totalHours": 57.4
  },
  {
    "date": "2026-04-24",
    "pickItems": 1416,
    "pickMinutes": 2757,
    "pickCompanies": 615,
    "pickEff": 99.0,
    "pickSetup": 944,
    "packItems": 1336,
    "packMinutes": 2045,
    "packCompanies": 394,
    "packEff": 105.3,
    "packSetup": 605,
    "setupMinutes": 1549,
    "totalItems": 2752,
    "totalHours": 80.0
  },
  {
    "date": "2026-04-27",
    "pickItems": 1221,
    "pickMinutes": 2739,
    "pickCompanies": 530,
    "pickEff": 85.9,
    "pickSetup": 814,
    "packItems": 1305,
    "packMinutes": 2486,
    "packCompanies": 382,
    "packEff": 84.4,
    "packSetup": 586,
    "setupMinutes": 1400,
    "totalItems": 2526,
    "totalHours": 87.1
  },
  {
    "date": "2026-04-28",
    "pickItems": 1237,
    "pickMinutes": 2644,
    "pickCompanies": 547,
    "pickEff": 90.7,
    "pickSetup": 840,
    "packItems": 1306,
    "packMinutes": 1830,
    "packCompanies": 381,
    "packEff": 114.6,
    "packSetup": 585,
    "setupMinutes": 1425,
    "totalItems": 2543,
    "totalHours": 74.6
  },
  {
    "date": "2026-04-30",
    "pickItems": 1101,
    "pickMinutes": 1696,
    "pickCompanies": 498,
    "pickEff": 126.9,
    "pickSetup": 765,
    "packItems": 1018,
    "packMinutes": 1697,
    "packCompanies": 295,
    "packEff": 96.2,
    "packSetup": 453,
    "setupMinutes": 1218,
    "totalItems": 2119,
    "totalHours": 56.5
  }
];

export const workers: Worker[] = [
  {
    "name": "本吉有美子",
    "role": "parttime",
    "pick": {
      "items": 1454,
      "minutes": 2028,
      "companies": 611,
      "days": 18,
      "itemsPerCompany": 2.38,
      "rawSecPerItem": 83.7,
      "pureSecPerItem": 45.0,
      "setupHours": 15.6,
      "efficiency": 136.6,
      "shrunk": 127.3,
      "lo": 112.1,
      "hi": 142.5,
      "fairTarget": 1.91,
      "verdict": "上位"
    },
    "pack": {
      "items": 2493,
      "minutes": 2599,
      "companies": 653,
      "days": 20,
      "itemsPerCompany": 3.82,
      "rawSecPerItem": 62.6,
      "pureSecPerItem": 38.4,
      "setupHours": 16.7,
      "efficiency": 149.7,
      "shrunk": 146.6,
      "lo": 131.4,
      "hi": 161.9,
      "fairTarget": 1.56,
      "verdict": "上位"
    }
  },
  {
    "name": "澤田凌",
    "role": "staff",
    "pick": {
      "items": 790,
      "minutes": 1245,
      "companies": 475,
      "days": 11,
      "itemsPerCompany": 1.66,
      "rawSecPerItem": 94.6,
      "pureSecPerItem": 39.2,
      "setupHours": 12.1,
      "efficiency": 138.5,
      "shrunk": 124.8,
      "lo": 106.9,
      "hi": 142.8,
      "fairTarget": 2.18,
      "verdict": "上位"
    },
    "pack": {
      "items": 634,
      "minutes": 1530,
      "companies": 249,
      "days": 10,
      "itemsPerCompany": 2.54,
      "rawSecPerItem": 144.8,
      "pureSecPerItem": 108.6,
      "setupHours": 6.4,
      "efficiency": 73.0,
      "shrunk": 78.0,
      "lo": 57.2,
      "hi": 98.8,
      "fairTarget": 1.76,
      "verdict": "要支援"
    }
  },
  {
    "name": "大江美記子",
    "role": "parttime",
    "pick": {
      "items": 981,
      "minutes": 1535,
      "companies": 481,
      "days": 16,
      "itemsPerCompany": 2.04,
      "rawSecPerItem": 93.9,
      "pureSecPerItem": 48.8,
      "setupHours": 12.3,
      "efficiency": 128.6,
      "shrunk": 120.9,
      "lo": 105.0,
      "hi": 136.8,
      "fairTarget": 2.01,
      "verdict": "上位"
    },
    "pack": {
      "items": 2616,
      "minutes": 3060,
      "companies": 675,
      "days": 19,
      "itemsPerCompany": 3.88,
      "rawSecPerItem": 70.2,
      "pureSecPerItem": 46.4,
      "setupHours": 17.3,
      "efficiency": 132.9,
      "shrunk": 131.0,
      "lo": 115.4,
      "hi": 146.6,
      "fairTarget": 1.55,
      "verdict": "上位"
    }
  },
  {
    "name": "佐藤辰成",
    "role": "staff",
    "pick": {
      "items": 667,
      "minutes": 810,
      "companies": 148,
      "days": 10,
      "itemsPerCompany": 4.52,
      "rawSecPerItem": 72.9,
      "pureSecPerItem": 52.5,
      "setupHours": 3.8,
      "efficiency": 131.7,
      "shrunk": 120.1,
      "lo": 101.6,
      "hi": 138.5,
      "fairTarget": 1.6,
      "verdict": "標準"
    },
    "pack": {
      "items": 284,
      "minutes": 305,
      "companies": 49,
      "days": 7,
      "itemsPerCompany": 5.8,
      "rawSecPerItem": 64.4,
      "pureSecPerItem": 48.6,
      "setupHours": 1.3,
      "efficiency": 132.5,
      "shrunk": 128.0,
      "lo": 103.9,
      "hi": 152.2,
      "fairTarget": 1.42,
      "verdict": "標準"
    }
  },
  {
    "name": "春谷智子",
    "role": "parttime",
    "pick": {
      "items": 122,
      "minutes": 210,
      "companies": 73,
      "days": 4,
      "itemsPerCompany": 1.66,
      "rawSecPerItem": 103.3,
      "pureSecPerItem": 47.9,
      "setupHours": 1.9,
      "efficiency": 126.8,
      "shrunk": 111.9,
      "lo": 89.0,
      "hi": 134.9,
      "fairTarget": 2.18,
      "verdict": "標準"
    },
    "pack": null
  },
  {
    "name": "後藤克行",
    "role": "staff",
    "pick": {
      "items": 2007,
      "minutes": 3585,
      "companies": 959,
      "days": 20,
      "itemsPerCompany": 2.09,
      "rawSecPerItem": 107.2,
      "pureSecPerItem": 63.2,
      "setupHours": 24.5,
      "efficiency": 111.6,
      "shrunk": 109.5,
      "lo": 94.8,
      "hi": 124.2,
      "fairTarget": 1.99,
      "verdict": "標準"
    },
    "pack": {
      "items": 1421,
      "minutes": 2760,
      "companies": 372,
      "days": 20,
      "itemsPerCompany": 3.82,
      "rawSecPerItem": 116.5,
      "pureSecPerItem": 92.4,
      "setupHours": 9.5,
      "efficiency": 80.3,
      "shrunk": 82.5,
      "lo": 67.2,
      "hi": 97.7,
      "fairTarget": 1.56,
      "verdict": "要支援"
    }
  },
  {
    "name": "中村美佳",
    "role": "staff",
    "pick": {
      "items": 79,
      "minutes": 120,
      "companies": 30,
      "days": 3,
      "itemsPerCompany": 2.61,
      "rawSecPerItem": 91.1,
      "pureSecPerItem": 55.8,
      "setupHours": 0.8,
      "efficiency": 121.7,
      "shrunk": 109.0,
      "lo": 84.9,
      "hi": 133.0,
      "fairTarget": 1.85,
      "verdict": "標準"
    },
    "pack": {
      "items": 375,
      "minutes": 730,
      "companies": 106,
      "days": 4,
      "itemsPerCompany": 3.54,
      "rawSecPerItem": 116.8,
      "pureSecPerItem": 90.8,
      "setupHours": 2.7,
      "efficiency": 81.8,
      "shrunk": 89.6,
      "lo": 59.7,
      "hi": 119.5,
      "fairTarget": 1.59,
      "verdict": "標準"
    }
  },
  {
    "name": "晩田恵美",
    "role": "parttime",
    "pick": {
      "items": 877,
      "minutes": 1346,
      "companies": 231,
      "days": 14,
      "itemsPerCompany": 3.8,
      "rawSecPerItem": 92.1,
      "pureSecPerItem": 67.8,
      "setupHours": 5.9,
      "efficiency": 108.4,
      "shrunk": 106.8,
      "lo": 90.2,
      "hi": 123.4,
      "fairTarget": 1.66,
      "verdict": "標準"
    },
    "pack": {
      "items": 2881,
      "minutes": 4007,
      "companies": 988,
      "days": 19,
      "itemsPerCompany": 2.92,
      "rawSecPerItem": 83.5,
      "pureSecPerItem": 51.9,
      "setupHours": 25.3,
      "efficiency": 121.1,
      "shrunk": 120.2,
      "lo": 104.5,
      "hi": 135.8,
      "fairTarget": 1.68,
      "verdict": "標準"
    }
  },
  {
    "name": "高橋佐織",
    "role": "parttime",
    "pick": {
      "items": 941,
      "minutes": 1685,
      "companies": 400,
      "days": 16,
      "itemsPerCompany": 2.35,
      "rawSecPerItem": 107.4,
      "pureSecPerItem": 68.3,
      "setupHours": 10.2,
      "efficiency": 106.8,
      "shrunk": 105.8,
      "lo": 89.9,
      "hi": 121.7,
      "fairTarget": 1.91,
      "verdict": "標準"
    },
    "pack": {
      "items": 2422,
      "minutes": 4132,
      "companies": 699,
      "days": 20,
      "itemsPerCompany": 3.46,
      "rawSecPerItem": 102.4,
      "pureSecPerItem": 75.8,
      "setupHours": 17.9,
      "efficiency": 93.9,
      "shrunk": 95.0,
      "lo": 79.7,
      "hi": 110.3,
      "fairTarget": 1.6,
      "verdict": "標準"
    }
  },
  {
    "name": "山本祥吉",
    "role": "staff",
    "pick": {
      "items": 2129,
      "minutes": 3589,
      "companies": 736,
      "days": 20,
      "itemsPerCompany": 2.89,
      "rawSecPerItem": 101.1,
      "pureSecPerItem": 69.3,
      "setupHours": 18.8,
      "efficiency": 106.2,
      "shrunk": 105.5,
      "lo": 90.9,
      "hi": 120.2,
      "fairTarget": 1.79,
      "verdict": "標準"
    },
    "pack": {
      "items": 1548,
      "minutes": 2828,
      "companies": 393,
      "days": 20,
      "itemsPerCompany": 3.94,
      "rawSecPerItem": 109.6,
      "pureSecPerItem": 86.2,
      "setupHours": 10.1,
      "efficiency": 84.7,
      "shrunk": 86.5,
      "lo": 71.3,
      "hi": 101.8,
      "fairTarget": 1.55,
      "verdict": "要支援"
    }
  },
  {
    "name": "佐々木千恵",
    "role": "staff",
    "pick": {
      "items": 681,
      "minutes": 1082,
      "companies": 191,
      "days": 10,
      "itemsPerCompany": 3.57,
      "rawSecPerItem": 95.3,
      "pureSecPerItem": 69.5,
      "setupHours": 4.9,
      "efficiency": 106.4,
      "shrunk": 105.2,
      "lo": 86.7,
      "hi": 123.7,
      "fairTarget": 1.69,
      "verdict": "標準"
    },
    "pack": {
      "items": 890,
      "minutes": 770,
      "companies": 191,
      "days": 7,
      "itemsPerCompany": 4.65,
      "rawSecPerItem": 51.9,
      "pureSecPerItem": 32.1,
      "setupHours": 4.9,
      "efficiency": 172.0,
      "shrunk": 160.2,
      "lo": 136.0,
      "hi": 184.3,
      "fairTarget": 1.49,
      "verdict": "上位"
    }
  },
  {
    "name": "北田倫子",
    "role": "parttime",
    "pick": {
      "items": 468,
      "minutes": 1001,
      "companies": 281,
      "days": 14,
      "itemsPerCompany": 1.67,
      "rawSecPerItem": 128.3,
      "pureSecPerItem": 73.0,
      "setupHours": 7.2,
      "efficiency": 102.0,
      "shrunk": 102.5,
      "lo": 85.9,
      "hi": 119.1,
      "fairTarget": 2.18,
      "verdict": "標準"
    },
    "pack": {
      "items": 1442,
      "minutes": 1758,
      "companies": 472,
      "days": 13,
      "itemsPerCompany": 3.06,
      "rawSecPerItem": 73.1,
      "pureSecPerItem": 43.0,
      "setupHours": 12.1,
      "efficiency": 136.2,
      "shrunk": 133.2,
      "lo": 114.6,
      "hi": 151.7,
      "fairTarget": 1.66,
      "verdict": "上位"
    }
  },
  {
    "name": "中納沙織",
    "role": "staff",
    "pick": {
      "items": 1143,
      "minutes": 2255,
      "companies": 556,
      "days": 9,
      "itemsPerCompany": 2.06,
      "rawSecPerItem": 118.4,
      "pureSecPerItem": 73.6,
      "setupHours": 14.2,
      "efficiency": 101.7,
      "shrunk": 102.5,
      "lo": 83.5,
      "hi": 121.5,
      "fairTarget": 2.01,
      "verdict": "標準"
    },
    "pack": {
      "items": 224,
      "minutes": 475,
      "companies": 38,
      "days": 3,
      "itemsPerCompany": 5.89,
      "rawSecPerItem": 127.2,
      "pureSecPerItem": 111.6,
      "setupHours": 1.0,
      "efficiency": 66.9,
      "shrunk": 81.6,
      "lo": 48.6,
      "hi": 114.6,
      "fairTarget": 1.42,
      "verdict": "標準"
    }
  },
  {
    "name": "石戸谷亜子",
    "role": "parttime",
    "pick": {
      "items": 846,
      "minutes": 1490,
      "companies": 282,
      "days": 8,
      "itemsPerCompany": 3.0,
      "rawSecPerItem": 105.7,
      "pureSecPerItem": 75.0,
      "setupHours": 7.2,
      "efficiency": 100.6,
      "shrunk": 102.0,
      "lo": 82.3,
      "hi": 121.6,
      "fairTarget": 1.77,
      "verdict": "標準"
    },
    "pack": null
  },
  {
    "name": "森田美加",
    "role": "parttime",
    "pick": {
      "items": 218,
      "minutes": 450,
      "companies": 109,
      "days": 5,
      "itemsPerCompany": 2.01,
      "rawSecPerItem": 123.9,
      "pureSecPerItem": 78.0,
      "setupHours": 2.8,
      "efficiency": 98.1,
      "shrunk": 101.2,
      "lo": 79.3,
      "hi": 123.2,
      "fairTarget": 2.02,
      "verdict": "標準"
    },
    "pack": {
      "items": 630,
      "minutes": 1945,
      "companies": 187,
      "days": 10,
      "itemsPerCompany": 3.37,
      "rawSecPerItem": 185.2,
      "pureSecPerItem": 157.9,
      "setupHours": 4.8,
      "efficiency": 52.3,
      "shrunk": 60.2,
      "lo": 39.3,
      "hi": 81.0,
      "fairTarget": 1.61,
      "verdict": "要支援"
    }
  },
  {
    "name": "河野忠",
    "role": "staff",
    "pick": {
      "items": 280,
      "minutes": 552,
      "companies": 124,
      "days": 6,
      "itemsPerCompany": 2.27,
      "rawSecPerItem": 118.3,
      "pureSecPerItem": 77.7,
      "setupHours": 3.2,
      "efficiency": 98.3,
      "shrunk": 101.1,
      "lo": 80.0,
      "hi": 122.2,
      "fairTarget": 1.94,
      "verdict": "標準"
    },
    "pack": {
      "items": 593,
      "minutes": 685,
      "companies": 71,
      "days": 7,
      "itemsPerCompany": 8.3,
      "rawSecPerItem": 69.3,
      "pureSecPerItem": 58.2,
      "setupHours": 1.8,
      "efficiency": 116.3,
      "shrunk": 114.9,
      "lo": 90.7,
      "hi": 139.1,
      "fairTarget": 1.34,
      "verdict": "標準"
    }
  },
  {
    "name": "木村千鶴",
    "role": "parttime",
    "pick": {
      "items": 691,
      "minutes": 1396,
      "companies": 339,
      "days": 16,
      "itemsPerCompany": 2.04,
      "rawSecPerItem": 121.2,
      "pureSecPerItem": 76.0,
      "setupHours": 8.7,
      "efficiency": 99.6,
      "shrunk": 100.8,
      "lo": 84.9,
      "hi": 116.7,
      "fairTarget": 2.01,
      "verdict": "標準"
    },
    "pack": {
      "items": 1750,
      "minutes": 3788,
      "companies": 452,
      "days": 20,
      "itemsPerCompany": 3.87,
      "rawSecPerItem": 129.9,
      "pureSecPerItem": 106.1,
      "setupHours": 11.6,
      "efficiency": 71.8,
      "shrunk": 74.6,
      "lo": 59.3,
      "hi": 89.9,
      "fairTarget": 1.55,
      "verdict": "要支援"
    }
  },
  {
    "name": "奥野愛海",
    "role": "parttime",
    "pick": {
      "items": 416,
      "minutes": 925,
      "companies": 209,
      "days": 3,
      "itemsPerCompany": 1.99,
      "rawSecPerItem": 133.4,
      "pureSecPerItem": 87.1,
      "setupHours": 5.3,
      "efficiency": 91.3,
      "shrunk": 99.9,
      "lo": 75.8,
      "hi": 123.9,
      "fairTarget": 2.03,
      "verdict": "標準"
    },
    "pack": null
  },
  {
    "name": "鈴木香織",
    "role": "parttime",
    "pick": {
      "items": 231,
      "minutes": 505,
      "companies": 128,
      "days": 10,
      "itemsPerCompany": 1.81,
      "rawSecPerItem": 131.2,
      "pureSecPerItem": 80.2,
      "setupHours": 3.3,
      "efficiency": 96.5,
      "shrunk": 99.4,
      "lo": 80.9,
      "hi": 117.9,
      "fairTarget": 2.11,
      "verdict": "標準"
    },
    "pack": {
      "items": 1050,
      "minutes": 1848,
      "companies": 380,
      "days": 12,
      "itemsPerCompany": 2.76,
      "rawSecPerItem": 105.6,
      "pureSecPerItem": 72.3,
      "setupHours": 9.7,
      "efficiency": 97.4,
      "shrunk": 98.7,
      "lo": 79.5,
      "hi": 118.0,
      "fairTarget": 1.71,
      "verdict": "標準"
    }
  },
  {
    "name": "向井ひかり",
    "role": "parttime",
    "pick": {
      "items": 866,
      "minutes": 1876,
      "companies": 389,
      "days": 12,
      "itemsPerCompany": 2.23,
      "rawSecPerItem": 130.0,
      "pureSecPerItem": 88.6,
      "setupHours": 10.0,
      "efficiency": 90.0,
      "shrunk": 95.0,
      "lo": 77.5,
      "hi": 112.5,
      "fairTarget": 1.95,
      "verdict": "標準"
    },
    "pack": null
  },
  {
    "name": "片岡達也",
    "role": "staff",
    "pick": {
      "items": 66,
      "minutes": 202,
      "companies": 47,
      "days": 4,
      "itemsPerCompany": 1.4,
      "rawSecPerItem": 183.6,
      "pureSecPerItem": 118.1,
      "setupHours": 1.2,
      "efficiency": 76.9,
      "shrunk": 93.9,
      "lo": 70.9,
      "hi": 116.8,
      "fairTarget": 2.35,
      "verdict": "標準"
    },
    "pack": null
  },
  {
    "name": "廣瀬こずえ",
    "role": "parttime",
    "pick": {
      "items": 838,
      "minutes": 1972,
      "companies": 443,
      "days": 12,
      "itemsPerCompany": 1.89,
      "rawSecPerItem": 141.2,
      "pureSecPerItem": 92.5,
      "setupHours": 11.3,
      "efficiency": 88.0,
      "shrunk": 93.7,
      "lo": 76.3,
      "hi": 111.2,
      "fairTarget": 2.07,
      "verdict": "標準"
    },
    "pack": null
  },
  {
    "name": "森本久美",
    "role": "parttime",
    "pick": {
      "items": 335,
      "minutes": 716,
      "companies": 107,
      "days": 9,
      "itemsPerCompany": 3.13,
      "rawSecPerItem": 128.2,
      "pureSecPerItem": 98.8,
      "setupHours": 2.7,
      "efficiency": 81.9,
      "shrunk": 91.4,
      "lo": 72.3,
      "hi": 110.4,
      "fairTarget": 1.75,
      "verdict": "標準"
    },
    "pack": {
      "items": 970,
      "minutes": 1558,
      "companies": 293,
      "days": 9,
      "itemsPerCompany": 3.31,
      "rawSecPerItem": 96.4,
      "pureSecPerItem": 68.6,
      "setupHours": 7.5,
      "efficiency": 101.0,
      "shrunk": 102.2,
      "lo": 80.4,
      "hi": 124.0,
      "fairTarget": 1.62,
      "verdict": "標準"
    }
  },
  {
    "name": "菊池敬",
    "role": "parttime",
    "pick": {
      "items": 422,
      "minutes": 950,
      "companies": 185,
      "days": 17,
      "itemsPerCompany": 2.28,
      "rawSecPerItem": 135.1,
      "pureSecPerItem": 94.7,
      "setupHours": 4.7,
      "efficiency": 85.9,
      "shrunk": 91.0,
      "lo": 75.5,
      "hi": 106.6,
      "fairTarget": 1.93,
      "verdict": "標準"
    },
    "pack": {
      "items": 1183,
      "minutes": 2943,
      "companies": 367,
      "days": 17,
      "itemsPerCompany": 3.22,
      "rawSecPerItem": 149.3,
      "pureSecPerItem": 120.7,
      "setupHours": 9.4,
      "efficiency": 65.7,
      "shrunk": 69.5,
      "lo": 53.0,
      "hi": 85.9,
      "fairTarget": 1.63,
      "verdict": "要支援"
    }
  },
  {
    "name": "高橋正美",
    "role": "parttime",
    "pick": {
      "items": 1090,
      "minutes": 2510,
      "companies": 428,
      "days": 12,
      "itemsPerCompany": 2.55,
      "rawSecPerItem": 138.2,
      "pureSecPerItem": 102.0,
      "setupHours": 10.9,
      "efficiency": 80.9,
      "shrunk": 89.2,
      "lo": 71.8,
      "hi": 106.7,
      "fairTarget": 1.86,
      "verdict": "標準"
    },
    "pack": null
  },
  {
    "name": "秋草文恵",
    "role": "parttime",
    "pick": {
      "items": 858,
      "minutes": 2094,
      "companies": 391,
      "days": 12,
      "itemsPerCompany": 2.19,
      "rawSecPerItem": 146.4,
      "pureSecPerItem": 104.5,
      "setupHours": 10.0,
      "efficiency": 80.3,
      "shrunk": 88.9,
      "lo": 71.4,
      "hi": 106.3,
      "fairTarget": 1.96,
      "verdict": "標準"
    },
    "pack": null
  },
  {
    "name": "上村和恵",
    "role": "parttime",
    "pick": {
      "items": 1112,
      "minutes": 2665,
      "companies": 465,
      "days": 13,
      "itemsPerCompany": 2.39,
      "rawSecPerItem": 143.8,
      "pureSecPerItem": 105.3,
      "setupHours": 11.9,
      "efficiency": 79.4,
      "shrunk": 87.8,
      "lo": 70.8,
      "hi": 104.9,
      "fairTarget": 1.9,
      "verdict": "標準"
    },
    "pack": null
  },
  {
    "name": "平田学",
    "role": "parttime",
    "pick": {
      "items": 370,
      "minutes": 1225,
      "companies": 148,
      "days": 4,
      "itemsPerCompany": 2.5,
      "rawSecPerItem": 198.6,
      "pureSecPerItem": 161.8,
      "setupHours": 3.8,
      "efficiency": 56.6,
      "shrunk": 86.5,
      "lo": 63.5,
      "hi": 109.5,
      "fairTarget": 1.87,
      "verdict": "標準"
    },
    "pack": null
  },
  {
    "name": "飯田由加里",
    "role": "parttime",
    "pick": {
      "items": 271,
      "minutes": 764,
      "companies": 149,
      "days": 11,
      "itemsPerCompany": 1.82,
      "rawSecPerItem": 169.2,
      "pureSecPerItem": 118.5,
      "setupHours": 3.8,
      "efficiency": 74.6,
      "shrunk": 85.9,
      "lo": 67.9,
      "hi": 103.8,
      "fairTarget": 2.1,
      "verdict": "標準"
    },
    "pack": {
      "items": 1061,
      "minutes": 1466,
      "companies": 433,
      "days": 12,
      "itemsPerCompany": 2.45,
      "rawSecPerItem": 82.9,
      "pureSecPerItem": 45.3,
      "setupHours": 11.1,
      "efficiency": 129.2,
      "shrunk": 126.8,
      "lo": 107.5,
      "hi": 146.0,
      "fairTarget": 1.78,
      "verdict": "標準"
    }
  }
];

export const timeMix: MixSlice[] = [
  {
    "label": "段取り",
    "detail": "リスト確認・伝票挟み（1社ごと）",
    "hours": 233.2
  },
  {
    "label": "移動",
    "detail": "棚まで往復（1件ごと）",
    "hours": 223.1
  },
  {
    "label": "ピック",
    "detail": "棚から取ってカゴへ（1件ごと・唯一の付加価値）",
    "hours": 223.1
  }
];

export const totals = {
  "pickItems": 21249,
  "pickMinutes": 40783,
  "pickCompanies": 9114,
  "pickEff": 100.0,
  "packItems": 24467,
  "packMinutes": 39187,
  "packCompanies": 7069,
  "packEff": 100.0,
  "totalItems": 45716,
  "totalHours": 1332.8,
  "setupHours": 414.0,
  "setupRatio": 31.1,
  "pickSetupRatio": 34.3,
  "avgEff": 100.0,
  "secPerItem": 105.0,
  "headcount": 29
} as const;

export const deltas = {
  "items": 29.4,
  "hours": 23.8,
  "eff": 6.7,
  "setup": 9.5
} as const;

/**
 * PK実働時間の記録が欠落している区間。チャート上で明示する。
 * 欠落が無い月は null になるので、参照側は必ず null を確認すること。
 */
export const recordGap: { start: string; end: string; note: string } | null = null;

export const dataWindow = {
  "start": "2026-04-01",
  "end": "2026-04-30",
  "completeThrough": "2026-04-30",
  "completeDays": 21,
  "totalDays": 21
} as const;
