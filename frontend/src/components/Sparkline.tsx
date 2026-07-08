interface SparklineProps {
    values: (number | null)[];
    width?: number;
    height?: number;
}

// 電力推移のミニグラフ。受信できなかった区間 (null) は線を切り、
// 下端に赤いティックを打って「切れていた時間帯」を見えるようにする。
export function Sparkline({ values, width = 160, height = 30 }: SparklineProps) {
    if (values.length < 2) {
        return null;
    }

    const numeric = values.filter((v): v is number => v !== null);
    if (numeric.length === 0) {
        return null;
    }

    const max = Math.max(...numeric, 1);
    const min = Math.min(...numeric, 0);
    const span = max - min || 1;

    const stepX = width / (values.length - 1);
    const scaleY = (v: number) => height - 2 - ((v - min) / span) * (height - 6);

    const segments: string[] = [];
    let current: string[] = [];
    values.forEach((v, i) => {
        if (v === null) {
            if (current.length > 1) segments.push(current.join(" "));
            current = [];
        } else {
            current.push(`${(i * stepX).toFixed(1)},${scaleY(v).toFixed(1)}`);
        }
    });
    if (current.length > 1) segments.push(current.join(" "));

    const gapTicks = values
        .map((v, i) => (v === null ? i : null))
        .filter((i): i is number => i !== null);

    return (
        <svg
            className="device-spark"
            width="100%"
            height={height}
            viewBox={`0 0 ${width} ${height}`}
            preserveAspectRatio="none"
            aria-hidden="true"
        >
            {segments.map((points, i) => (
                <polyline
                    key={i}
                    points={points}
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.6"
                    strokeLinejoin="round"
                    strokeLinecap="round"
                />
            ))}
            {gapTicks.map((i) => (
                <line
                    key={`gap-${i}`}
                    x1={i * stepX}
                    y1={height - 2}
                    x2={i * stepX}
                    y2={height}
                    stroke="var(--bad)"
                    strokeOpacity="0.45"
                    strokeWidth={Math.max(stepX * 0.8, 1)}
                />
            ))}
        </svg>
    );
}
