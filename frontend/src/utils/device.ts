// デバイス名のキーワードからアイコン (絵文字) を推定する
const ICON_RULES: [RegExp, string][] = [
    [/エアレーション/, "🫧"],
    [/ライト|照明/, "💡"],
    [/温度/, "🌡️"],
    [/水槽/, "🐠"],
    [/エアコン/, "❄️"],
    [/冷蔵庫/, "🧊"],
    [/洗濯/, "🧺"],
    [/食洗/, "🍽️"],
    [/レンジ|オーブン/, "♨️"],
    [/ポット|ケトル/, "☕"],
    [/テレビ|TV/, "📺"],
    [/ディスプレイ|モニタ/, "🖥️"],
    [/PC|パソコン/, "💻"],
    [/カメラ/, "📹"],
    [/トイレ/, "🚽"],
    [/学習|デスク/, "📚"],
];

export function deviceIcon(name: string): string {
    for (const [pattern, icon] of ICON_RULES) {
        if (pattern.test(name)) {
            return icon;
        }
    }
    return "🔌";
}

// ---------- 接続状態 ----------
//
// センサーは約 6 分周期で送信するワイヤレス接続。
//   接続中   : 15 分以内に受信 (2 周期分の欠落までは許容)
//   不安定   : 受信はしているが直近 24h の受信率が 90% 未満
//   切断     : 15 分〜24 時間受信なし
//   長期切断 : 24 時間以上受信なし (恒久的な切断の疑い)

export type ConnState = "online" | "unstable" | "disconnected" | "lost";

const DISCONNECT_THRESHOLD_SEC = 15 * 60;
const LOST_THRESHOLD_SEC = 24 * 3600;
const UNSTABLE_AVAILABILITY = 90;

export function connectionState(
    lastReceivedTs: number | null,
    availability24h: number,
    nowSec: number,
): ConnState {
    if (lastReceivedTs === null) return "lost";

    const age = nowSec - lastReceivedTs;
    if (age > LOST_THRESHOLD_SEC) return "lost";
    if (age > DISCONNECT_THRESHOLD_SEC) return "disconnected";
    if (availability24h < UNSTABLE_AVAILABILITY) return "unstable";
    return "online";
}

export const CONN_STATE_LABEL: Record<ConnState, string> = {
    online: "接続中",
    unstable: "不安定",
    disconnected: "切断",
    lost: "長期切断",
};

export const CONN_STATE_CHIP: Record<ConnState, string> = {
    online: "good",
    unstable: "warn",
    disconnected: "bad",
    lost: "bad",
};

// ---------- 表示フォーマット ----------

export function formatDuration(sec: number): string {
    if (sec < 60) return "1分未満";
    if (sec < 3600) return `${Math.floor(sec / 60)}分`;
    if (sec < 86400) return `${Math.floor(sec / 3600)}時間`;
    return `${Math.floor(sec / 86400)}日`;
}

// 「たった今」「3分前」のような相対表記
export function formatAgo(sec: number): string {
    if (sec < 60) return "たった今";
    return `${formatDuration(sec)}前`;
}

export function formatWatt(watt: number): string {
    return Math.round(watt).toLocaleString("ja-JP");
}

export function formatKwh(wh: number): string {
    const kwh = wh / 1000;
    return kwh >= 100
        ? Math.round(kwh).toLocaleString("ja-JP")
        : kwh.toFixed(1);
}

export function formatYen(yen: number): string {
    return Math.round(yen).toLocaleString("ja-JP");
}
