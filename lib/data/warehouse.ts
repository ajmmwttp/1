// 自動生成 — mkwarehouse.py が dash.json から書き出す。手で編集しない。
// 出典: 月次実績表を IE 標準時間モデル T = a×企業数 + b×件数 で評価したもの。
//   ピッキング a=112.4 秒/社, b=66.2 秒/件
//   梱包       a=76.2 秒/社, b=74.1 秒/件
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
  pick: { a: 112.4, b: 66.2 },
  pack: { a: 76.2, b: 74.1 },
} as const;

/**
 * 散布図①②の相関。① は素の秒/件、② は段取りを除いた純速度で、
 * どちらも横軸は 社/件（リストの組み方）。
 */
export const scatterStats = {
  raw: {
  "r": 0.491,
  "p": 0.011,
  "n": 26
},
  pure: {
  "r": 0.063,
  "p": 0.761,
  "n": 26
},
} as const;

export const days: DayPoint[] = [
  {
    "date": "2026-04-01",
    "pickItems": 1139,
    "pickMinutes": 1971,
    "pickCompanies": 491,
    "pickEff": 110.5,
    "pickSetup": 920,
    "packItems": 1224,
    "packMinutes": 1866,
    "packCompanies": 316,
    "packEff": 102.5,
    "packSetup": 402,
    "setupMinutes": 1322,
    "totalItems": 2363,
    "totalHours": 64.0
  },
  {
    "date": "2026-04-02",
    "pickItems": 1159,
    "pickMinutes": 2021,
    "pickCompanies": 493,
    "pickEff": 109.0,
    "pickSetup": 924,
    "packItems": 1139,
    "packMinutes": 1825,
    "packCompanies": 312,
    "packEff": 98.8,
    "packSetup": 397,
    "setupMinutes": 1321,
    "totalItems": 2298,
    "totalHours": 64.1
  },
  {
    "date": "2026-04-03",
    "pickItems": 1330,
    "pickMinutes": 1905,
    "pickCompanies": 528,
    "pickEff": 129.0,
    "pickSetup": 989,
    "packItems": 1339,
    "packMinutes": 1798,
    "packCompanies": 390,
    "packEff": 119.5,
    "packSetup": 495,
    "setupMinutes": 1484,
    "totalItems": 2669,
    "totalHours": 61.7
  },
  {
    "date": "2026-04-06",
    "pickItems": 1351,
    "pickMinutes": 2428,
    "pickCompanies": 576,
    "pickEff": 105.8,
    "pickSetup": 1079,
    "packItems": 1412,
    "packMinutes": 2216,
    "packCompanies": 412,
    "packEff": 102.3,
    "packSetup": 524,
    "setupMinutes": 1603,
    "totalItems": 2763,
    "totalHours": 77.4
  },
  {
    "date": "2026-04-07",
    "pickItems": 1217,
    "pickMinutes": 2114,
    "pickCompanies": 494,
    "pickEff": 107.3,
    "pickSetup": 925,
    "packItems": 1260,
    "packMinutes": 1875,
    "packCompanies": 353,
    "packEff": 106.9,
    "packSetup": 448,
    "setupMinutes": 1373,
    "totalItems": 2477,
    "totalHours": 66.5
  },
  {
    "date": "2026-04-08",
    "pickItems": 1371,
    "pickMinutes": 2064,
    "pickCompanies": 580,
    "pickEff": 125.9,
    "pickSetup": 1086,
    "packItems": 1322,
    "packMinutes": 2027,
    "packCompanies": 347,
    "packEff": 102.3,
    "packSetup": 440,
    "setupMinutes": 1526,
    "totalItems": 2693,
    "totalHours": 68.2
  },
  {
    "date": "2026-04-09",
    "pickItems": 1137,
    "pickMinutes": 1995,
    "pickCompanies": 489,
    "pickEff": 108.8,
    "pickSetup": 916,
    "packItems": 1215,
    "packMinutes": 1690,
    "packCompanies": 360,
    "packEff": 115.8,
    "packSetup": 457,
    "setupMinutes": 1373,
    "totalItems": 2352,
    "totalHours": 61.4
  },
  {
    "date": "2026-04-10",
    "pickItems": 770,
    "pickMinutes": 1544,
    "pickCompanies": 329,
    "pickEff": 94.9,
    "pickSetup": 616,
    "packItems": 1225,
    "packMinutes": 1942,
    "packCompanies": 355,
    "packEff": 101.1,
    "packSetup": 451,
    "setupMinutes": 1067,
    "totalItems": 1995,
    "totalHours": 58.1
  },
  {
    "date": "2026-04-13",
    "pickItems": 641,
    "pickMinutes": 1563,
    "pickCompanies": 277,
    "pickEff": 78.5,
    "pickSetup": 519,
    "packItems": 1471,
    "packMinutes": 2591,
    "packCompanies": 418,
    "packEff": 90.6,
    "packSetup": 530,
    "setupMinutes": 1049,
    "totalItems": 2112,
    "totalHours": 69.2
  },
  {
    "date": "2026-04-14",
    "pickItems": 692,
    "pickMinutes": 1563,
    "pickCompanies": 291,
    "pickEff": 83.7,
    "pickSetup": 545,
    "packItems": 1031,
    "packMinutes": 1913,
    "packCompanies": 309,
    "packEff": 87.1,
    "packSetup": 392,
    "setupMinutes": 937,
    "totalItems": 1723,
    "totalHours": 57.9
  },
  {
    "date": "2026-04-15",
    "pickItems": 805,
    "pickMinutes": 1794,
    "pickCompanies": 344,
    "pickEff": 85.5,
    "pickSetup": 645,
    "packItems": 863,
    "packMinutes": 1416,
    "packCompanies": 254,
    "packEff": 98.1,
    "packSetup": 323,
    "setupMinutes": 968,
    "totalItems": 1668,
    "totalHours": 53.5
  },
  {
    "date": "2026-04-16",
    "pickItems": 571,
    "pickMinutes": 1335,
    "pickCompanies": 256,
    "pickEff": 83.1,
    "pickSetup": 479,
    "packItems": 1011,
    "packMinutes": 1657,
    "packCompanies": 301,
    "packEff": 98.4,
    "packSetup": 382,
    "setupMinutes": 861,
    "totalItems": 1582,
    "totalHours": 49.9
  },
  {
    "date": "2026-04-17",
    "pickItems": 532,
    "pickMinutes": 1077,
    "pickCompanies": 223,
    "pickEff": 93.3,
    "pickSetup": 418,
    "packItems": 1031,
    "packMinutes": 1616,
    "packCompanies": 303,
    "packEff": 102.6,
    "packSetup": 384,
    "setupMinutes": 802,
    "totalItems": 1563,
    "totalHours": 44.9
  },
  {
    "date": "2026-04-20",
    "pickItems": 649,
    "pickMinutes": 1717,
    "pickCompanies": 293,
    "pickEff": 73.7,
    "pickSetup": 550,
    "packItems": 905,
    "packMinutes": 1503,
    "packCompanies": 269,
    "packEff": 97.1,
    "packSetup": 342,
    "setupMinutes": 892,
    "totalItems": 1554,
    "totalHours": 53.7
  },
  {
    "date": "2026-04-21",
    "pickItems": 1107,
    "pickMinutes": 2256,
    "pickCompanies": 490,
    "pickEff": 94.8,
    "pickSetup": 918,
    "packItems": 1127,
    "packMinutes": 1907,
    "packCompanies": 340,
    "packEff": 95.6,
    "packSetup": 431,
    "setupMinutes": 1349,
    "totalItems": 2234,
    "totalHours": 69.4
  },
  {
    "date": "2026-04-22",
    "pickItems": 891,
    "pickMinutes": 1786,
    "pickCompanies": 384,
    "pickEff": 95.3,
    "pickSetup": 720,
    "packItems": 926,
    "packMinutes": 1520,
    "packCompanies": 255,
    "packEff": 96.5,
    "packSetup": 323,
    "setupMinutes": 1043,
    "totalItems": 1817,
    "totalHours": 55.1
  },
  {
    "date": "2026-04-23",
    "pickItems": 829,
    "pickMinutes": 1679,
    "pickCompanies": 349,
    "pickEff": 93.4,
    "pickSetup": 653,
    "packItems": 1001,
    "packMinutes": 1767,
    "packCompanies": 291,
    "packEff": 90.9,
    "packSetup": 369,
    "setupMinutes": 1022,
    "totalItems": 1830,
    "totalHours": 57.4
  },
  {
    "date": "2026-04-24",
    "pickItems": 0,
    "pickMinutes": 0,
    "pickCompanies": 0,
    "pickEff": null,
    "pickSetup": 0,
    "packItems": 1318,
    "packMinutes": 2005,
    "packCompanies": 389,
    "packEff": 105.8,
    "packSetup": 494,
    "setupMinutes": 494,
    "totalItems": 1318,
    "totalHours": 33.4
  },
  {
    "date": "2026-04-27",
    "pickItems": 0,
    "pickMinutes": 0,
    "pickCompanies": 0,
    "pickEff": null,
    "pickSetup": 0,
    "packItems": 1305,
    "packMinutes": 2486,
    "packCompanies": 381,
    "packEff": 84.3,
    "packSetup": 483,
    "setupMinutes": 483,
    "totalItems": 1305,
    "totalHours": 41.4
  },
  {
    "date": "2026-04-28",
    "pickItems": 0,
    "pickMinutes": 0,
    "pickCompanies": 0,
    "pickEff": null,
    "pickSetup": 0,
    "packItems": 1306,
    "packMinutes": 1830,
    "packCompanies": 379,
    "packEff": 114.4,
    "packSetup": 481,
    "setupMinutes": 481,
    "totalItems": 1306,
    "totalHours": 30.5
  },
  {
    "date": "2026-04-30",
    "pickItems": 0,
    "pickMinutes": 0,
    "pickCompanies": 0,
    "pickEff": null,
    "pickSetup": 0,
    "packItems": 1018,
    "packMinutes": 1697,
    "packCompanies": 295,
    "packEff": 96.2,
    "packSetup": 374,
    "setupMinutes": 374,
    "totalItems": 1018,
    "totalHours": 28.3
  }
];

