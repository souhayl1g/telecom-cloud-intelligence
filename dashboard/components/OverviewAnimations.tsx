"use client";
import { motion } from 'framer-motion';
import { ReactNode } from 'react';

const staggerContainer = {
    hidden: { opacity: 0 },
    show: {
        opacity: 1,
        transition: { staggerChildren: 0.08 },
    },
};

const staggerItem = {
    hidden: { opacity: 0, y: 20, scale: 0.97 },
    show: {
        opacity: 1, y: 0, scale: 1,
        transition: { duration: 0.4, ease: [0.4, 0, 0.2, 1] as const },
    },
};

export function StaggerGrid({ children, className }: { children: ReactNode; className?: string }) {
    return (
        <motion.div
            className={className}
            variants={staggerContainer}
            initial="hidden"
            animate="show"
        >
            {children}
        </motion.div>
    );
}

export function StaggerItem({ children, className, style }: { children: ReactNode; className?: string; style?: React.CSSProperties }) {
    return (
        <motion.div
            className={className}
            style={style}
            variants={staggerItem}
            whileHover={{ y: -3, transition: { duration: 0.2 } }}
        >
            {children}
        </motion.div>
    );
}

export function FadeIn({ children, className, delay = 0 }: { children: ReactNode; className?: string; delay?: number }) {
    return (
        <motion.div
            className={className}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay, ease: [0.4, 0, 0.2, 1] as const }}
        >
            {children}
        </motion.div>
    );
}

export function SlideInBanner({ children, className }: { children: ReactNode; className?: string }) {
    return (
        <motion.div
            className={className}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5, delay: 0.3, ease: [0.4, 0, 0.2, 1] as const }}
            whileHover={{ scale: 1.005, transition: { duration: 0.2 } }}
        >
            {children}
        </motion.div>
    );
}
