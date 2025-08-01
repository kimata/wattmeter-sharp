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
  const [displayValue, setDisplayValue] = useState(value);
  const [isInitialized, setIsInitialized] = useState(false);
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

  useEffect(() => {
    if (!isInitialized) {
      spring.jump(value);
      setIsInitialized(true);
    } else {
      spring.set(value);
    }
  }, [value, spring, isInitialized]);

  useEffect(() => {
    const unsubscribe = display.on('change', (latest) => {
      const numericValue = useComma ? parseFloat(latest.replace(/,/g, '')) : parseFloat(latest);
      setDisplayValue(numericValue);
    });
    return unsubscribe;
  }, [display, useComma]);

  return (
    <motion.span
      className={className}
      initial={{ scale: 1, y: 0 }}
      animate={{
        scale: value !== displayValue ? [1, 1.05, 1] : 1,
        y: value !== displayValue ? [0, -8, 0] : 0
      }}
      transition={{ duration: 0.3 }}
    >
      {display.get()}
    </motion.span>
  );
};
