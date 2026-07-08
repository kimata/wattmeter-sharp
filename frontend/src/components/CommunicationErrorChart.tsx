import {
    Chart as ChartJS,
    CategoryScale,
    LinearScale,
    BarElement,
    Tooltip,
} from "chart.js";
import { Bar } from "react-chartjs-2";

import { usePrefersDark } from "../hooks/usePrefersDark";
import type { CommunicationErrorHistogram } from "../types";

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip);

interface CommunicationErrorChartProps {
    histogram: CommunicationErrorHistogram;
}

// 時間帯別の通信エラー発生ヒストグラム。
// 「電子レンジ使用時に切れる」「深夜に切れる」など、切断の傾向をつかむための表示。
export function CommunicationErrorChart({ histogram }: CommunicationErrorChartProps) {
    const isDark = usePrefersDark();
    const barColor = isDark ? "#3987e5" : "#2a78d6";
    const textColor = isDark ? "#c3c2b7" : "#52514e";
    const gridColor = isDark ? "rgba(255,255,255,0.07)" : "rgba(0,0,0,0.06)";

    return (
        <section className="card" data-testid="error-chart">
            <h2 className="card-title">
                切断が起きやすい時間帯
                <span className="card-note">
                    過去30日 / 30分刻み / 合計 {histogram.total_errors.toLocaleString("ja-JP")} 回
                </span>
            </h2>
            <div className="chart-container small">
                <Bar
                    data={{
                        labels: histogram.bin_labels,
                        datasets: [
                            {
                                label: "通信エラー",
                                data: histogram.bins,
                                backgroundColor: barColor,
                                borderRadius: 3,
                                barPercentage: 0.9,
                                categoryPercentage: 0.9,
                            },
                        ],
                    }}
                    options={{
                        responsive: true,
                        maintainAspectRatio: false,
                        animation: { duration: 300 },
                        // リサイズ時はアニメーションなしで即時再描画する
                        transitions: { resize: { animation: { duration: 0 } } },
                        scales: {
                            x: {
                                ticks: {
                                    color: textColor,
                                    maxTicksLimit: 12,
                                    maxRotation: 0,
                                    font: { size: 11 },
                                },
                                grid: { display: false },
                            },
                            y: {
                                beginAtZero: true,
                                ticks: {
                                    color: textColor,
                                    precision: 0,
                                    font: { size: 11 },
                                },
                                grid: { color: gridColor },
                            },
                        },
                        plugins: {
                            // 単一系列のため凡例は表示しない
                            legend: { display: false },
                            tooltip: {
                                callbacks: {
                                    label: (ctx) => ` ${ctx.parsed.y} 回`,
                                },
                            },
                        },
                    }}
                />
            </div>
        </section>
    );
}