export const workers: Worker[] = [
  {
    "name": "本吉有美子",
    "role": "parttime",
    "pick": {
      "items": 1239,
      "minutes": 1643,
      "companies": 521,
      "days": 15,
      "itemsPerCompany": 2.38,
      "rawSecPerItem": 79.6,
      "pureSecPerItem": 32.3,
      "setupHours": 16.3,
      "efficiency": 142.6,
      "shrunk": 131.7,
      "lo": 116.2,
      "hi": 147.1,
      "fairTarget": 1.89,
      "verdict": "上位"
    },
    "pack": {
      "items": 2493,
      "minutes": 2599,
      "companies": 653,
      "days": 20,
      "itemsPerCompany": 3.82,
      "rawSecPerItem": 62.6,
      "pureSecPerItem": 42.6,
      "setupHours": 13.8,
      "efficiency": 150.4,
      "shrunk": 147.9,
      "lo": 133.8,
      "hi": 162.0,
      "fairTarget": 1.57,
      "verdict": "上位"
    }
  },
  {
    "name": "大江美記子",
    "role": "parttime",
    "pick": {
      "items": 773,
      "minutes": 1235,
      "companies": 379,
      "days": 13,
      "itemsPerCompany": 2.04,
      "rawSecPerItem": 95.9,
      "pureSecPerItem": 40.8,
      "setupHours": 11.8,
      "efficiency": 126.5,
      "shrunk": 119.4,
      "lo": 103.1,
      "hi": 135.7,
      "fairTarget": 2.02,
      "verdict": "標準"
    },
    "pack": {
      "items": 2616,
      "minutes": 3060,
      "companies": 675,
      "days": 19,
      "itemsPerCompany": 3.88,
      "rawSecPerItem": 70.2,
      "pureSecPerItem": 50.5,
      "setupHours": 14.3,
      "efficiency": 133.6,
      "shrunk": 132.0,
      "lo": 117.6,
      "hi": 146.5,
      "fairTarget": 1.56,
      "verdict": "上位"
    }
  },
  {
    "name": "鈴木香織",
    "role": "parttime",
    "pick": {
      "items": 210,
      "minutes": 345,
      "companies": 116,
      "days": 8,
      "itemsPerCompany": 1.81,
      "rawSecPerItem": 98.6,
      "pureSecPerItem": 36.3,
      "setupHours": 3.6,
      "efficiency": 130.3,
      "shrunk": 119.0,
      "lo": 100.0,
      "hi": 138.0,
      "fairTarget": 2.14,
      "verdict": "標準"
    },
    "pack": {
      "items": 1050,
      "minutes": 1848,
      "companies": 380,
      "days": 12,
      "itemsPerCompany": 2.76,
      "rawSecPerItem": 105.6,
      "pureSecPerItem": 78.0,
      "setupHours": 8.0,
      "efficiency": 96.3,
      "shrunk": 97.5,
      "lo": 79.7,
      "hi": 115.4,
      "fairTarget": 1.69,
      "verdict": "標準"
    }
  },
  {
    "name": "晩田恵美",
    "role": "parttime",
    "pick": {
      "items": 656,
      "minutes": 841,
      "companies": 173,
      "days": 10,
      "itemsPerCompany": 3.8,
      "rawSecPerItem": 76.9,
      "pureSecPerItem": 47.3,
      "setupHours": 5.4,
      "efficiency": 124.6,
      "shrunk": 116.8,
      "lo": 99.0,
      "hi": 134.6,
      "fairTarget": 1.6,
      "verdict": "標準"
    },
    "pack": {
      "items": 2881,
      "minutes": 4007,
      "companies": 988,
      "days": 19,
      "itemsPerCompany": 2.92,
      "rawSecPerItem": 83.5,
      "pureSecPerItem": 57.3,
      "setupHours": 20.9,
      "efficiency": 120.1,
      "shrunk": 119.4,
      "lo": 105.0,
      "hi": 133.8,
      "fairTarget": 1.67,
      "verdict": "標準"
    }
  },
  {
    "name": "澤田凌",
    "role": "staff",
    "pick": {
      "items": 611,
      "minutes": 1115,
      "companies": 382,
      "days": 9,
      "itemsPerCompany": 1.6,
      "rawSecPerItem": 109.5,
      "pureSecPerItem": 39.3,
      "setupHours": 11.9,
      "efficiency": 124.6,
      "shrunk": 116.3,
      "lo": 97.9,
      "hi": 134.7,
      "fairTarget": 2.27,
      "verdict": "標準"
    },
    "pack": {
      "items": 634,
      "minutes": 1530,
      "companies": 211,
      "days": 10,
      "itemsPerCompany": 3.01,
      "rawSecPerItem": 144.8,
      "pureSecPerItem": 119.5,
      "setupHours": 4.5,
      "efficiency": 68.7,
      "shrunk": 73.3,
      "lo": 53.9,
      "hi": 92.6,
      "fairTarget": 1.66,
      "verdict": "要支援"
    }
  },
  {
    "name": "佐藤辰成",
    "role": "staff",
    "pick": {
      "items": 583,
      "minutes": 740,
      "companies": 129,
      "days": 8,
      "itemsPerCompany": 4.52,
      "rawSecPerItem": 76.2,
      "pureSecPerItem": 51.3,
      "setupHours": 4.0,
      "efficiency": 119.6,
      "shrunk": 112.8,
      "lo": 93.8,
      "hi": 131.8,
      "fairTarget": 1.52,
      "verdict": "標準"
    },
    "pack": {
      "items": 266,
      "minutes": 265,
      "companies": 46,
      "days": 6,
      "itemsPerCompany": 5.8,
      "rawSecPerItem": 59.8,
      "pureSecPerItem": 46.6,
      "setupHours": 1.0,
      "efficiency": 145.9,
      "shrunk": 139.4,
      "lo": 115.3,
      "hi": 163.5,
      "fairTarget": 1.45,
      "verdict": "上位"
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
      "pureSecPerItem": 48.0,
      "setupHours": 0.9,
      "efficiency": 120.0,
      "shrunk": 109.1,
      "lo": 85.2,
      "hi": 132.9,
      "fairTarget": 1.82,
      "verdict": "標準"
    },
    "pack": {
      "items": 375,
      "minutes": 730,
      "companies": 106,
      "days": 4,
      "itemsPerCompany": 3.54,
      "rawSecPerItem": 116.8,
      "pureSecPerItem": 95.3,
      "setupHours": 2.2,
      "efficiency": 81.9,
      "shrunk": 88.5,
      "lo": 60.2,
      "hi": 116.8,
      "fairTarget": 1.59,
      "verdict": "標準"
    }
  },
  {
    "name": "河野忠",
    "role": "staff",
    "pick": {
      "items": 263,
      "minutes": 450,
      "companies": 116,
      "days": 5,
      "itemsPerCompany": 2.27,
      "rawSecPerItem": 102.7,
      "pureSecPerItem": 53.1,
      "setupHours": 3.6,
      "efficiency": 112.8,
      "shrunk": 107.8,
      "lo": 86.2,
      "hi": 129.3,
      "fairTarget": 1.93,
      "verdict": "標準"
    },
    "pack": {
      "items": 593,
      "minutes": 685,
      "companies": 71,
      "days": 7,
      "itemsPerCompany": 8.3,
      "rawSecPerItem": 69.3,
      "pureSecPerItem": 60.1,
      "setupHours": 1.5,
      "efficiency": 120.2,
      "shrunk": 118.4,
      "lo": 95.8,
      "hi": 141.0,
      "fairTarget": 1.39,
      "verdict": "標準"
    }
  },
  {
    "name": "後藤克行",
    "role": "staff",
    "pick": {
      "items": 1579,
      "minutes": 2975,
      "companies": 754,
      "days": 16,
      "itemsPerCompany": 2.09,
      "rawSecPerItem": 113.0,
      "pureSecPerItem": 59.3,
      "setupHours": 23.6,
      "efficiency": 106.1,
      "shrunk": 105.4,
      "lo": 90.2,
      "hi": 120.5,
      "fairTarget": 2.0,
      "verdict": "標準"
    },
    "pack": {
      "items": 1421,
      "minutes": 2760,
      "companies": 372,
      "days": 20,
      "itemsPerCompany": 3.82,
      "rawSecPerItem": 116.5,
      "pureSecPerItem": 96.6,
      "setupHours": 7.9,
      "efficiency": 80.7,
      "shrunk": 82.4,
      "lo": 68.3,
      "hi": 96.5,
      "fairTarget": 1.57,
      "verdict": "要支援"
    }
  },
  {
    "name": "佐々木千恵",
    "role": "staff",
    "pick": {
      "items": 588,
      "minutes": 905,
      "companies": 165,
      "days": 8,
      "itemsPerCompany": 3.57,
      "rawSecPerItem": 92.3,
      "pureSecPerItem": 60.8,
      "setupHours": 5.1,
      "efficiency": 105.8,
      "shrunk": 104.8,
      "lo": 85.8,
      "hi": 123.8,
      "fairTarget": 1.63,
      "verdict": "標準"
    },
    "pack": {
      "items": 890,
      "minutes": 770,
      "companies": 191,
      "days": 7,
      "itemsPerCompany": 4.65,
      "rawSecPerItem": 51.9,
      "pureSecPerItem": 35.5,
      "setupHours": 4.1,
      "efficiency": 174.3,
      "shrunk": 164.1,
      "lo": 141.6,
      "hi": 186.7,
      "fairTarget": 1.51,
      "verdict": "上位"
    }
  },
  {
    "name": "高橋佐織",
    "role": "parttime",
    "pick": {
      "items": 888,
      "minutes": 1605,
      "companies": 377,
      "days": 13,
      "itemsPerCompany": 2.35,
      "rawSecPerItem": 108.4,
      "pureSecPerItem": 60.7,
      "setupHours": 11.8,
      "efficiency": 105.1,
      "shrunk": 104.6,
      "lo": 88.3,
      "hi": 120.9,
      "fairTarget": 1.9,
      "verdict": "標準"
    },
    "pack": {
      "items": 2422,
      "minutes": 4132,
      "companies": 699,
      "days": 20,
      "itemsPerCompany": 3.46,
      "rawSecPerItem": 102.4,
      "pureSecPerItem": 80.4,
      "setupHours": 14.8,
      "efficiency": 93.9,
      "shrunk": 94.8,
      "lo": 80.7,
      "hi": 108.9,
      "fairTarget": 1.6,
      "verdict": "要支援"
    }
  },
  {
    "name": "山本祥吉",
    "role": "staff",
    "pick": {
      "items": 1776,
      "minutes": 3029,
      "companies": 614,
      "days": 16,
      "itemsPerCompany": 2.89,
      "rawSecPerItem": 102.3,
      "pureSecPerItem": 63.5,
      "setupHours": 19.2,
      "efficiency": 102.7,
      "shrunk": 102.9,
      "lo": 87.7,
      "hi": 118.0,
      "fairTarget": 1.75,
      "verdict": "標準"
    },
    "pack": {
      "items": 1548,
      "minutes": 2828,
      "companies": 393,
      "days": 20,
      "itemsPerCompany": 3.94,
      "rawSecPerItem": 109.6,
      "pureSecPerItem": 90.3,
      "setupHours": 8.3,
      "efficiency": 85.3,
      "shrunk": 86.7,
      "lo": 72.6,
      "hi": 100.8,
      "fairTarget": 1.56,
      "verdict": "要支援"
    }
  },
  {
    "name": "森田美加",
    "role": "parttime",
    "pick": {
      "items": 191,
      "minutes": 385,
      "companies": 95,
      "days": 4,
      "itemsPerCompany": 2.01,
      "rawSecPerItem": 120.9,
      "pureSecPerItem": 65.0,
      "setupHours": 3.0,
      "efficiency": 101.0,
      "shrunk": 102.4,
      "lo": 79.9,
      "hi": 125.0,
      "fairTarget": 2.04,
      "verdict": "標準"
    },
    "pack": {
      "items": 630,
      "minutes": 1945,
      "companies": 187,
      "days": 10,
      "itemsPerCompany": 3.37,
      "rawSecPerItem": 185.2,
      "pureSecPerItem": 162.6,
      "setupHours": 4.0,
      "efficiency": 52.2,
      "shrunk": 58.7,
      "lo": 39.4,
      "hi": 78.1,
      "fairTarget": 1.61,
      "verdict": "要支援"
    }
  },
  {
    "name": "石戸谷亜子",
    "role": "parttime",
    "pick": {
      "items": 736,
      "minutes": 1298,
      "companies": 245,
      "days": 7,
      "itemsPerCompany": 3.0,
      "rawSecPerItem": 105.8,
      "pureSecPerItem": 68.3,
      "setupHours": 7.7,
      "efficiency": 98.0,
      "shrunk": 100.4,
      "lo": 80.7,
      "hi": 120.2,
      "fairTarget": 1.73,
      "verdict": "標準"
    },
    "pack": null
  },
  {
    "name": "北田倫子",
    "role": "parttime",
    "pick": {
      "items": 321,
      "minutes": 725,
      "companies": 193,
      "days": 11,
      "itemsPerCompany": 1.67,
      "rawSecPerItem": 135.5,
      "pureSecPerItem": 68.0,
      "setupHours": 6.0,
      "efficiency": 98.7,
      "shrunk": 100.3,
      "lo": 83.1,
      "hi": 117.5,
      "fairTarget": 2.23,
      "verdict": "標準"
    },
    "pack": {
      "items": 1442,
      "minutes": 1758,
      "companies": 472,
      "days": 13,
      "itemsPerCompany": 3.06,
      "rawSecPerItem": 73.1,
      "pureSecPerItem": 48.2,
      "setupHours": 10.0,
      "efficiency": 135.4,
      "shrunk": 133.0,
      "lo": 115.8,
      "hi": 150.2,
      "fairTarget": 1.65,
      "verdict": "上位"
    }
  },
  {
    "name": "中納沙織",
    "role": "staff",
    "pick": {
      "items": 669,
      "minutes": 1435,
      "companies": 325,
      "days": 5,
      "itemsPerCompany": 2.06,
      "rawSecPerItem": 128.7,
      "pureSecPerItem": 74.0,
      "setupHours": 10.2,
      "efficiency": 93.9,
      "shrunk": 99.0,
      "lo": 77.5,
      "hi": 120.5,
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
      "pureSecPerItem": 114.3,
      "setupHours": 0.8,
      "efficiency": 68.4,
      "shrunk": 80.6,
      "lo": 49.2,
      "hi": 112.0,
      "fairTarget": 1.45,
      "verdict": "標準"
    }
  },
  {
    "name": "木村千鶴",
    "role": "parttime",
    "pick": {
      "items": 546,
      "minutes": 1161,
      "companies": 268,
      "days": 14,
      "itemsPerCompany": 2.04,
      "rawSecPerItem": 127.6,
      "pureSecPerItem": 72.4,
      "setupHours": 8.4,
      "efficiency": 95.1,
      "shrunk": 97.5,
      "lo": 81.7,
      "hi": 113.4,
      "fairTarget": 2.02,
      "verdict": "標準"
    },
    "pack": {
      "items": 1750,
      "minutes": 3788,
      "companies": 452,
      "days": 20,
      "itemsPerCompany": 3.87,
      "rawSecPerItem": 129.9,
      "pureSecPerItem": 110.2,
      "setupHours": 9.6,
      "efficiency": 72.2,
      "shrunk": 74.4,
      "lo": 60.3,
      "hi": 88.5,
      "fairTarget": 1.56,
      "verdict": "要支援"
    }
  },
  {
    "name": "廣瀬こずえ",
    "role": "parttime",
    "pick": {
      "items": 711,
      "minutes": 1653,
      "companies": 376,
      "days": 10,
      "itemsPerCompany": 1.89,
      "rawSecPerItem": 139.5,
      "pureSecPerItem": 80.1,
      "setupHours": 11.7,
      "efficiency": 90.1,
      "shrunk": 95.0,
      "lo": 77.2,
      "hi": 112.7,
      "fairTarget": 2.09,
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
      "pureSecPerItem": 103.6,
      "setupHours": 1.5,
      "efficiency": 79.6,
      "shrunk": 93.7,
      "lo": 71.1,
      "hi": 116.3,
      "fairTarget": 2.44,
      "verdict": "標準"
    },
    "pack": null
  },
  {
    "name": "菊池敬",
    "role": "parttime",
    "pick": {
      "items": 361,
      "minutes": 784,
      "companies": 158,
      "days": 14,
      "itemsPerCompany": 2.28,
      "rawSecPerItem": 130.3,
      "pureSecPerItem": 81.0,
      "setupHours": 4.9,
      "efficiency": 88.6,
      "shrunk": 93.0,
      "lo": 77.1,
      "hi": 108.8,
      "fairTarget": 1.92,
      "verdict": "標準"
    },
    "pack": {
      "items": 1183,
      "minutes": 2943,
      "companies": 367,
      "days": 17,
      "itemsPerCompany": 3.22,
      "rawSecPerItem": 149.3,
      "pureSecPerItem": 125.6,
      "setupHours": 7.8,
      "efficiency": 65.5,
      "shrunk": 68.6,
      "lo": 53.3,
      "hi": 83.8,
      "fairTarget": 1.63,
      "verdict": "要支援"
    }
  },
  {
    "name": "向井ひかり",
    "role": "parttime",
    "pick": {
      "items": 585,
      "minutes": 1340,
      "companies": 263,
      "days": 9,
      "itemsPerCompany": 2.23,
      "rawSecPerItem": 137.4,
      "pureSecPerItem": 86.9,
      "setupHours": 8.2,
      "efficiency": 84.9,
      "shrunk": 92.2,
      "lo": 73.8,
      "hi": 110.5,
      "fairTarget": 1.94,
      "verdict": "標準"
    },
    "pack": null
  },
  {
    "name": "飯田由加里",
    "role": "parttime",
    "pick": {
      "items": 168,
      "minutes": 458,
      "companies": 92,
      "days": 8,
      "itemsPerCompany": 1.82,
      "rawSecPerItem": 163.6,
      "pureSecPerItem": 101.8,
      "setupHours": 2.9,
      "efficiency": 78.3,
      "shrunk": 88.8,
      "lo": 69.8,
      "hi": 107.9,
      "fairTarget": 2.13,
      "verdict": "標準"
    },
    "pack": {
      "items": 1061,
      "minutes": 1466,
      "companies": 433,
      "days": 12,
      "itemsPerCompany": 2.45,
      "rawSecPerItem": 82.9,
      "pureSecPerItem": 51.8,
      "setupHours": 9.2,
      "efficiency": 126.9,
      "shrunk": 125.2,
      "lo": 107.3,
      "hi": 143.0,
      "fairTarget": 1.75,
      "verdict": "標準"
    }
  },
  {
    "name": "高橋正美",
    "role": "parttime",
    "pick": {
      "items": 915,
      "minutes": 2098,
      "companies": 359,
      "days": 10,
      "itemsPerCompany": 2.55,
      "rawSecPerItem": 137.6,
      "pureSecPerItem": 93.4,
      "setupHours": 11.2,
      "efficiency": 80.2,
      "shrunk": 88.7,
      "lo": 70.9,
      "hi": 106.5,
      "fairTarget": 1.84,
      "verdict": "標準"
    },
    "pack": null
  },
  {
    "name": "秋草文恵",
    "role": "parttime",
    "pick": {
      "items": 628,
      "minutes": 1552,
      "companies": 286,
      "days": 9,
      "itemsPerCompany": 2.19,
      "rawSecPerItem": 148.3,
      "pureSecPerItem": 97.1,
      "setupHours": 8.9,
      "efficiency": 79.2,
      "shrunk": 88.7,
      "lo": 70.3,
      "hi": 107.1,
      "fairTarget": 1.96,
      "verdict": "標準"
    },
    "pack": null
  },
  {
    "name": "上村和恵",
    "role": "parttime",
    "pick": {
      "items": 889,
      "minutes": 2250,
      "companies": 372,
      "days": 10,
      "itemsPerCompany": 2.39,
      "rawSecPerItem": 151.9,
      "pureSecPerItem": 104.9,
      "setupHours": 11.6,
      "efficiency": 74.5,
      "shrunk": 85.1,
      "lo": 67.4,
      "hi": 102.9,
      "fairTarget": 1.89,
      "verdict": "要支援"
    },
    "pack": null
  },
  {
    "name": "森本久美",
    "role": "parttime",
    "pick": {
      "items": 160,
      "minutes": 468,
      "companies": 51,
      "days": 7,
      "itemsPerCompany": 3.13,
      "rawSecPerItem": 175.5,
      "pureSecPerItem": 139.6,
      "setupHours": 1.6,
      "efficiency": 58.2,
      "shrunk": 78.7,
      "lo": 58.9,
      "hi": 98.4,
      "fairTarget": 1.7,
      "verdict": "要支援"
    },
    "pack": {
      "items": 970,
      "minutes": 1558,
      "companies": 293,
      "days": 9,
      "itemsPerCompany": 3.31,
      "rawSecPerItem": 96.4,
      "pureSecPerItem": 73.4,
      "setupHours": 6.2,
      "efficiency": 100.8,
      "shrunk": 101.8,
      "lo": 81.5,
      "hi": 122.1,
      "fairTarget": 1.62,
      "verdict": "標準"
    }
  }
];

