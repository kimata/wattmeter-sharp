import dayjs from "dayjs";

import { SensorTable } from "./SensorTable";
import { CommunicationErrorChart } from "./CommunicationErrorChart";
import { CommunicationErrorTable } from "./CommunicationErrorTable";
import { UnknownDevices } from "./UnknownDevices";
import type { DeviceView } from "../App";
import type { CommunicationErrorResponse, UnknownDevice } from "../types";

interface ConnectionStatusProps {
    devices: DeviceView[];
    errors: CommunicationErrorResponse | null;
    unknownDevices: UnknownDevice[];
    startDate: string | null;
    nowSec: number;
}

export function ConnectionStatus({
    devices,
    errors,
    unknownDevices,
    startDate,
    nowSec,
}: ConnectionStatusProps) {
    const count = (state: DeviceView["state"]) =>
        devices.filter((d) => d.state === state).length;

    const online = count("online");
    const unstable = count("unstable");
    const disconnected = count("disconnected");
    const lost = count("lost");

    return (
        <div data-testid="connection-status">
            <section className="card">
                <h2 className="card-title">
                    接続サマリー
                    {startDate && (
                        <span className="card-note">
                            計測開始: {dayjs(startDate).format("YYYY年M月D日")} (
                            {dayjs(nowSec * 1000).diff(dayjs(startDate), "day")}日前)
                        </span>
                    )}
                </h2>
                <div className="summary-tiles">
                    <div className="summary-tile good">
                        <div className="num">{online}</div>
                        <div className="label">接続中</div>
                    </div>
                    <div className="summary-tile warn">
                        <div className="num">{unstable}</div>
                        <div className="label">不安定 (受信率 90% 未満)</div>
                    </div>
                    <div className="summary-tile bad">
                        <div className="num">{disconnected}</div>
                        <div className="label">切断 (15分〜24時間)</div>
                    </div>
                    <div className="summary-tile bad">
                        <div className="num">{lost}</div>
                        <div className="label">長期切断 (24時間以上)</div>
                    </div>
                </div>
            </section>

            <UnknownDevices devices={unknownDevices} />

            <SensorTable devices={devices} nowSec={nowSec} />

            {errors ? (
                <>
                    <CommunicationErrorChart histogram={errors.histogram} />
                    <CommunicationErrorTable errors={errors.latest_errors} />
                </>
            ) : (
                <section className="card">
                    <div className="skeleton" style={{ height: "200px" }} />
                </section>
            )}
        </div>
    );
}
