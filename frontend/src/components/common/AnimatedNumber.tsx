import React, { useEffect, useState } from "react";
import { motion, useSpring, useTransform } from "framer-motion";

interface AnimatedNumberProps {
    value: number;
    decimals?: number;
    className?: string;
    duration?: number;
    useComma?: boolean;
}

// スプリングでカウントアップし、値の変化時に軽くバウンスする数値表示。
export const AnimatedNumber: React.FC<AnimatedNumberProps> = ({
    value,
    decimals = 1,
    className = "",
    duration = 1.5,
    useComma = false,
}) => {
    const [isInitialized, setIsInitialized] = useState(false);
    const [previousValue, setPreviousValue] = useState(value);
    // bounceを無効にしてオーバーシュートを防ぐ
    const spring = useSpring(value, {
        duration: duration * 1000,
        bounce: 0,
        damping: 30,
        stiffness: 100,
    });

    const display = useTransform(spring, (latest) => {
        const fixedValue = latest.toFixed(decimals);
        if (useComma) {
            return parseFloat(fixedValue).toLocaleString("ja-JP", {
                minimumFractionDigits: decimals,
                maximumFractionDigits: decimals,
            });
        }
        return fixedValue;
    });

    useEffect(() => {
        const currentValue = spring.get();

        if (!isInitialized) {
            // 初回はアニメーションなしで値を設定
            spring.jump(value);
            setIsInitialized(true);
        } else if (
            currentValue < 0 ||
            Math.abs(value - currentValue) > Math.abs(value) * 2 + 1
        ) {
            // 異常な状態を検出した場合はアニメーションをスキップ
            // (バックグラウンドタブでのスプリング状態異常への対策)
            spring.jump(value);
        } else {
            spring.set(value);
        }
        setPreviousValue(value);
    }, [value, spring, isInitialized]);

    return (
        <motion.span
            className={className}
            initial={{ scale: 1, y: 0 }}
            animate={{
                scale: value !== previousValue ? [1, 1.04, 1] : 1,
                y: value !== previousValue ? [0, -4, 0] : 0,
            }}
            transition={{ duration: 0.35 }}
            style={{ display: "inline-block" }}
        >
            {display}
        </motion.span>
    );
};
