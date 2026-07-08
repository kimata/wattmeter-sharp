import { useState } from "react";
import dayjs from "dayjs";

import { deviceIcon } from "../utils/device";
import type { CommunicationError } from "../types";

interface CommunicationErrorTableProps {
    errors: CommunicationError[];
}

const INITIAL_LIMIT = 15;

export function CommunicationErrorTable({ errors }: CommunicationErrorTableProps) {
    const [expanded, setExpanded] = useState(false);

    const visible = expanded ? errors : errors.slice(0, INITIAL_LIMIT);

    return (
        <section className="card">
            <h2 className="card-title">
                最近の切断ログ
                <span className="card-note">直近 {errors.length} 件</span>
            </h2>
            <div className="table-wrap">
                <table className="data-table" data-testid="error-table">
                    <thead>
                        <tr>
                            <th className="plain">日時</th>
                            <th className="plain">デバイス</th>
                            <th className="plain">内容</th>
                        </tr>
                    </thead>
                    <tbody>
                        {visible.map((error, i) => (
                            <tr key={`${error.timestamp}-${error.sensor_name}-${i}`}>
                                <td>
                                    {dayjs(error.datetime).format("M/D HH:mm")}
                                    <span style={{ color: "var(--muted)", marginLeft: "0.4rem" }}>
                                        ({dayjs(error.datetime).fromNow()})
                                    </span>
                                </td>
                                <td>
                                    {deviceIcon(error.sensor_name)} {error.sensor_name}
                                </td>
                                <td>
                                    <span className="chip neutral">
                                        {error.error_type === "consecutive_failure"
                                            ? "受信欠落"
                                            : error.error_type}
                                    </span>
                                </td>
                            </tr>
                        ))}
                        {errors.length === 0 && (
                            <tr>
                                <td colSpan={3} style={{ color: "var(--muted)" }}>
                                    切断は記録されていません 🎉
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
            {errors.length > INITIAL_LIMIT && (
                <button
                    type="button"
                    className="link-btn"
                    onClick={() => setExpanded(!expanded)}
                >
                    {expanded ? "折りたたむ" : `すべて表示 (${errors.length}件)`}
                </button>
            )}
        </section>
    );
}
