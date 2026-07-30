// 自動生成 — 2026年4月の実績（ピッキング／梱包）。
// 出典: 月次実績表を IE 標準時間モデル T = a×企業数 + b×件数 で評価したもの。
//   ピッキング a=112.8 秒/社, b=65.7 秒/件
//   梱包       a=50.0  秒/社（暫定）, b=81.8 秒/件

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

export const days: DayPoint[] = [
  {
    "date": "2026-04-01",
    "pickItems": 1032,
    "pickMinutes": 2253,
    "pickCompanies": 440,
    "pickEff": 86.8,
    "pickSetup": 826,
    "packItems": 1394,
    "packMinutes": 1927,
    "packCompanies": 398,
    "packEff": 115.8,
    "packSetup": 332,
    "setupMinutes": 1158,
    "totalItems": 2426,
    "totalHours": 69.7
  },
  {
    "date": "2026-04-02",
    "pickItems": 839,
    "pickMinutes": 2007,
    "pickCompanies": 358,
    "pickEff": 79.3,
    "pickSetup": 672,
    "packItems": 1088,
    "packMinutes": 1822,
    "packCompanies": 310,
    "packEff": 95.6,
    "packSetup": 259,
    "setupMinutes": 931,
    "totalItems": 1927,
    "totalHours": 63.8
  },
  {
    "date": "2026-04-03",
    "pickItems": 963,
    "pickMinutes": 1841,
    "pickCompanies": 410,
    "pickEff": 99.2,
    "pickSetup": 771,
    "packItems": 1284,
    "packMinutes": 1795,
    "packCompanies": 366,
    "packEff": 114.5,
    "packSetup": 305,
    "setupMinutes": 1076,
    "totalItems": 2247,
    "totalHours": 60.6
  },
  {
    "date": "2026-04-06",
    "pickItems": 1037,
    "pickMinutes": 2443,
    "pickCompanies": 442,
    "pickEff": 80.5,
    "pickSetup": 830,
    "packItems": 1360,
    "packMinutes": 2212,
    "packCompanies": 388,
    "packEff": 98.5,
    "packSetup": 323,
    "setupMinutes": 1153,
    "totalItems": 2397,
    "totalHours": 77.6
  },
  {
    "date": "2026-04-07",
    "pickItems": 918,
    "pickMinutes": 1995,
    "pickCompanies": 391,
    "pickEff": 87.3,
    "pickSetup": 735,
    "packItems": 1203,
    "packMinutes": 1871,
    "packCompanies": 343,
    "packEff": 103.0,
    "packSetup": 286,
    "setupMinutes": 1021,
    "totalItems": 2121,
    "totalHours": 64.4
  },
  {
    "date": "2026-04-08",
    "pickItems": 1055,
    "pickMinutes": 1995,
    "pickCompanies": 449,
    "pickEff": 100.3,
    "pickSetup": 845,
    "packItems": 1377,
    "packMinutes": 2033,
    "packCompanies": 393,
    "packEff": 108.5,
    "packSetup": 328,
    "setupMinutes": 1173,
    "totalItems": 2432,
    "totalHours": 67.1
  },
  {
    "date": "2026-04-09",
    "pickItems": 881,
    "pickMinutes": 1928,
    "pickCompanies": 375,
    "pickEff": 86.6,
    "pickSetup": 706,
    "packItems": 1160,
    "packMinutes": 1687,
    "packCompanies": 331,
    "packEff": 110.2,
    "packSetup": 276,
    "setupMinutes": 982,
    "totalItems": 2041,
    "totalHours": 60.2
  },
  {
    "date": "2026-04-10",
    "pickItems": 566,
    "pickMinutes": 1492,
    "pickCompanies": 241,
    "pickEff": 71.9,
    "pickSetup": 453,
    "packItems": 1201,
    "packMinutes": 1938,
    "packCompanies": 343,
    "packEff": 99.3,
    "packSetup": 286,
    "setupMinutes": 739,
    "totalItems": 1767,
    "totalHours": 57.2
  },
  {
    "date": "2026-04-13",
    "pickItems": 464,
    "pickMinutes": 1511,
    "pickCompanies": 198,
    "pickEff": 58.3,
    "pickSetup": 372,
    "packItems": 1408,
    "packMinutes": 2586,
    "packCompanies": 402,
    "packEff": 87.2,
    "packSetup": 335,
    "setupMinutes": 707,
    "totalItems": 1872,
    "totalHours": 68.3
  },
  {
    "date": "2026-04-14",
    "pickItems": 501,
    "pickMinutes": 1520,
    "pickCompanies": 213,
    "pickEff": 62.5,
    "pickSetup": 401,
    "packItems": 1071,
    "packMinutes": 1909,
    "packCompanies": 306,
    "packEff": 89.8,
    "packSetup": 255,
    "setupMinutes": 656,
    "totalItems": 1572,
    "totalHours": 57.1
  },
  {
    "date": "2026-04-15",
    "pickItems": 583,
    "pickMinutes": 1763,
    "pickCompanies": 248,
    "pickEff": 62.7,
    "pickSetup": 467,
    "packItems": 926,
    "packMinutes": 1413,
    "packCompanies": 264,
    "packEff": 105.0,
    "packSetup": 220,
    "setupMinutes": 687,
    "totalItems": 1509,
    "totalHours": 52.9
  },
  {
    "date": "2026-04-16",
    "pickItems": 413,
    "pickMinutes": 1508,
    "pickCompanies": 176,
    "pickEff": 52.0,
    "pickSetup": 331,
    "packItems": 1173,
    "packMinutes": 1654,
    "packCompanies": 335,
    "packEff": 113.5,
    "packSetup": 279,
    "setupMinutes": 610,
    "totalItems": 1586,
    "totalHours": 52.7
  },
  {
    "date": "2026-04-17",
    "pickItems": 416,
    "pickMinutes": 1118,
    "pickCompanies": 177,
    "pickEff": 70.6,
    "pickSetup": 333,
    "packItems": 1033,
    "packMinutes": 1613,
    "packCompanies": 295,
    "packEff": 102.6,
    "packSetup": 246,
    "setupMinutes": 579,
    "totalItems": 1449,
    "totalHours": 45.5
  },
  {
    "date": "2026-04-20",
    "pickItems": 470,
    "pickMinutes": 1722,
    "pickCompanies": 200,
    "pickEff": 51.7,
    "pickSetup": 376,
    "packItems": 864,
    "packMinutes": 1500,
    "packCompanies": 247,
    "packEff": 92.3,
    "packSetup": 206,
    "setupMinutes": 582,
    "totalItems": 1334,
    "totalHours": 53.7
  },
  {
    "date": "2026-04-21",
    "pickItems": 823,
    "pickMinutes": 2227,
    "pickCompanies": 350,
    "pickEff": 70.0,
    "pickSetup": 659,
    "packItems": 1137,
    "packMinutes": 1903,
    "packCompanies": 324,
    "packEff": 95.6,
    "packSetup": 270,
    "setupMinutes": 929,
    "totalItems": 1960,
    "totalHours": 68.8
  },
  {
    "date": "2026-04-22",
    "pickItems": 645,
    "pickMinutes": 1847,
    "pickCompanies": 275,
    "pickEff": 66.2,
    "pickSetup": 517,
    "packItems": 894,
    "packMinutes": 1517,
    "packCompanies": 255,
    "packEff": 94.3,
    "packSetup": 213,
    "setupMinutes": 730,
    "totalItems": 1539,
    "totalHours": 56.1
  },
  {
    "date": "2026-04-23",
    "pickItems": 607,
    "pickMinutes": 1104,
    "pickCompanies": 258,
    "pickEff": 104.2,
    "pickSetup": 486,
    "packItems": 956,
    "packMinutes": 1764,
    "packCompanies": 273,
    "packEff": 86.8,
    "packSetup": 227,
    "setupMinutes": 713,
    "totalItems": 1563,
    "totalHours": 47.8
  },
  {
    "date": "2026-04-24",
    "pickItems": 1025,
    "pickMinutes": 0,
    "pickCompanies": 437,
    "pickEff": null,
    "pickSetup": 821,
    "packItems": 1352,
    "packMinutes": 2001,
    "packCompanies": 386,
    "packEff": 108.2,
    "packSetup": 322,
    "setupMinutes": 1143,
    "totalItems": 2377,
    "totalHours": 33.4
  },
  {
    "date": "2026-04-27",
    "pickItems": 962,
    "pickMinutes": 0,
    "pickCompanies": 410,
    "pickEff": null,
    "pickSetup": 770,
    "packItems": 1270,
    "packMinutes": 2481,
    "packCompanies": 362,
    "packEff": 82.0,
    "packSetup": 302,
    "setupMinutes": 1072,
    "totalItems": 2232,
    "totalHours": 41.4
  },
  {
    "date": "2026-04-28",
    "pickItems": 943,
    "pickMinutes": 0,
    "pickCompanies": 402,
    "pickEff": null,
    "pickSetup": 755,
    "packItems": 1247,
    "packMinutes": 1827,
    "packCompanies": 356,
    "packEff": 109.3,
    "packSetup": 297,
    "setupMinutes": 1052,
    "totalItems": 2190,
    "totalHours": 30.4
  },
  {
    "date": "2026-04-30",
    "pickItems": 797,
    "pickMinutes": 0,
    "pickCompanies": 340,
    "pickEff": null,
    "pickSetup": 638,
    "packItems": 1049,
    "packMinutes": 1694,
    "packCompanies": 299,
    "packEff": 99.1,
    "packSetup": 249,
    "setupMinutes": 887,
    "totalItems": 1846,
    "totalHours": 28.2
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
      "pureSecPerItem": 32.2,
      "setupHours": 16.3,
      "efficiency": 142.2,
      "shrunk": 130.4,
      "lo": 114.8,
      "hi": 146.1,
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
      "pureSecPerItem": 49.5,
      "setupHours": 9.1,
      "efficiency": 151.7,
      "shrunk": 149.1,
      "lo": 134.8,
      "hi": 163.5,
      "fairTarget": 1.58,
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
      "pureSecPerItem": 40.6,
      "setupHours": 11.9,
      "efficiency": 126.2,
      "shrunk": 118.6,
      "lo": 102.1,
      "hi": 135.1,
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
      "pureSecPerItem": 57.3,
      "setupHours": 9.4,
      "efficiency": 134.9,
      "shrunk": 133.3,
      "lo": 118.6,
      "hi": 148.0,
      "fairTarget": 1.58,
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
      "pureSecPerItem": 36.1,
      "setupHours": 3.6,
      "efficiency": 130.0,
      "shrunk": 118.1,
      "lo": 99.0,
      "hi": 137.2,
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
      "pureSecPerItem": 87.5,
      "setupHours": 5.3,
      "efficiency": 94.6,
      "shrunk": 96.0,
      "lo": 77.9,
      "hi": 114.2,
      "fairTarget": 1.66,
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
      "pureSecPerItem": 47.2,
      "setupHours": 5.4,
      "efficiency": 124.0,
      "shrunk": 115.9,
      "lo": 98.0,
      "hi": 133.8,
      "fairTarget": 1.59,
      "verdict": "標準"
    },
    "pack": {
      "items": 2881,
      "minutes": 4007,
      "companies": 988,
      "days": 19,
      "itemsPerCompany": 2.92,
      "rawSecPerItem": 83.5,
      "pureSecPerItem": 66.3,
      "setupHours": 13.7,
      "efficiency": 118.6,
      "shrunk": 118.0,
      "lo": 103.3,
      "hi": 132.7,
      "fairTarget": 1.65,
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
      "pureSecPerItem": 39.0,
      "setupHours": 12.0,
      "efficiency": 124.3,
      "shrunk": 115.6,
      "lo": 97.1,
      "hi": 134.0,
      "fairTarget": 2.27,
      "verdict": "標準"
    },
    "pack": {
      "items": 634,
      "minutes": 1530,
      "companies": 161,
      "days": 10,
      "itemsPerCompany": 3.95,
      "rawSecPerItem": 144.8,
      "pureSecPerItem": 132.1,
      "setupHours": 2.2,
      "efficiency": 65.2,
      "shrunk": 70.3,
      "lo": 50.6,
      "hi": 90.0,
      "fairTarget": 1.57,
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
      "pureSecPerItem": 51.2,
      "setupHours": 4.0,
      "efficiency": 119.0,
      "shrunk": 112.0,
      "lo": 92.9,
      "hi": 131.1,
      "fairTarget": 1.51,
      "verdict": "標準"
    },
    "pack": {
      "items": 266,
      "minutes": 265,
      "companies": 46,
      "days": 6,
      "itemsPerCompany": 5.8,
      "rawSecPerItem": 59.8,
      "pureSecPerItem": 51.2,
      "setupHours": 0.6,
      "efficiency": 151.3,
      "shrunk": 143.8,
      "lo": 119.3,
      "hi": 168.3,
      "fairTarget": 1.51,
      "verdict": "上位"
    }
  },
  {
    "name": "中村美佳",
    "role": "parttime",
    "pick": {
      "items": 79,
      "minutes": 120,
      "companies": 30,
      "days": 3,
      "itemsPerCompany": 2.61,
      "rawSecPerItem": 91.1,
      "pureSecPerItem": 47.9,
      "setupHours": 0.9,
      "efficiency": 119.6,
      "shrunk": 108.5,
      "lo": 84.9,
      "hi": 132.1,
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
      "pureSecPerItem": 102.7,
      "setupHours": 1.5,
      "efficiency": 82.1,
      "shrunk": 88.7,
      "lo": 60.0,
      "hi": 117.5,
      "fairTarget": 1.6,
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
      "pureSecPerItem": 52.9,
      "setupHours": 3.6,
      "efficiency": 112.5,
      "shrunk": 107.3,
      "lo": 85.9,
      "hi": 128.8,
      "fairTarget": 1.92,
      "verdict": "標準"
    },
    "pack": {
      "items": 593,
      "minutes": 685,
      "companies": 71,
      "days": 7,
      "itemsPerCompany": 8.3,
      "rawSecPerItem": 69.3,
      "pureSecPerItem": 63.3,
      "setupHours": 1.0,
      "efficiency": 126.7,
      "shrunk": 124.0,
      "lo": 101.0,
      "hi": 147.0,
      "fairTarget": 1.46,
      "verdict": "標準"
    }
  },
  {
    "name": "後藤克行",
    "role": "parttime",
    "pick": {
      "items": 1579,
      "minutes": 2975,
      "companies": 754,
      "days": 16,
      "itemsPerCompany": 2.09,
      "rawSecPerItem": 113.0,
      "pureSecPerItem": 59.1,
      "setupHours": 23.6,
      "efficiency": 105.8,
      "shrunk": 105.1,
      "lo": 89.8,
      "hi": 120.4,
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
      "pureSecPerItem": 103.4,
      "setupHours": 5.2,
      "efficiency": 81.4,
      "shrunk": 83.1,
      "lo": 68.8,
      "hi": 97.5,
      "fairTarget": 1.58,
      "verdict": "要支援"
    }
  },
  {
    "name": "佐々木千恵",
    "role": "parttime",
    "pick": {
      "items": 588,
      "minutes": 905,
      "companies": 165,
      "days": 8,
      "itemsPerCompany": 3.57,
      "rawSecPerItem": 92.3,
      "pureSecPerItem": 60.7,
      "setupHours": 5.2,
      "efficiency": 105.4,
      "shrunk": 104.5,
      "lo": 85.4,
      "hi": 123.6,
      "fairTarget": 1.62,
      "verdict": "標準"
    },
    "pack": {
      "items": 890,
      "minutes": 770,
      "companies": 191,
      "days": 7,
      "itemsPerCompany": 4.65,
      "rawSecPerItem": 51.9,
      "pureSecPerItem": 41.2,
      "setupHours": 2.7,
      "efficiency": 178.3,
      "shrunk": 167.5,
      "lo": 144.5,
      "hi": 190.5,
      "fairTarget": 1.54,
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
      "pureSecPerItem": 60.5,
      "setupHours": 11.8,
      "efficiency": 104.8,
      "shrunk": 104.3,
      "lo": 87.9,
      "hi": 120.8,
      "fairTarget": 1.89,
      "verdict": "標準"
    },
    "pack": {
      "items": 2422,
      "minutes": 4132,
      "companies": 699,
      "days": 20,
      "itemsPerCompany": 3.46,
      "rawSecPerItem": 102.4,
      "pureSecPerItem": 87.9,
      "setupHours": 9.7,
      "efficiency": 94.0,
      "shrunk": 94.9,
      "lo": 80.6,
      "hi": 109.3,
      "fairTarget": 1.6,
      "verdict": "標準"
    }
  },
  {
    "name": "山本祥吉",
    "role": "parttime",
    "pick": {
      "items": 1776,
      "minutes": 3029,
      "companies": 614,
      "days": 16,
      "itemsPerCompany": 2.89,
      "rawSecPerItem": 102.3,
      "pureSecPerItem": 63.3,
      "setupHours": 19.2,
      "efficiency": 102.3,
      "shrunk": 102.6,
      "lo": 87.3,
      "hi": 118.0,
      "fairTarget": 1.74,
      "verdict": "標準"
    },
    "pack": {
      "items": 1548,
      "minutes": 2828,
      "companies": 393,
      "days": 20,
      "itemsPerCompany": 3.94,
      "rawSecPerItem": 109.6,
      "pureSecPerItem": 96.9,
      "setupHours": 5.5,
      "efficiency": 86.2,
      "shrunk": 87.6,
      "lo": 73.3,
      "hi": 101.9,
      "fairTarget": 1.57,
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
      "pureSecPerItem": 64.8,
      "setupHours": 3.0,
      "efficiency": 100.8,
      "shrunk": 102.4,
      "lo": 79.9,
      "hi": 124.8,
      "fairTarget": 2.03,
      "verdict": "標準"
    },
    "pack": {
      "items": 630,
      "minutes": 1945,
      "companies": 187,
      "days": 10,
      "itemsPerCompany": 3.37,
      "rawSecPerItem": 185.2,
      "pureSecPerItem": 170.4,
      "setupHours": 2.6,
      "efficiency": 52.2,
      "shrunk": 58.7,
      "lo": 39.0,
      "hi": 78.4,
      "fairTarget": 1.61,
      "verdict": "要支援"
    }
  },
  {
    "name": "石戸谷亜子",
    "role": "parttime",
    "pick": {
      "items": 640,
      "minutes": 1123,
      "companies": 213,
      "days": 6,
      "itemsPerCompany": 3.0,
      "rawSecPerItem": 105.3,
      "pureSecPerItem": 67.7,
      "setupHours": 6.7,
      "efficiency": 98.1,
      "shrunk": 100.9,
      "lo": 80.3,
      "hi": 121.4,
      "fairTarget": 1.72,
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
      "pureSecPerItem": 67.8,
      "setupHours": 6.0,
      "efficiency": 98.5,
      "shrunk": 100.3,
      "lo": 82.9,
      "hi": 117.7,
      "fairTarget": 2.22,
      "verdict": "標準"
    },
    "pack": {
      "items": 1442,
      "minutes": 1758,
      "companies": 472,
      "days": 13,
      "itemsPerCompany": 3.06,
      "rawSecPerItem": 73.1,
      "pureSecPerItem": 56.8,
      "setupHours": 6.6,
      "efficiency": 134.2,
      "shrunk": 131.9,
      "lo": 114.4,
      "hi": 149.4,
      "fairTarget": 1.64,
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
      "pureSecPerItem": 73.8,
      "setupHours": 10.2,
      "efficiency": 93.7,
      "shrunk": 99.2,
      "lo": 77.7,
      "hi": 120.6,
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
      "pureSecPerItem": 118.8,
      "setupHours": 0.5,
      "efficiency": 71.0,
      "shrunk": 82.5,
      "lo": 50.5,
      "hi": 114.4,
      "fairTarget": 1.5,
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
      "pureSecPerItem": 72.2,
      "setupHours": 8.4,
      "efficiency": 94.9,
      "shrunk": 97.6,
      "lo": 81.5,
      "hi": 113.6,
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
      "pureSecPerItem": 117.0,
      "setupHours": 6.3,
      "efficiency": 72.9,
      "shrunk": 75.1,
      "lo": 60.8,
      "hi": 89.5,
      "fairTarget": 1.58,
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
      "pureSecPerItem": 79.9,
      "setupHours": 11.8,
      "efficiency": 89.8,
      "shrunk": 95.2,
      "lo": 77.3,
      "hi": 113.1,
      "fairTarget": 2.09,
      "verdict": "標準"
    },
    "pack": null
  },
  {
    "name": "片岡達也",
    "role": "parttime",
    "pick": {
      "items": 66,
      "minutes": 202,
      "companies": 47,
      "days": 4,
      "itemsPerCompany": 1.4,
      "rawSecPerItem": 183.6,
      "pureSecPerItem": 103.3,
      "setupHours": 1.5,
      "efficiency": 79.5,
      "shrunk": 94.3,
      "lo": 71.8,
      "hi": 116.7,
      "fairTarget": 2.43,
      "verdict": "標準"
    },
    "pack": null
  },
  {
    "name": "菊池敬",
    "role": "parttime",
    "pick": {
      "items": 332,
      "minutes": 712,
      "companies": 146,
      "days": 13,
      "itemsPerCompany": 2.28,
      "rawSecPerItem": 128.7,
      "pureSecPerItem": 79.2,
      "setupHours": 4.6,
      "efficiency": 89.5,
      "shrunk": 94.1,
      "lo": 77.6,
      "hi": 110.6,
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
      "pureSecPerItem": 133.8,
      "setupHours": 5.1,
      "efficiency": 65.2,
      "shrunk": 68.3,
      "lo": 52.8,
      "hi": 83.8,
      "fairTarget": 1.62,
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
      "pureSecPerItem": 86.8,
      "setupHours": 8.2,
      "efficiency": 84.7,
      "shrunk": 92.5,
      "lo": 74.0,
      "hi": 111.0,
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
      "pureSecPerItem": 101.6,
      "setupHours": 2.9,
      "efficiency": 78.1,
      "shrunk": 89.4,
      "lo": 70.3,
      "hi": 108.5,
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
      "pureSecPerItem": 62.5,
      "setupHours": 6.0,
      "efficiency": 123.3,
      "shrunk": 121.9,
      "lo": 103.8,
      "hi": 140.1,
      "fairTarget": 1.7,
      "verdict": "標準"
    }
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
      "pureSecPerItem": 96.9,
      "setupHours": 9.0,
      "efficiency": 79.0,
      "shrunk": 89.2,
      "lo": 70.7,
      "hi": 107.7,
      "fairTarget": 1.95,
      "verdict": "標準"
    },
    "pack": null
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
      "pureSecPerItem": 93.3,
      "setupHours": 11.3,
      "efficiency": 80.0,
      "shrunk": 89.2,
      "lo": 71.3,
      "hi": 107.1,
      "fairTarget": 1.83,
      "verdict": "標準"
    },
    "pack": null
  },
  {
    "name": "上村和恵",
    "role": "parttime",
    "pick": {
      "items": 765,
      "minutes": 1960,
      "companies": 320,
      "days": 9,
      "itemsPerCompany": 2.39,
      "rawSecPerItem": 153.7,
      "pureSecPerItem": 106.6,
      "setupHours": 10.0,
      "efficiency": 73.4,
      "shrunk": 86.0,
      "lo": 67.5,
      "hi": 104.5,
      "fairTarget": 1.88,
      "verdict": "標準"
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
      "pureSecPerItem": 139.5,
      "setupHours": 1.6,
      "efficiency": 58.0,
      "shrunk": 79.8,
      "lo": 60.0,
      "hi": 99.6,
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
      "pureSecPerItem": 81.3,
      "setupHours": 4.1,
      "efficiency": 100.6,
      "shrunk": 101.6,
      "lo": 81.0,
      "hi": 122.3,
      "fairTarget": 1.62,
      "verdict": "標準"
    }
  }
];

