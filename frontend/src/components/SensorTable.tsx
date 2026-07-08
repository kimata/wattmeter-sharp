import { useState } from "react";
import dayjs from "dayjs";

import {
    deviceIcon,
    formatAgo,
    CONN_STATE_LABEL,
    CONN_STATE_CHIP,
} from "../utils/device";
import type { DeviceView } from "../App";

interface SensorTableProps {
    devices: DeviceView[];
    nowSec: number;
}

type SortKey = "name" | "state" | "availability_24h" | "availability_total" | "last_received";

const STATE_ORDER = { lost: 0, disconnected: 1, unstable: 2, online: 3 };

function availClass(percent: number): string {
    if (percent >= 90) return "good";
    if (percent >= 70) return "warn";
    return "bad";
}

function AvailabilityCell({ percent }: { percent: number }) {
    return (
        <div className="avail-cell">
            <div className={`avail-bar ${availClass(percent)}`}>
                <span style={{ width: `${Math.min(percent, 100)}%` }} />
            </div>
            <span>{percent.toFixed(1)}%</span>
        </div>
    );
}

export function SensorTable({ devices, nowSec }: SensorTableProps) {
    const [sortKey, setSortKey] = useState<SortKey>("state");
    const [ascending, setAscending] = useState(true);

    const handleSort = (key: SortKey) => {
        if (key === sortKey) {
            setAscending(!ascending);
        } else {
            setSortKey(key);
            setAscending(true);
        }
    };

    const sorted = [...devices].sort((a, b) => {
        let cmp = 0;
        switch (sortKey) {
            case "name":
                cmp = a.name.localeCompare(b.name, "ja");
                break;
            case "state":
                cmp = STATE_ORDER[a.state] - STATE_ORDER[b.state];
                break;
            case "availability_24h":
                cmp = a.availability24h - b.availability24h;
                break;
            case "availability_total":
                cmp = a.availabilityTotal - b.availabilityTotal;
                break;
            case "last_received":
                cmp = (a.lastReceivedTs ?? 0) - (b.lastReceivedTs ?? 0);
                break;
        }
        return ascending ? cmp : -cmp;
    });

    const arrow = (key: SortKey) =>
        sortKey === key ? (ascending ? " ▲" : " ▼") : "";

    return (
        <section className="card">
            <h2 className="card-title">
                デバイス別の受信状態
                <span className="card-note">見出しクリックで並べ替え</span>
            </h2>
            <div className="table-wrap">
                <table className="data-table" data-testid="sensor-table">
                    <thead>
                        <tr>
                            <th onClick={() => handleSort("name")}>デバイス{arrow("name")}</th>
                            <th onClick={() => handleSort("state")}>状態{arrow("state")}</th>
                            <th onClick={() => handleSort("availability_24h")}>
                                受信率 (24時間){arrow("availability_24h")}
                            </th>
                            <th onClick={() => handleSort("availability_total")}>
                                受信率 (累計){arrow("availability_total")}
                            </th>
                            <th onClick={() => handleSort("last_received")}>
                                最終受信{arrow("last_received")}
                            </th>
                        </tr>
                    </thead>
                    <tbody>
                        {sorted.map((device) => {
                            const age =
                                device.lastReceivedTs !== null
                                    ? nowSec - device.lastReceivedTs
                                    : null;
                            return (
                                <tr key={device.name}>
                                    <td>
                                        {deviceIcon(device.name)} {device.name}
                                    </td>
                                    <td>
                                        <span className={`chip ${CONN_STATE_CHIP[device.state]}`}>
                                            {CONN_STATE_LABEL[device.state]}
                                        </span>
                                    </td>
                                    <td>
                                        <AvailabilityCell percent={device.availability24h} />
                                    </td>
                                    <td>
                                        <AvailabilityCell percent={device.availabilityTotal} />
                                    </td>
                                    <td>
                                        {device.lastReceivedTs !== null ? (
                                            <>
                                                {dayjs(device.lastReceivedTs * 1000).format(
                                                    "M/D HH:mm",
                                                )}
                                                <span
                                                    style={{
                                                        color: "var(--muted)",
                                                        marginLeft: "0.4rem",
                                                    }}
                                                >
                                                    ({age !== null ? formatAgo(age) : ""})
                                                </span>
                                            </>
                                        ) : (
                                            "受信履歴なし"
                                        )}
                                    </td>
                                </tr>
                            );
                        })}
                    </tbody>
                </table>
            </div>
        </section>
    );
}
