import { useMemo, useState } from "react";
import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
import "dayjs/locale/ja";

import type {
    ApiResponse,
    CommunicationErrorResponse,
    PowerCurrentResponse,
    PowerHistoryResponse,
} from "./types";
import { useApi } from "./hooks/useApi";
import { buildApiUrl, RANGE_OPTIONS, type RangeKey } from "./config/constants";
import { connectionState, type ConnState } from "./utils/device";
import { PowerNow } from "./components/PowerNow";
import { TrendChart } from "./components/TrendChart";
import { DeviceGrid } from "./components/DeviceGrid";
import { EnergyRanking } from "./components/EnergyRanking";
import { ConnectionStatus } from "./components/ConnectionStatus";
import { Footer } from "./components/Footer";

dayjs.extend(relativeTime);
dayjs.locale("ja");

// 電力 (power API) と受信状態 (sensor_stat API) をデバイス名で束ねた表示用モデル
export interface DeviceView {
    name: string;
    watt: number | null;
    state: ConnState;
    lastReceivedTs: number | null;
    availability24h: number;
    availabilityTotal: number;
    spark: (number | null)[] | null;
}

type Tab = "power" | "connection";

function App() {
    const [tab, setTab] = useState<Tab>("power");
    const [range, setRange] = useState<RangeKey>("24h");

    const { data: current, error: currentError } = useApi<PowerCurrentResponse>(
        buildApiUrl("power/current"),
        { interval: 60000 },
    );
    const { data: history, error: historyError } = useApi<PowerHistoryResponse>(
        buildApiUrl(`power/history?range=${range}`),
        { interval: 300000 },
    );
    const { data: stat, error: statError } = useApi<ApiResponse>(
        buildApiUrl("sensor_stat"),
        { interval: 120000 },
    );
    const { data: commErrors } = useApi<CommunicationErrorResponse>(
        buildApiUrl("communication_errors"),
        { interval: 300000 },
    );

    const nowSec = Math.floor(Date.now() / 1000);

    const devices: DeviceView[] = useMemo(() => {
        if (!current) return [];

        const statByName = new Map(stat?.sensors.map((s) => [s.name, s]) ?? []);
        const sparkByName = new Map(
            history?.series.map((s) => [s.name, s.values]) ?? [],
        );

        return current.devices.map((device) => {
            const sensorStat = statByName.get(device.name);
            // 受信時刻はハートビート (metrics.db) を優先し、なければ電力データの時刻
            const lastReceivedTs =
                sensorStat?.last_received_ts ?? device.time ?? null;
            const availability24h = sensorStat?.availability_24h ?? 0;

            return {
                name: device.name,
                watt: device.watt,
                state: connectionState(lastReceivedTs, availability24h, nowSec),
                lastReceivedTs,
                availability24h,
                availabilityTotal: sensorStat?.availability_total ?? 0,
                spark: sparkByName.get(device.name) ?? null,
            };
        });
    }, [current, stat, history, nowSec]);

    const issueCount = devices.filter(
        (d) => d.state === "disconnected" || d.state === "lost",
    ).length;

    const rangeLabel =
        RANGE_OPTIONS.find((option) => option.key === range)?.label ?? range;

    const apiError = currentError || historyError || statError;
    const updateTime = current
        ? dayjs(current.updated_at * 1000).format("YYYY年MM月DD日 HH:mm:ss")
        : "–";

    return (
        <div data-testid="app">
            <header className="app-header">
                <div className="app-header-inner">
                    <h1 className="app-title" data-testid="app-title">
                        ⚡ おうち電力モニター
                        <span className="app-subtitle">SHARP HEMS</span>
                    </h1>
                    <nav className="tabs">
                        <button
                            type="button"
                            className={`tab${tab === "power" ? " active" : ""}`}
                            data-testid="tab-power"
                            onClick={() => setTab("power")}
                        >
                            電力
                        </button>
                        <button
                            type="button"
                            className={`tab${tab === "connection" ? " active" : ""}`}
                            data-testid="tab-connection"
                            onClick={() => setTab("connection")}
                        >
                            接続状態
                            {issueCount > 0 && <span className="tab-alert" />}
                        </button>
                    </nav>
                </div>
            </header>

            <main className="app-main">
                {apiError && devices.length > 0 && (
                    <div className="error-banner" data-testid="error-banner">
                        ⚠ データの更新に失敗しました ({apiError})。前回取得したデータを表示しています。
                    </div>
                )}
                {apiError && devices.length === 0 && (
                    <div className="error-banner" data-testid="error-banner">
                        ⚠ データを取得できませんでした: {apiError}
                    </div>
                )}

                {tab === "power" ? (
                    <>
                        {current ? (
                            <PowerNow
                                devices={devices}
                                history={history}
                                rangeLabel={rangeLabel}
                                updatedAt={current.updated_at}
                            />
                        ) : (
                            <div className="skeleton" style={{ height: "160px", marginBottom: "1rem" }} />
                        )}

                        <TrendChart history={history} range={range} onRangeChange={setRange} />

                        {current ? (
                            <DeviceGrid
                                devices={devices}
                                nowSec={nowSec}
                                sparkRefreshKey={history?.updated_at ?? 0}
                            />
                        ) : (
                            <div className="skeleton" style={{ height: "300px", marginBottom: "1rem" }} />
                        )}

                        <EnergyRanking history={history} rangeLabel={rangeLabel} />
                    </>
                ) : (
                    <ConnectionStatus
                        devices={devices}
                        errors={commErrors}
                        startDate={stat?.start_date ?? null}
                        nowSec={nowSec}
                    />
                )}
            </main>

            <Footer updateTime={updateTime} />
        </div>
    );
}

export default App;