/** ピッキング総時間の内訳。付加価値作業は「ピック」だけ。 */
export const timeMix: MixSlice[] = [
  {
    "label": "段取り",
    "detail": "リスト確認・伝票挟み（1社ごと）",
    "hours": 212.8
  },
  {
    "label": "移動",
    "detail": "棚まで往復（1件ごと）",
    "hours": 145.7
  },
  {
    "label": "ピック",
    "detail": "棚から取ってカゴへ（1件ごと・唯一の付加価値）",
    "hours": 145.7
  }
];

export const totals = {
  "pickItems": 15942,
  "packItems": 24449,
  "pickMinutes": 30275,
  "packMinutes": 39147,
  "pickCompanies": 6791,
  "packCompanies": 6977,
  "totalItems": 40391,
  "totalHours": 1157.0,
  "setupHours": 309.7,
  "setupRatio": 26.8,
  "pickSetupRatio": 42.2,
  "avgEff": 99.9,
  "pickEff": 99.8,
  "packEff": 100.0,
  "secPerItem": 103.1,
  "headcount": 26
} as const;

/** 直近7日 vs その前7日（記録が揃っている日のみ）。 */
export const deltas = {
  "items": -23.0,
  "hours": -16.5,
  "eff": -12.8,
  "setup": -24.9
} as const;

/** PK実働時間の記録が欠落している区間。チャート上で明示する。 */
export const recordGap = {
  "start": "2026-04-23",
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
