"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { geoMercator, geoPath } from "d3-geo";
import type { FeatureCollection, Geometry } from "geojson";
import { motion, AnimatePresence } from "framer-motion";
import { MapPin, AlertTriangle, Play, Pause, Activity, Radio, Layers } from "lucide-react";
import tunisiaGeo from "../lib/tunisia-geojson.json";
import type { GovernorateRow } from "../lib/tunisia-areas";

type Metric = "anomaly_count" | "rate" | "cell_count";

interface Props {
    rows: GovernorateRow[];
    metric?: Metric;
    width?: number;
    height?: number;
    onSelect?: (governorate: string | null) => void;
    selected?: string | null;
    /** Optional time-series frames; if supplied a play/pause scrubber renders. */
    frames?: { label: string; rows: GovernorateRow[] }[];
}

interface FeatureProps {
    shapeName: string;
    shapeISO: string;
}

/** Sequential colormap (slate-100 → sky → amber → red → deep red). */
const STOPS = [
    [241, 245, 249],
    [186, 230, 253],
    [253, 186, 116],
    [248, 113, 113],
    [185, 28, 28],
];

function lerp(a: number, b: number, t: number) { return a + (b - a) * t; }

function colorForIntensity(t: number) {
    const v = Math.max(0, Math.min(1, t));
    const seg = v * (STOPS.length - 1);
    const i = Math.min(STOPS.length - 2, Math.floor(seg));
    const frac = seg - i;
    const r = Math.round(lerp(STOPS[i][0], STOPS[i + 1][0], frac));
    const g = Math.round(lerp(STOPS[i][1], STOPS[i + 1][1], frac));
    const b = Math.round(lerp(STOPS[i][2], STOPS[i + 1][2], frac));
    return `rgb(${r}, ${g}, ${b})`;
}

function pickMetric(r: GovernorateRow | undefined, m: Metric): number {
    if (!r) return 0;
    if (m === "rate") return r.rate;
    if (m === "cell_count") return r.cell_count;
    return r.anomaly_count;
}

const METRIC_LABEL: Record<Metric, string> = {
    anomaly_count: "Anomaly count",
    rate: "Anomaly rate (%)",
    cell_count: "Cells observed",
};

