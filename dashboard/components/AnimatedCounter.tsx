"use client";
import { motion, useMotionValue, useTransform, animate } from 'framer-motion';
import { useEffect, useRef } from 'react';

interface AnimatedCounterProps {
    value: number;
    decimals?: number;
    suffix?: string;
    prefix?: string;
    className?: string;
    style?: React.CSSProperties;
    duration?: number;
}

export default function AnimatedCounter({
    value,
    decimals = 0,
    suffix = '',
    prefix = '',
    className = 'stat-value',
    style,
    duration = 1.2,
}: AnimatedCounterProps) {
    const motionVal = useMotionValue(0);
    const ref = useRef<HTMLSpanElement>(null);

    useEffect(() => {
        const controls = animate(motionVal, value, {
            duration,
            ease: [0.4, 0, 0.2, 1] as const,
            onUpdate: (v) => {
                if (ref.current) {
                    ref.current.textContent = prefix + v.toFixed(decimals) + suffix;
                }
            },
        });
        return () => controls.stop();
    }, [value, decimals, suffix, prefix, duration, motionVal]);

    return (
        <motion.span
            ref={ref}
            className={className}
            style={style}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
        >
            {prefix}{value.toFixed(decimals)}{suffix}
        </motion.span>
    );
}
