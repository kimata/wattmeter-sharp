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
  duration = 30.0,
  useComma = false
}) => {
  const [displayValue, setDisplayValue] = useState(value);
  const spring = useSpring(value, {
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
    spring.set(value);
  }, [value, spring]);

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
