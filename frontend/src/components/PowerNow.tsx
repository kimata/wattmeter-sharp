import { AnimatedNumber } from "./common/AnimatedNumber";
import { ELECTRICITY_RATE_YEN_PER_KWH } from "../config/constants";
import { CONN_STATE_LABEL } from "../utils/device";
import type { DeviceView } from "../App";
import type { PowerHistoryResponse } from "../types";

interface PowerNowProps {
    devices: DeviceView[];
    history: PowerHistoryResponse | null;
    rangeLabel: string;
    updatedAt: number | null;
}

export function PowerNow({ devices, history, rangeLabel, updatedAt }: PowerNowProps) {
    const total = devices.reduce((sum, d) => sum + (d.watt ?? 0), 0);

    const totalEnergyWh = history
        ? history.series.reduce((sum, s) => sum + (s.energy_wh ?? 0), 0)
        : null;
    const estimatedYen =
        totalEnergyWh !== null
            ? (totalEnergyWh / 1000) * ELECTRICITY_RATE_YEN_PER_KWH
            : null;

    const onlineCount = devices.filter(
        (d) => d.state === "online" || d.state === "unstable",
    ).length;
    const issueDevices = devices.filter(
        (d) => d.state === "disconnected" || d.state === "lost",
    );
    const connLevel =
        issueDevices.length > 0 ? "bad" : onlineCount < devices.length ? "warn" : "good";

    return (
        <section className="card" data-testid="power-hero">
            <div className="hero">
                <div className="hero-main">
                    <div className="hero-label">現在の消費電力</div>
                    <div className="hero-value" data-testid="total-watt">
                        <AnimatedNumber
                            value={Math.round(total)}
                            decimals={0}
                            useComma={true}
                            duration={1.0}
                        />
                        <span className="unit">W</span>
                    </div>
                    {updatedAt && (
                        <div className="hero-sub">
                            <span className="live-dot" />
                            {new Date(updatedAt * 1000).toLocaleTimeString("ja-JP")} 更新
                            (1分毎に自動更新)
                        </div>
                    )}
                </div>
                <div className="hero-stats">
                    <div className="stat-tile">
                        <div className="stat-label">使用量 ({rangeLabel})</div>
                        <div className="stat-value">
                            {totalEnergyWh !== null ? (
                                <AnimatedNumber
                                    value={totalEnergyWh / 1000}
                                    decimals={totalEnergyWh >= 100_000 ? 0 : 1}
                                    useComma={true}
                                />
                            ) : (
                                "–"
                            )}
                            <span className="unit">kWh</span>
                        </div>
                    </div>
                    <div className="stat-tile">
                        <div className="stat-label">電気代の目安 ({rangeLabel})</div>
                        <div className="stat-value">
                            {estimatedYen !== null ? (
                                <>
                                    ¥
                                    <AnimatedNumber
                                        value={estimatedYen}
                                        decimals={0}
                                        useComma={true}
                                    />
                                </>
                            ) : (
                                "–"
                            )}
                        </div>
                        <div className="stat-note">
                            {ELECTRICITY_RATE_YEN_PER_KWH}円/kWh で計算
                        </div>
                    </div>
                    <div className="stat-tile" data-testid="conn-summary">
                        <div className="stat-label">デバイス接続</div>
                        <div className="stat-value">
                            <span className={`chip ${connLevel}`} style={{ fontSize: "1rem" }}>
                                {onlineCount} / {devices.length}
                            </span>
                        </div>
                        <div className="stat-note">
                            {issueDevices.length > 0
                                ? `${issueDevices
                                      .slice(0, 2)
                                      .map((d) => d.name)
                                      .join("・")}${issueDevices.length > 2 ? ` ほか${issueDevices.length - 2}台` : ""}が${CONN_STATE_LABEL[issueDevices[0].state]}`
                                : "全デバイス受信中"}
                        </div>
                    </div>
                </div>
            </div>
        </section>
    );
}
