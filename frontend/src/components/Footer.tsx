import dayjs from "dayjs";
import { version as reactVersion } from "react";

import { useApi } from "../hooks/useApi";
import { buildApiUrl } from "../config/constants";
import type { SysInfo } from "../types";

interface FooterProps {
    updateTime: string;
}

export function Footer({ updateTime }: FooterProps) {
    const buildDate = dayjs(
        import.meta.env.VITE_BUILD_DATE || new Date().toISOString(),
    );
    const { data: sysInfo } = useApi<SysInfo>(buildApiUrl("sysinfo"), {
        interval: 300000,
    });

    return (
        <footer className="app-footer" data-testid="footer">
            <div>
                <div>最終更新: {updateTime}</div>
                {sysInfo?.image_build_date && (
                    <div>
                        イメージビルド:{" "}
                        {dayjs(sysInfo.image_build_date).format("YYYY/MM/DD HH:mm")}
                    </div>
                )}
                <div>
                    フロントエンドビルド: {buildDate.format("YYYY/MM/DD HH:mm")} (React{" "}
                    {reactVersion})
                </div>
            </div>
            <a href="https://github.com/kimata/wattmeter-sharp">GitHub ↗</a>
        </footer>
    );
}
