"use client";
import { motion } from 'framer-motion';
import { ReactNode } from 'react';

interface AnimatedCardProps {
    children: ReactNode;
    className?: string;
    delay?: number;
    style?: React.CSSProperties;
}

export default function AnimatedCard({ children, className = 'card', delay = 0, style }: AnimatedCardProps) {
    return (
        <motion.div
            className={className}
            style={style}
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35, delay, ease: [0.4, 0, 0.2, 1] as const }}
            whileHover={{ y: -2, transition: { duration: 0.2 } }}
        >
            {children}
        </motion.div>
    );
}
