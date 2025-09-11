import React, { useEffect, useState } from 'react';
import { motion, useSpring, useTransform } from 'framer-motion';

interface AnimatedNumberProps {
  value: number;
  decimals?: number;
  className?: string;
  duration?: number;
  useComma?: boolean;
}

export const AnimatedNumber: React.FC<AnimatedNumberProps> = ({
  value,
  decimals = 1,
  className = '',
  duration = 3.0,
  useComma = false
}) => {
  const [isInitialized, setIsInitialized] = useState(false);
  const [previousValue, setPreviousValue] = useState(value);
  // 初期値を明確にvalueに設定
  // bounceを無効にしてオーバーシュートを防ぐ
  const spring = useSpring(value, {
    duration: duration * 1000,
    bounce: 0,  // バウンスを無効化
    damping: 30,  // 減衰を強める
    stiffness: 100  // 剛性を調整
  });

  const display = useTransform(spring, (latest) => {
    const fixedValue = latest.toFixed(decimals);
    if (useComma) {
      return parseFloat(fixedValue).toLocaleString('ja-JP', {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals
      });
    }
    return fixedValue;
  });

  useEffect(() => {
    if (!isInitialized) {
      // 初回はアニメーションなしで値を設定
      spring.jump(value);
      setIsInitialized(true);
    } else {
      // 2回目以降はアニメーション付きで変更
      spring.set(value);
    }
    setPreviousValue(value);
  }, [value, spring, isInitialized]);

  return (
    <motion.span
      className={className}
      initial={{ scale: 1, y: 0 }}
      animate={{
        scale: value !== previousValue ? [1, 1.05, 1] : 1,
        y: value !== previousValue ? [0, -8, 0] : 0
      }}
      transition={{ duration: 0.3 }}
    >
      {display}
    </motion.span>
  );
};