export default function TunisiaMap({
    rows,
    metric: initialMetric = "anomaly_count",
    width = 640,
    height = 760,
    onSelect,
    selected,
    frames,
}: Props) {
    const fc = tunisiaGeo as unknown as FeatureCollection<Geometry, FeatureProps>;
    const [metric, setMetric] = useState<Metric>(initialMetric);
    const [hovered, setHovered] = useState<{ name: string; x: number; y: number } | null>(null);

    // ── Animation state ────────────────────────────────────────────────────
    const [playing, setPlaying] = useState(false);
    const [frameIdx, setFrameIdx] = useState(0);
    const rafRef = useRef<number | null>(null);
    const lastTickRef = useRef<number>(0);

    useEffect(() => {
        if (!frames || frames.length <= 1 || !playing) return;
        const FRAME_MS = 900;
        const tick = (t: number) => {
            if (t - lastTickRef.current >= FRAME_MS) {
                lastTickRef.current = t;
                setFrameIdx((i) => (i + 1) % frames.length);
            }
            rafRef.current = requestAnimationFrame(tick);
        };
        rafRef.current = requestAnimationFrame(tick);
        return () => { if (rafRef.current) cancelAnimationFrame(rafRef.current); };
    }, [playing, frames]);

    const activeRows = frames && frames.length > 0 ? frames[frameIdx]?.rows ?? rows : rows;
    const activeFrameLabel = frames && frames.length > 0 ? frames[frameIdx]?.label : null;

    const valueByGov = useMemo(() => {
        const m = new Map<string, GovernorateRow>();
        for (const r of activeRows) m.set(r.governorate as string, r);
        return m;
    }, [activeRows]);

    const maxValue = useMemo(() => {
        let max = 0;
        for (const r of activeRows) {
            const v = pickMetric(r, metric);
            if (v > max) max = v;
        }
        return max || 1;
    }, [activeRows, metric]);

    const projection = useMemo(
        () => geoMercator().fitExtent([[12, 12], [width - 12, height - 60]], fc),
        [fc, width, height]
    );
    const pathGen = useMemo(() => geoPath(projection), [projection]);

    // Render hot polygons last so they sit on top.
    const orderedFeatures = useMemo(() => {
        return [...fc.features].sort((a, b) => {
            const va = pickMetric(valueByGov.get(a.properties.shapeName), metric);
            const vb = pickMetric(valueByGov.get(b.properties.shapeName), metric);
            return va - vb;
        });
    }, [fc.features, valueByGov, metric]);

    const totalAnoms = activeRows.reduce((s, r) => s + r.anomaly_count, 0);
    const totalCells = activeRows.reduce((s, r) => s + r.cell_count, 0);

    return (
        <div className="tunisia-map-wrap">
            {/* Toolbar */}
            <div className="tunisia-map-toolbar">
                <div className="tunisia-map-toolbar-group">
                    <Layers size={12} strokeWidth={2.2} />
                    {(["anomaly_count", "rate", "cell_count"] as Metric[]).map((m) => (
                        <button
                            key={m}
                            type="button"
                            className={`tunisia-map-toolbar-btn ${metric === m ? "is-active" : ""}`}
                            onClick={() => setMetric(m)}
                        >
                            {METRIC_LABEL[m]}
                        </button>
                    ))}
                </div>
                {frames && frames.length > 1 && (
                    <div className="tunisia-map-toolbar-group">
                        <button
                            type="button"
                            className="tunisia-map-toolbar-btn"
                            onClick={() => setPlaying((p) => !p)}
                            aria-label={playing ? "Pause" : "Play"}
                        >
                            {playing ? <Pause size={11} /> : <Play size={11} />}
                            <span style={{ marginLeft: 4 }}>{playing ? "Pause" : "Play"}</span>
                        </button>
                        <span className="tunisia-map-frame-label">
                            {activeFrameLabel} · {frameIdx + 1}/{frames.length}
                        </span>
                    </div>
                )}
            </div>

            <svg
                viewBox={`0 0 ${width} ${height}`}
                width="100%"
                height="100%"
                preserveAspectRatio="xMidYMid meet"
                style={{ display: "block" }}
            >
                <defs>
                    <filter id="map-glow" x="-20%" y="-20%" width="140%" height="140%">
                        <feGaussianBlur stdDeviation="2.5" result="blur" />
                        <feMerge>
                            <feMergeNode in="blur" />
                            <feMergeNode in="SourceGraphic" />
                        </feMerge>
                    </filter>
                    <radialGradient id="map-canvas-bg" cx="50%" cy="40%" r="65%">
                        <stop offset="0%" stopColor="#F8FAFC" />
                        <stop offset="100%" stopColor="#E2E8F0" />
                    </radialGradient>
                    <linearGradient id="hotspot-pulse" x1="0%" y1="0%" x2="0%" y2="100%">
                        <stop offset="0%" stopColor="#FCA5A5" />
                        <stop offset="100%" stopColor="#B91C1C" />
                    </linearGradient>
                    <pattern id="empty-hatch" patternUnits="userSpaceOnUse" width="6" height="6" patternTransform="rotate(45)">
                        <line x1="0" y1="0" x2="0" y2="6" stroke="#CBD5E1" strokeWidth="1" />
                    </pattern>
                </defs>

                <rect x={0} y={0} width={width} height={height} fill="url(#map-canvas-bg)" rx={12} />

                {/* Polygons — always visible. Empty governorates get a hatched pattern. */}
                {orderedFeatures.map((f, i) => {
                    const name = f.properties.shapeName;
                    const row = valueByGov.get(name);
                    const value = pickMetric(row, metric);
                    const intensity = value / maxValue;
                    const fill = row && value > 0 ? colorForIntensity(intensity) : "url(#empty-hatch)";
                    const isSelected = selected === name;
                    const isHovered = hovered?.name === name;
                    const stroke = isSelected ? "#0F172A" : intensity > 0.4 ? "#7F1D1D" : "#334155";
                    const strokeWidth = isSelected ? 2.4 : isHovered ? 1.8 : 1.1;
                    const d = pathGen(f) ?? "";
                    const centroid = pathGen.centroid(f);

                    return (
                        <g key={f.properties.shapeISO ?? i}>
                            <motion.path
                                d={d}
                                fill={fill}
                                stroke={stroke}
                                strokeWidth={strokeWidth}
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                transition={{ delay: i * 0.012, duration: 0.4 }}
                                onMouseEnter={() => setHovered({ name, x: centroid[0], y: centroid[1] })}
                                onMouseLeave={() => setHovered(null)}
                                onClick={() => onSelect?.(selected === name ? null : name)}
                                style={{
                                    cursor: "pointer",
                                    transition: "stroke-width 0.15s ease, filter 0.2s ease",
                                    filter: isHovered || isSelected ? "url(#map-glow) brightness(1.05)" : undefined,
                                }}
                            />
                        </g>
                    );
                })}

                {/* Pulsing hotspots — top ≥45% intensity */}
                {orderedFeatures
                    .filter((f) => {
                        const v = pickMetric(valueByGov.get(f.properties.shapeName), metric);
                        return v / maxValue > 0.45;
                    })
                    .map((f, i) => {
                        const centroid = pathGen.centroid(f);
                        const name = f.properties.shapeName;
                        return (
                            <g key={`hot-${name}`} pointerEvents="none">
                                <motion.circle
                                    cx={centroid[0]}
                                    cy={centroid[1]}
                                    r={7}
                                    fill="none"
                                    stroke="#B91C1C"
                                    strokeWidth={1.5}
                                    animate={{ r: [7, 20], opacity: [0.85, 0] }}
                                    transition={{ duration: 1.8, repeat: Infinity, ease: "easeOut", delay: i * 0.2 }}
                                />
                                <circle
                                    cx={centroid[0]}
                                    cy={centroid[1]}
                                    r={5}
                                    fill="url(#hotspot-pulse)"
                                    stroke="#FFFFFF"
                                    strokeWidth={1.5}
                                />
                            </g>
                        );
                    })}

                {/* Labels — top ≥20% intensity */}
                {orderedFeatures
                    .filter((f) => {
                        const v = pickMetric(valueByGov.get(f.properties.shapeName), metric);
                        return v / maxValue > 0.20;
                    })
                    .map((f) => {
                        const centroid = pathGen.centroid(f);
                        return (
                            <text
                                key={`lbl-${f.properties.shapeName}`}
                                x={centroid[0]}
                                y={centroid[1] + 16}
                                textAnchor="middle"
                                fontSize={10}
                                fontWeight={700}
                                fill="#0F172A"
                                pointerEvents="none"
                                style={{
                                    paintOrder: "stroke",
                                    stroke: "rgba(255,255,255,0.95)",
                                    strokeWidth: 3,
                                    fontFamily: "Geist, Inter, sans-serif",
                                }}
                            >
                                {f.properties.shapeName}
                            </text>
                        );
                    })}
            </svg>

            <AnimatePresence>
                {hovered && (() => {
                    const row = valueByGov.get(hovered.name);
                    return (
                        <motion.div
                            initial={{ opacity: 0, y: 4 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -2 }}
                            className="tunisia-map-tooltip"
                            style={{
                                left: `${(hovered.x / width) * 100}%`,
                                top: `${(hovered.y / height) * 100}%`,
                            }}
                        >
                            <div className="tunisia-map-tooltip-title">
                                <MapPin size={13} strokeWidth={2.4} /> {hovered.name}
                            </div>
                            {row ? (
                                <>
                                    <div className="tunisia-map-tooltip-row">
                                        <span>Anomalies</span>
                                        <strong>{row.anomaly_count.toLocaleString()}</strong>
                                    </div>
                                    <div className="tunisia-map-tooltip-row">
                                        <span>Rate</span>
                                        <strong>{row.rate}%</strong>
                                    </div>
                                    <div className="tunisia-map-tooltip-row">
                                        <span>Cells</span>
                                        <strong>{row.cell_count}</strong>
                                    </div>
                                    <div className="tunisia-map-tooltip-hint">Click to inspect causes</div>
                                </>
                            ) : (
                                <div className="tunisia-map-tooltip-empty">No anomalies recorded</div>
                            )}
                        </motion.div>
                    );
                })()}
            </AnimatePresence>

            <div className="tunisia-map-stats">
                <div className="tunisia-map-stat">
                    <div className="tunisia-map-stat-icon"><AlertTriangle size={13} strokeWidth={2.4} /></div>
                    <div>
                        <div className="tunisia-map-stat-value">{totalAnoms.toLocaleString()}</div>
                        <div className="tunisia-map-stat-label">total anomalies</div>
                    </div>
                </div>
                <div className="tunisia-map-stat-sep" />
                <div className="tunisia-map-stat">
                    <div className="tunisia-map-stat-icon"><Radio size={13} strokeWidth={2.4} /></div>
                    <div>
                        <div className="tunisia-map-stat-value">{activeRows.length}</div>
                        <div className="tunisia-map-stat-label">regions · {totalCells} cells</div>
                    </div>
                </div>
                <div className="tunisia-map-stat-sep" />
                <div className="tunisia-map-stat">
                    <div className="tunisia-map-stat-icon"><Activity size={13} strokeWidth={2.4} /></div>
                    <div>
                        <div className="tunisia-map-stat-value">{METRIC_LABEL[metric]}</div>
                        <div className="tunisia-map-stat-label">current layer</div>
                    </div>
                </div>
            </div>

            <div className="tunisia-map-legend">
                <span className="tunisia-map-legend-label">0</span>
                <div className="tunisia-map-legend-bar" />
                <span className="tunisia-map-legend-label">
                    {metric === "rate" ? `${maxValue.toFixed(1)}%` : maxValue.toLocaleString()}
                </span>
            </div>
        </div>
    );
}
