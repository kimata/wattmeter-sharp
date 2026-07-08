import { Sparkline } from "./Sparkline";
import {
    deviceIcon,
    formatWatt,
    formatDuration,
    formatAgo,
    CONN_STATE_LABEL,
    CONN_STATE_CHIP,
} from "../utils/device";
import type { DeviceView } from "../App";

interface DeviceGridProps {
    devices: DeviceView[];
    nowSec: number;
}

// NOTE: 不安定でも受信できている間は電力順に混ぜて表示し、
// 受信が途絶えているデバイスだけ末尾にまとめる
const STATE_ORDER = { online: 0, unstable: 0, disconnected: 1, lost: 2 };

export function DeviceGrid({ devices, nowSec }: DeviceGridProps) {
    const total = devices.reduce((sum, d) => sum + (d.watt ?? 0), 0);

    const sorted = [...devices].sort((a, b) => {
        if (STATE_ORDER[a.state] !== STATE_ORDER[b.state]) {
            return STATE_ORDER[a.state] - STATE_ORDER[b.state];
        }
        return (b.watt ?? -1) - (a.watt ?? -1);
    });

    return (
        <section className="card">
            <h2 className="card-title">
                デバイス別の消費電力
                <span className="card-note">切断中のデバイスは末尾に表示</span>
            </h2>
            <div className="device-grid" data-testid="device-grid">
                {sorted.map((device) => {
                    const share =
                        device.watt !== null && total > 0
                            ? (device.watt / total) * 100
                            : null;
                    const offline =
                        device.state === "disconnected" || device.state === "lost";
                    const age =
                        device.lastReceivedTs !== null
                            ? nowSec - device.lastReceivedTs
                            : null;

                    return (
                        <div
                            key={device.name}
                            className={`device-card${offline ? " offline" : ""}`}
                            data-testid="device-card"
                        >
                            <div className="device-card-head">
                                <span className="device-icon">{deviceIcon(device.name)}</span>
                                <span className="device-name" title={device.name}>
                                    {device.name}
                                </span>
                                {device.state !== "online" && (
                                    <span
                                        className={`chip ${CONN_STATE_CHIP[device.state]}`}
                                        style={{ marginLeft: "auto", flexShrink: 0 }}
                                    >
                                        {CONN_STATE_LABEL[device.state]}
                                    </span>
                                )}
                            </div>

                            {offline ? (
                                <div className="device-watt na">
                                    {age !== null
                                        ? `${formatDuration(age)}前から受信なし`
                                        : "受信履歴なし"}
                                </div>
                            ) : (
                                <div className="device-watt">
                                    {device.watt !== null ? formatWatt(device.watt) : "–"}
                                    <span className="unit">W</span>
                                </div>
                            )}

                            <div className="share-bar">
                                <span
                                    style={{
                                        width: `${share !== null ? Math.max(share, 0.5) : 0}%`,
                                    }}
                                />
                            </div>

                            {device.spark && <Sparkline values={device.spark} />}

                            <div className="device-foot">
                                <span>{share !== null ? `シェア ${share.toFixed(1)}%` : " "}</span>
                                <span>
                                    {age !== null && !offline
                                        ? `${formatAgo(age)}受信`
                                        : " "}
                                </span>
                            </div>
                        </div>
                    );
                })}
            </div>
        </section>
    );
}
