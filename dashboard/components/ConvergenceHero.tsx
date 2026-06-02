"use client";

import { motion } from "framer-motion";

const TOWERS = [
    { y: 60 },
    { y: 130 },
    { y: 220 },
    { y: 290 },
];

const SUBSCRIBERS = [
    { y: 60 },
    { y: 130 },
    { y: 220 },
    { y: 290 },
];

const TOWER_X = 80;
const SUB_X = 520;
const CORE_X = 300;
const CORE_Y = 175;

function curve(x1: number, y1: number, x2: number, y2: number) {
    const mx = (x1 + x2) / 2;
    return `M ${x1} ${y1} C ${mx} ${y1}, ${mx} ${y2}, ${x2} ${y2}`;
}

export default function ConvergenceHero() {
    return (
        <div className="convergence-hero" aria-hidden="true">
            <svg
                viewBox="0 0 600 360"
                width="100%"
                height="100%"
                preserveAspectRatio="xMidYMid meet"
                role="img"
                aria-label="OSS to CEM convergence illustration"
            >
                <defs>
                    <linearGradient id="beamGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                        <stop offset="0%" stopColor="#00E5FF" stopOpacity="0.1" />
                        <stop offset="50%" stopColor="#00D4FF" stopOpacity="1" />
                        <stop offset="100%" stopColor="#0066FF" stopOpacity="0.1" />
                    </linearGradient>
                    <linearGradient id="coreGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stopColor="#00E5FF" />
                        <stop offset="50%" stopColor="#00D4FF" />
                        <stop offset="100%" stopColor="#0066FF" />
                    </linearGradient>
                    <radialGradient id="coreGlow" cx="50%" cy="50%" r="50%">
                        <stop offset="0%" stopColor="#00D4FF" stopOpacity="0.4" />
                        <stop offset="100%" stopColor="#00D4FF" stopOpacity="0" />
                    </radialGradient>
                </defs>

                {/* Column labels */}
                <text
                    x={TOWER_X}
                    y={28}
                    textAnchor="middle"
                    fill="currentColor"
                    fontFamily="'Fira Code', monospace"
                    fontSize="10"
                    letterSpacing="2"
                >
                    OSS · CELLS
                </text>
                <text
                    x={SUB_X}
                    y={28}
                    textAnchor="middle"
                    fill="currentColor"
                    fontFamily="'Fira Code', monospace"
                    fontSize="10"
                    letterSpacing="2"
                >
                    CEM · SUBSCRIBERS
                </text>
                <text
                    x={CORE_X}
                    y={28}
                    textAnchor="middle"
                    fill="#007DBA"
                    fontFamily="'Fira Code', monospace"
                    fontSize="10"
                    letterSpacing="3"
                    fontWeight="600"
                >
                    NeXo CORE
                </text>

                {/* OSS tower nodes */}
                {TOWERS.map((t, i) => (
                    <g key={`tower-${i}`}>
                        <motion.circle
                            cx={TOWER_X}
                            cy={t.y}
                            r={6}
                            fill="rgba(0,212,255,0.18)"
                            stroke="#00D4FF"
                            strokeWidth={1.5}
                            animate={{ r: [6, 11, 6], opacity: [0.7, 1, 0.7] }}
                            transition={{
                                duration: 2.4,
                                repeat: Infinity,
                                ease: "easeInOut",
                                delay: i * 0.3,
                            }}
                        />
                        <circle cx={TOWER_X} cy={t.y} r={3} fill="#00D4FF" />
                        {/* tower stem hint */}
                        <line
                            x1={TOWER_X}
                            y1={t.y - 12}
                            x2={TOWER_X}
                            y2={t.y - 18}
                            stroke="rgba(0,212,255,0.4)"
                            strokeWidth={1}
                        />
                        <line
                            x1={TOWER_X - 4}
                            y1={t.y - 16}
                            x2={TOWER_X + 4}
                            y2={t.y - 16}
                            stroke="rgba(0,212,255,0.4)"
                            strokeWidth={1}
                        />
                    </g>
                ))}

                {/* Subscriber nodes */}
                {SUBSCRIBERS.map((s, i) => (
                    <g key={`sub-${i}`}>
                        <motion.circle
                            cx={SUB_X}
                            cy={s.y}
                            r={9}
                            fill="rgba(0,102,255,0.12)"
                            stroke="#0066FF"
                            strokeWidth={1.5}
                            animate={{ opacity: [0.4, 1, 0.4] }}
                            transition={{
                                duration: 4,
                                repeat: Infinity,
                                ease: "easeInOut",
                                delay: 1.8 + i * 0.3,
                            }}
                        />
                        {/* user glyph */}
                        <circle cx={SUB_X} cy={s.y - 2} r={2.2} fill="#0066FF" />
                        <path
                            d={`M ${SUB_X - 3.5} ${s.y + 4} q 3.5 -3 7 0`}
                            stroke="#0066FF"
                            strokeWidth={1.2}
                            fill="none"
                        />
                    </g>
                ))}

                {/* Beams: tower -> core */}
                {TOWERS.map((t, i) => (
                    <g key={`beam-in-${i}`}>
                        {/* Static faint guide */}
                        <path
                            d={curve(TOWER_X, t.y, CORE_X, CORE_Y)}
                            stroke="rgba(0,212,255,0.10)"
                            strokeWidth={1}
                            fill="none"
                        />
                        {/* Animated beam draw */}
                        <motion.path
                            d={curve(TOWER_X, t.y, CORE_X, CORE_Y)}
                            stroke="url(#beamGradient)"
                            strokeWidth={1.8}
                            fill="none"
                            strokeLinecap="round"
                            initial={{ pathLength: 0, opacity: 0 }}
                            animate={{ pathLength: [0, 1, 1], opacity: [0, 1, 0] }}
                            transition={{
                                duration: 2.4,
                                repeat: Infinity,
                                ease: "easeInOut",
                                delay: i * 0.25,
                            }}
                        />
                        {/* Traveling particle */}
                        <motion.circle
                            r={3}
                            fill="#00E5FF"
                            initial={{ opacity: 0 }}
                            animate={{
                                cx: [TOWER_X, (TOWER_X + CORE_X) / 2, CORE_X],
                                cy: [t.y, t.y, CORE_Y],
                                opacity: [0, 1, 0],
                            }}
                            transition={{
                                duration: 2.4,
                                repeat: Infinity,
                                ease: "easeIn",
                                delay: i * 0.25,
                            }}
                        />
                    </g>
                ))}

                {/* Beams: core -> subscriber */}
                {SUBSCRIBERS.map((s, i) => (
                    <g key={`beam-out-${i}`}>
                        <path
                            d={curve(CORE_X, CORE_Y, SUB_X, s.y)}
                            stroke="rgba(0,102,255,0.10)"
                            strokeWidth={1}
                            fill="none"
                        />
                        <motion.path
                            d={curve(CORE_X, CORE_Y, SUB_X, s.y)}
                            stroke="url(#beamGradient)"
                            strokeWidth={1.8}
                            fill="none"
                            strokeLinecap="round"
                            initial={{ pathLength: 0, opacity: 0 }}
                            animate={{ pathLength: [0, 1, 1], opacity: [0, 1, 0] }}
                            transition={{
                                duration: 2.4,
                                repeat: Infinity,
                                ease: "easeInOut",
                                delay: 1.0 + i * 0.25,
                            }}
                        />
                        {/* Traveling particle out */}
                        <motion.circle
                            r={3}
                            fill="#0066FF"
                            initial={{ opacity: 0 }}
                            animate={{
                                cx: [CORE_X, (CORE_X + SUB_X) / 2, SUB_X],
                                cy: [CORE_Y, s.y, s.y],
                                opacity: [0, 1, 0],
                            }}
                            transition={{
                                duration: 2.4,
                                repeat: Infinity,
                                ease: "easeIn",
                                delay: 1.0 + i * 0.25,
                            }}
                        />
                    </g>
                ))}

                {/* Expanding pulse rings around core */}
                {[0, 1, 2].map((i) => (
                    <motion.circle
                        key={`pulse-${i}`}
                        cx={CORE_X}
                        cy={CORE_Y}
                        fill="none"
                        stroke="#00D4FF"
                        strokeWidth={1.5}
                        initial={{ r: 28, opacity: 0.6 }}
                        animate={{ r: [28, 80], opacity: [0.6, 0] }}
                        transition={{
                            duration: 2.4,
                            repeat: Infinity,
                            ease: "easeOut",
                            delay: i * 0.8,
                        }}
                    />
                ))}

                {/* Core glow */}
                <circle cx={CORE_X} cy={CORE_Y} r={60} fill="url(#coreGlow)" />

                {/* Outer rotating dashed ring */}
                <motion.g
                    style={{ originX: `${CORE_X}px`, originY: `${CORE_Y}px` }}
                    animate={{ rotate: 360 }}
                    transition={{ duration: 24, repeat: Infinity, ease: "linear" }}
                >
                    <circle
                        cx={CORE_X}
                        cy={CORE_Y}
                        r={48}
                        fill="none"
                        stroke="rgba(0,184,212,0.32)"
                        strokeWidth={1}
                        strokeDasharray="2 6"
                    />
                </motion.g>

                {/* Core hexagon (faster rotation) */}
                <motion.g
                    style={{ originX: `${CORE_X}px`, originY: `${CORE_Y}px` }}
                    animate={{ rotate: 360 }}
                    transition={{ duration: 10, repeat: Infinity, ease: "linear" }}
                >
                    <polygon
                        points={hexPoints(CORE_X, CORE_Y, 32)}
                        fill="none"
                        stroke="url(#coreGradient)"
                        strokeWidth={2}
                    />
                    <polygon
                        points={hexPoints(CORE_X, CORE_Y, 22)}
                        fill="rgba(0,212,255,0.12)"
                        stroke="rgba(0,212,255,0.7)"
                        strokeWidth={1.2}
                    />
                </motion.g>

                {/* Core counter-rotating inner ring */}
                <motion.g
                    style={{ originX: `${CORE_X}px`, originY: `${CORE_Y}px` }}
                    animate={{ rotate: -360 }}
                    transition={{ duration: 14, repeat: Infinity, ease: "linear" }}
                >
                    <circle
                        cx={CORE_X}
                        cy={CORE_Y}
                        r={14}
                        fill="none"
                        stroke="rgba(0,229,255,0.85)"
                        strokeWidth={1.2}
                        strokeDasharray="3 4"
                    />
                </motion.g>

                {/* Core center dot — stronger pulse */}
                <motion.circle
                    cx={CORE_X}
                    cy={CORE_Y}
                    r={5}
                    fill="#00E5FF"
                    animate={{ scale: [1, 1.6, 1], opacity: [0.85, 1, 0.85] }}
                    transition={{ duration: 1.4, repeat: Infinity, ease: "easeInOut" }}
                    style={{ originX: `${CORE_X}px`, originY: `${CORE_Y}px` }}
                />

                {/* Core halo */}
                <motion.circle
                    cx={CORE_X}
                    cy={CORE_Y}
                    r={5}
                    fill="none"
                    stroke="#00E5FF"
                    strokeWidth={1}
                    animate={{ r: [5, 12], opacity: [0.7, 0] }}
                    transition={{ duration: 1.4, repeat: Infinity, ease: "easeOut" }}
                />
            </svg>

            <p className="convergence-hero-caption">
                Closing the loop between network signals and customer experience.
            </p>
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
