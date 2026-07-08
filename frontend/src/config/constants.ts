// APIのベースURLを管理
// Viteのbaseパスと同じ値を使用してAPIエンドポイントを構築

// vite.config.tsで明示的に定義されたAPI_BASE_URLを使用
export const API_BASE_URL =
    import.meta.env.VITE_API_BASE_URL || "/wattmeter-sharp/metrics/";

// API URLを構築するヘルパー関数
export const buildApiUrl = (endpoint: string): string => {
    // API_BASE_URLは末尾にスラッシュを含むので、endpointの先頭スラッシュを除去
    const cleanEndpoint = endpoint.startsWith("/")
        ? endpoint.slice(1)
        : endpoint;
    // apiディレクトリを挟んでURLを構築
    return `${API_BASE_URL}api/${cleanEndpoint}`;
};

// 概算電気代の計算に使う単価 (円/kWh)
// 全国平均的な従量料金の目安。契約に応じて変更してください。
export const ELECTRICITY_RATE_YEN_PER_KWH = 31;

// 電力推移の期間セレクタ
export type RangeKey = "3h" | "24h" | "7d" | "30d";

export const RANGE_OPTIONS: { key: RangeKey; label: string; hours: number }[] =
    [
        { key: "3h", label: "3時間", hours: 3 },
        { key: "24h", label: "24時間", hours: 24 },
        { key: "7d", label: "7日", hours: 24 * 7 },
        { key: "30d", label: "30日", hours: 24 * 30 },
    ];

// 電力推移チャートで個別系列として表示する最大数 (残りは「その他」に集約)
export const MAX_CHART_SERIES = 8;

// カテゴリカルパレット (CVD 検証済み・ライト/ダーク)
export const SERIES_COLORS_LIGHT = [
    "#2a78d6",
    "#1baf7a",
    "#eda100",
    "#008300",
    "#4a3aa7",
    "#e34948",
    "#e87ba4",
    "#eb6834",
];

export const SERIES_COLORS_DARK = [
    "#3987e5",
    "#199e70",
    "#c98500",
    "#008300",
    "#9085e9",
    "#e66767",
    "#d55181",
    "#d95926",
];

export const OTHER_SERIES_COLOR_LIGHT = "#a5a49d";
export const OTHER_SERIES_COLOR_DARK = "#6f6e67";
