import { deviceIcon, formatKwh, formatYen } from "../utils/device";
import { ELECTRICITY_RATE_YEN_PER_KWH } from "../config/constants";
import type { PowerHistoryResponse } from "../types";

interface EnergyRankingProps {
    history: PowerHistoryResponse | null;
    rangeLabel: string;
}

const TOP_N = 10;

export function EnergyRanking({ history, rangeLabel }: EnergyRankingProps) {
    if (!history) {
        return (
            <section className="card">
                <h2 className="card-title">電力量ランキング</h2>
                <div className="skeleton" style={{ height: "220px" }} />
            </section>
        );
    }

    const ranked = history.series
        .filter((s) => s.energy_wh !== null && s.energy_wh > 0)
        .sort((a, b) => (b.energy_wh ?? 0) - (a.energy_wh ?? 0))
        .slice(0, TOP_N);

    const maxWh = ranked.length > 0 ? (ranked[0].energy_wh ?? 1) : 1;

    return (
        <section className="card" data-testid="energy-ranking">
            <h2 className="card-title">
                電力量ランキング
                <span className="card-note">{rangeLabel}の使用量上位 {ranked.length} 台</span>
            </h2>
            <div className="ranking">
                {ranked.map((s, i) => {
                    const wh = s.energy_wh ?? 0;
                    const yen = (wh / 1000) * ELECTRICITY_RATE_YEN_PER_KWH;
                    return (
                        <div className="ranking-row" key={s.name}>
                            <span className="ranking-rank">{i + 1}</span>
                            <span className="ranking-name" title={s.name}>
                                {deviceIcon(s.name)} {s.name}
                            </span>
                            <div className="ranking-bar">
                                <span style={{ width: `${(wh / maxWh) * 100}%` }} />
                            </div>
                            <span className="ranking-value">
                                {formatKwh(wh)} kWh
                                <span className="sub">¥{formatYen(yen)}</span>
                            </span>
                        </div>
                    );
                })}
                {ranked.length === 0 && (
                    <div className="card-note">この期間のデータがありません</div>
                )}
            </div>
        </section>
    );
}
