import type { UnknownDevice } from "../types";

interface UnknownDevicesProps {
    devices: UnknownDevice[];
}

// 観測されたが device.yaml に未登録のデバイスを表示し、登録用のスニペットを提示する
export function UnknownDevices({ devices }: UnknownDevicesProps) {
    if (devices.length === 0) {
        return null;
    }

    const snippet = devices
        .map((d) => `- addr: "${d.addr}"\n  name: 新しいデバイス (${d.dev_id})`)
        .join("\n");

    return (
        <section className="card" data-testid="unknown-devices">
            <h2 className="card-title">
                ❓ 未登録のデバイス
                <span className="card-note">
                    電力データを受信していますが device.yaml に定義がありません
                </span>
            </h2>
            <div className="table-wrap">
                <table className="data-table">
                    <thead>
                        <tr>
                            <th className="plain">dev_id</th>
                            <th className="plain">IEEE アドレス</th>
                        </tr>
                    </thead>
                    <tbody>
                        {devices.map((d) => (
                            <tr key={d.addr}>
                                <td>{d.dev_id}</td>
                                <td>{d.addr}</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
            <p className="card-note" style={{ marginTop: "0.7rem" }}>
                device.yaml に以下を追記して名前を付けると計測対象になります:
            </p>
            <pre
                style={{
                    background: "var(--surface-2)",
                    padding: "0.7rem 1rem",
                    borderRadius: "8px",
                    fontSize: "0.8rem",
                    overflowX: "auto",
                }}
            >
                {snippet}
            </pre>
        </section>
    );
}