export const timeMix: MixSlice[] = [
  {
    "label": "段取り",
    "detail": "リスト確認・伝票挟み（1社ごと）",
    "hours": 215.0
  },
  {
    "label": "移動",
    "detail": "棚まで往復（1件ごと）",
    "hours": 148.9
  },
  {
    "label": "ピック",
    "detail": "棚から取ってカゴへ（1件ごと・唯一の付加価値）",
    "hours": 148.9
  }
];

export const totals = {
  "pickItems": 16191,
  "pickMinutes": 30812,
  "pickCompanies": 6887,
  "pickEff": 99.9,
  "packItems": 24449,
  "packMinutes": 39147,
  "packCompanies": 7027,
  "packEff": 99.9,
  "totalItems": 40640,
  "totalHours": 1166.0,
  "setupHours": 363.8,
  "setupRatio": 31.2,
  "pickSetupRatio": 41.9,
  "avgEff": 99.9,
  "secPerItem": 103.3,
  "headcount": 26
} as const;

export const deltas = {
  "items": -11.2,
  "hours": -18.5,
  "eff": 6.5,
  "setup": -2.1
} as const;

/** PK実働時間の記録が欠落している区間。チャート上で明示する。 */
export const recordGap = {
  "start": "2026-04-24",
  "end": "2026-04-30",
  "note": "PK実働時間の記録が欠落している期間"
} as const;

export const dataWindow = {
  "start": "2026-04-01",
  "end": "2026-04-30",
  "completeThrough": "2026-04-23",
  "completeDays": 17,
  "totalDays": 21
} as const;
