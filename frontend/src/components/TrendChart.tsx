import { useMemo } from "react";
import {
    Chart as ChartJS,
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    Filler,
    Tooltip,
    Legend,
} from "chart.js";
import { Line } from "react-chartjs-2";
import dayjs from "dayjs";

import { usePrefersDark } from "../hooks/usePrefersDark";
import {
    RANGE_OPTIONS,
    MAX_CHART_SERIES,
    SERIES_COLORS_LIGHT,
    SERIES_COLORS_DARK,
    OTHER_SERIES_COLOR_LIGHT,
    OTHER_SERIES_COLOR_DARK,
    type RangeKey,
} from "../config/constants";
import type { PowerHistoryResponse } from "../types";

ChartJS.register(
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    Filler,
    Tooltip,
    Legend,
);

interface TrendChartProps {
    history: PowerHistoryResponse | null;
    range: RangeKey;
    onRangeChange: (range: RangeKey) => void;
}

function formatTime(epoch: number, range: RangeKey): string {
    const t = dayjs(epoch * 1000);
    switch (range) {
        case "3h":
        case "24h":
            return t.format("H:mm");
        case "7d":
            return t.format("M/D H時");
        default:
            return t.format("M/D");
    }
}

export function TrendChart({ history, range, onRangeChange }: TrendChartProps) {
    const isDark = usePrefersDark();
    const palette = isDark ? SERIES_COLORS_DARK : SERIES_COLORS_LIGHT;
    const otherColor = isDark ? OTHER_SERIES_COLOR_DARK : OTHER_SERIES_COLOR_LIGHT;
    const textColor = isDark ? "#c3c2b7" : "#52514e";
    const gridColor = isDark ? "rgba(255,255,255,0.07)" : "rgba(0,0,0,0.06)";

    const chartData = useMemo(() => {
        if (!history || history.times.length === 0) return null;

        // 電力量の多い順に上位を個別表示し、残りは「その他」へ集約
        const ranked = [...history.series].sort(
            (a, b) => (b.energy_wh ?? 0) - (a.energy_wh ?? 0),
        );
        const top = ranked.slice(0, MAX_CHART_SERIES);
        const rest = ranked.slice(MAX_CHART_SERIES);

        const labels = history.times.map((t) => formatTime(t, range));

        const datasets = top.map((s, i) => ({
            label: s.name,
            // NOTE: 積み上げ表示のため未受信 (null) は 0 として扱う
            data: s.values.map((v) => v ?? 0),
            borderColor: palette[i % palette.length],
            backgroundColor: `${palette[i % palette.length]}55`,
            borderWidth: 1.5,
            pointRadius: 0,
            pointHoverRadius: 3,
            fill: true,
            tension: 0.25,
        }));

        if (rest.length > 0) {
            const otherValues = history.times.map((_, ti) =>
                rest.reduce((sum, s) => sum + (s.values[ti] ?? 0), 0),
            );
            datasets.push({
                label: `その他 (${rest.length}台)`,
                data: otherValues,
                borderColor: otherColor,
                backgroundColor: `${otherColor}55`,
                borderWidth: 1.5,
                pointRadius: 0,
                pointHoverRadius: 3,
                fill: true,
                tension: 0.25,
            });
        }

        return { labels, datasets };
    }, [history, range, palette, otherColor]);

    const isStale = history !== null && history.range !== range;

    return (
        <section className="card" data-testid="trend-chart">
            <h2 className="card-title">
                電力の推移
                <span className="card-note">積み上げ表示 / 上位{MAX_CHART_SERIES}台+その他</span>
                <div className="range-selector" role="group" aria-label="表示期間">
                    {RANGE_OPTIONS.map((option) => (
                        <button
                            key={option.key}
                            type="button"
                            className={`range-btn${option.key === range ? " active" : ""}`}
                            data-testid={`range-${option.key}`}
                            onClick={() => onRangeChange(option.key)}
                        >
                            {option.label}
                        </button>
                    ))}
                </div>
            </h2>
            <div className="chart-container">
                {chartData ? (
                    <Line
                        data={chartData}
                        options={{
                            responsive: true,
                            maintainAspectRatio: false,
                            // データ更新時に滑らかにモーフィングさせる
                            animation: { duration: 800, easing: "easeOutQuart" },
                            // リサイズ時はアニメーションなしで即時再描画する
                            transitions: { resize: { animation: { duration: 0 } } },
                            interaction: { mode: "index", intersect: false },
                            scales: {
                                x: {
                                    stacked: true,
                                    ticks: {
                                        color: textColor,
                                        maxTicksLimit: 9,
                                        maxRotation: 0,
                                        font: { size: 11 },
                                    },
                                    grid: { display: false },
                                },
                                y: {
                                    stacked: true,
                                    beginAtZero: true,
                                    ticks: {
                                        color: textColor,
                                        font: { size: 11 },
                                        callback: (value) => `${value} W`,
                                    },
                                    grid: { color: gridColor },
                                },
                            },
                            plugins: {
                                legend: {
                                    position: "bottom",
                                    labels: {
                                        color: textColor,
                                        boxWidth: 12,
                                        boxHeight: 12,
                                        font: { size: 11 },
                                    },
                                },
                                tooltip: {
                                    callbacks: {
                                        label: (ctx) =>
                                            ` ${ctx.dataset.label}: ${Math.round(ctx.parsed.y)} W`,
                                        footer: (items) => {
                                            const total = items.reduce(
                                                (sum, item) => sum + item.parsed.y,
                                                0,
                                            );
                                            return `合計: ${Math.round(total)} W`;
                                        },
                                    },
                                },
                            },
                        }}
                    />
                ) : (
                    <div className="skeleton" style={{ height: "100%" }} />
                )}
                {isStale && <div className="chart-loading">読み込み中…</div>}
            </div>
        </section>
    );
}
