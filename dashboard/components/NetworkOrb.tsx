"use client";

import { motion } from "framer-motion";

/**
 * Abstract animated network orb — AI brain at center with orbiting signal nodes.
 * Non-technical visual hook for the login page. No labels, no jargon.
 */
const NODES = [
    { angle: 0,   r: 110, size: 6, delay: 0 },
    { angle: 45,  r: 130, size: 4, delay: 0.3 },
    { angle: 90,  r: 100, size: 7, delay: 0.6 },
    { angle: 135, r: 140, size: 5, delay: 0.9 },
    { angle: 180, r: 115, size: 6, delay: 1.2 },
    { angle: 225, r: 135, size: 4, delay: 1.5 },
    { angle: 270, r: 105, size: 7, delay: 1.8 },
    { angle: 315, r: 145, size: 5, delay: 2.1 },
];

const CX = 200;
const CY = 200;

function polarToXY(angleDeg: number, radius: number) {
    const a = (angleDeg * Math.PI) / 180;
    return { x: CX + radius * Math.cos(a), y: CY + radius * Math.sin(a) };
}

export default function NetworkOrb() {
    return (
        <div className="network-orb" aria-hidden="true">
            <svg viewBox="0 0 400 400" width="100%" height="100%" preserveAspectRatio="xMidYMid meet">
                <defs>
                    <radialGradient id="orb-core-glow" cx="50%" cy="50%" r="50%">
                        <stop offset="0%" stopColor="#00D4FF" stopOpacity="0.45" />
                        <stop offset="60%" stopColor="#00D4FF" stopOpacity="0.10" />
                        <stop offset="100%" stopColor="#00D4FF" stopOpacity="0" />
                    </radialGradient>
                    <linearGradient id="orb-core-grad" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stopColor="#00E5FF" />
                        <stop offset="50%" stopColor="#00B8D4" />
                        <stop offset="100%" stopColor="#0066FF" />
                    </linearGradient>
                    <radialGradient id="node-grad" cx="50%" cy="50%" r="50%">
                        <stop offset="0%" stopColor="#00E5FF" />
                        <stop offset="100%" stopColor="#0066FF" />
                    </radialGradient>
                </defs>

                {/* Soft ambient glow */}
                <circle cx={CX} cy={CY} r={160} fill="url(#orb-core-glow)" />

                {/* Connection lines core -> orbital nodes */}
                {NODES.map((n, i) => {
                    const p = polarToXY(n.angle, n.r);
                    return (
                        <motion.line
                            key={`line-${i}`}
                            x1={CX}
                            y1={CY}
                            x2={p.x}
                            y2={p.y}
                            stroke="url(#orb-core-grad)"
                            strokeWidth={0.8}
                            opacity={0.3}
                            animate={{ opacity: [0.15, 0.5, 0.15] }}
                            transition={{ duration: 3, repeat: Infinity, delay: n.delay * 0.3, ease: "easeInOut" }}
                        />
                    );
                })}

                {/* Outer rotating dashed ring */}
                <motion.circle
                    cx={CX}
                    cy={CY}
                    r={150}
                    fill="none"
                    stroke="rgba(0,184,212,0.25)"
                    strokeWidth={1}
                    strokeDasharray="3 8"
                    style={{ originX: `${CX}px`, originY: `${CY}px` }}
                    animate={{ rotate: 360 }}
                    transition={{ duration: 40, repeat: Infinity, ease: "linear" }}
                />

                {/* Inner counter-rotating dashed ring */}
                <motion.circle
                    cx={CX}
                    cy={CY}
                    r={75}
                    fill="none"
                    stroke="rgba(0,212,255,0.35)"
                    strokeWidth={1}
                    strokeDasharray="2 6"
                    style={{ originX: `${CX}px`, originY: `${CY}px` }}
                    animate={{ rotate: -360 }}
                    transition={{ duration: 22, repeat: Infinity, ease: "linear" }}
                />

                {/* Expanding pulse rings */}
                {[0, 1, 2].map((i) => (
                    <motion.circle
                        key={`pulse-${i}`}
                        cx={CX}
                        cy={CY}
                        fill="none"
                        stroke="#00D4FF"
                        strokeWidth={1.5}
                        initial={{ r: 50, opacity: 0.5 }}
                        animate={{ r: [50, 160], opacity: [0.5, 0] }}
                        transition={{ duration: 3, repeat: Infinity, ease: "easeOut", delay: i * 1.0 }}
                    />
                ))}

                {/* Orbital nodes with traveling particles */}
                {NODES.map((n, i) => {
                    const p = polarToXY(n.angle, n.r);
                    return (
                        <g key={`node-${i}`}>
                            <motion.circle
                                cx={p.x}
                                cy={p.y}
                                r={n.size}
                                fill="url(#node-grad)"
                                animate={{ scale: [1, 1.4, 1], opacity: [0.6, 1, 0.6] }}
                                transition={{ duration: 2.2, repeat: Infinity, delay: n.delay * 0.2, ease: "easeInOut" }}
                                style={{ originX: `${p.x}px`, originY: `${p.y}px` }}
                            />
                            {/* Traveling particle from node to core */}
                            <motion.circle
                                r={2.5}
                                fill="#00E5FF"
                                animate={{
                                    cx: [p.x, CX],
                                    cy: [p.y, CY],
                                    opacity: [0, 1, 0],
                                }}
                                transition={{ duration: 2.5, repeat: Infinity, delay: n.delay * 0.3 + 0.5, ease: "easeIn" }}
                            />
                        </g>
                    );
                })}

                {/* Core hexagon */}
                <motion.g
                    style={{ originX: `${CX}px`, originY: `${CY}px` }}
                    animate={{ rotate: 360 }}
                    transition={{ duration: 14, repeat: Infinity, ease: "linear" }}
                >
                    <polygon
                        points={hexPoints(CX, CY, 38)}
                        fill="rgba(0, 212, 255, 0.06)"
                        stroke="url(#orb-core-grad)"
                        strokeWidth={2.5}
                    />
                    <polygon
                        points={hexPoints(CX, CY, 26)}
                        fill="rgba(0, 212, 255, 0.14)"
                        stroke="rgba(0, 229, 255, 0.7)"
                        strokeWidth={1.2}
                    />
                </motion.g>

                {/* Core center pulse */}
                <motion.circle
                    cx={CX}
                    cy={CY}
                    r={8}
                    fill="#00E5FF"
                    animate={{ scale: [1, 1.5, 1], opacity: [0.8, 1, 0.8] }}
                    transition={{ duration: 1.4, repeat: Infinity, ease: "easeInOut" }}
                    style={{ originX: `${CX}px`, originY: `${CY}px` }}
                />
                <motion.circle
                    cx={CX}
                    cy={CY}
                    r={8}
                    fill="none"
                    stroke="#00E5FF"
                    strokeWidth={1.5}
                    animate={{ r: [8, 20], opacity: [0.8, 0] }}
                    transition={{ duration: 1.4, repeat: Infinity, ease: "easeOut" }}
                />
            </svg>
        </div>
    );
}

function hexPoints(cx: number, cy: number, r: number): string {
    const pts: string[] = [];
    for (let i = 0; i < 6; i++) {
        const angle = (Math.PI / 3) * i - Math.PI / 2;
        pts.push(`${cx + r * Math.cos(angle)},${cy + r * Math.sin(angle)}`);
    }
    return pts.join(" ");
}
