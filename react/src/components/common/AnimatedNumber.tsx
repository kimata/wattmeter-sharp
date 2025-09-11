import React, { useEffect, useState, useRef } from 'react';
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
  const lastUpdateTime = useRef<number>(Date.now());
  const isDocumentVisible = useRef<boolean>(true);
  const spring = useSpring(isInitialized ? value : value, {
    duration: duration * 1000,
    bounce: 0.1
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

  // ドキュメントの可視状態を監視
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.hidden) {
        isDocumentVisible.current = false;
      } else {
        // タブがアクティブになった時
        isDocumentVisible.current = true;
        const timeSinceLastUpdate = Date.now() - lastUpdateTime.current;

        // 5秒以上バックグラウンドにいた場合はアニメーションをスキップ
        if (timeSinceLastUpdate > 5000) {
          spring.jump(value);
        }
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [value, spring]);

  useEffect(() => {
    lastUpdateTime.current = Date.now();

    if (!isInitialized) {
      spring.jump(value);
      setIsInitialized(true);
    } else {
      // ドキュメントが非表示の場合はアニメーションをスキップ
      if (document.hidden) {
        spring.jump(value);
      } else {
        spring.set(value);
      }
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
