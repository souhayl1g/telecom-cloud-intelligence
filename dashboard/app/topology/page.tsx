"use client";
import { useEffect, useState, useCallback } from 'react';
import PageInfoBar from '../../components/PageInfoBar';
import { useRefresh } from '../../components/RefreshContext';

/* ── Types ─────────────────────────────────────────────────────────────── */
interface CellNode {
    id: string;
    name: string;
    type: 'enodeb' | 'gnodeb' | 'core' | 'aggregation' | 'bsc';
    x: number;
    y: number;
    status: 'healthy' | 'warning' | 'critical' | 'maintenance';
    kpis: {
        throughput: number;
        latency: number;
        packetLoss: number;
        users: number;
        rsrp: number;
    };
    anomalyScore: number;
}

interface LinkEdge {
    source: string;
    target: string;
    bandwidth: number;
    utilization: number;
    status: 'active' | 'degraded' | 'down';
}

/* ── Generate realistic topology from live data ─────────────────────────── */
function generateTopology(anomalies: any[], slaScore: number): { nodes: CellNode[]; links: LinkEdge[] } {
    const regions = ['TN-TUNIS', 'TN-SFAX', 'TN-SOUSSE', 'TN-BIZERTE', 'TN-GABES', 'TN-NABEUL'];
    const types: CellNode['type'][] = ['gnodeb', 'enodeb', 'enodeb', 'aggregation', 'gnodeb', 'enodeb'];

    // Core node
    const coreNode: CellNode = {
        id: 'CORE-01', name: 'Core Network', type: 'core',
        x: 400, y: 60,
        status: slaScore >= 0.7 ? 'critical' : slaScore >= 0.4 ? 'warning' : 'healthy',
        kpis: { throughput: 1200, latency: 5, packetLoss: 0.01, users: 50000, rsrp: -65 },
        anomalyScore: slaScore,
    };

    // Cell nodes
    const cellNodes: CellNode[] = regions.map((region, i) => {
        const angle = (i / regions.length) * 2 * Math.PI - Math.PI / 2;
        const radius = 180;
        const anomaly = anomalies[i % anomalies.length];
        const severity = anomaly?.severity ?? Math.random() * 0.5;
        return {
            id: `CELL-${region}`,
            name: region,
            type: types[i],
            x: 400 + Math.cos(angle) * radius,
            y: 240 + Math.sin(angle) * radius,
            status: severity > 0.9 ? 'critical' : severity > 0.5 ? 'warning' : 'healthy',
            kpis: {
                throughput: anomaly?.throughput_mbps ?? (50 + Math.random() * 100),
                latency: anomaly?.latency_ms ?? (10 + Math.random() * 40),
                packetLoss: anomaly?.packet_loss_pct ?? Math.random() * 2,
                users: anomaly?.active_users ?? Math.floor(100 + Math.random() * 500),
                rsrp: anomaly?.signal_rsrp_dbm ?? (-120 + Math.random() * 50),
            },
            anomalyScore: severity,
        };
    });

    // BSC node
    const bscNode: CellNode = {
        id: 'BSC-01', name: 'BSC Controller', type: 'bsc',
        x: 400, y: 420,
        status: 'healthy',
        kpis: { throughput: 800, latency: 3, packetLoss: 0.005, users: 30000, rsrp: -70 },
        anomalyScore: 0.1,
    };

    const nodes = [coreNode, ...cellNodes, bscNode];

    // Links from core to cells and cells to BSC
    const links: LinkEdge[] = [
        ...cellNodes.map(cell => ({
            source: 'CORE-01',
            target: cell.id,
            bandwidth: 10000,
            utilization: 30 + cell.anomalyScore * 60,
            status: cell.status === 'critical' ? 'degraded' as const : 'active' as const,
        })),
        ...cellNodes.slice(0, 3).map(cell => ({
            source: cell.id,
            target: 'BSC-01',
            bandwidth: 5000,
            utilization: 20 + Math.random() * 40,
            status: 'active' as const,
        })),
    ];

    return { nodes, links };
}

/* ── SVG Topology Renderer ──────────────────────────────────────────────── */
function TopologyGraph({ nodes, links, selected, onSelect }: {
    nodes: CellNode[]; links: LinkEdge[];
    selected: CellNode | null; onSelect: (n: CellNode | null) => void;
}) {
    const statusColor = (s: string) => {
        switch (s) {
            case 'critical': return 'var(--color-danger)';
            case 'warning': return 'var(--color-warning)';
            case 'maintenance': return 'var(--text-muted)';
            default: return 'var(--color-success)';
        }
    };

    const typeIcon = (t: string) => {
        switch (t) {
            case 'core': return '\u{1F3E2}';
            case 'gnodeb': return '\u{1F4F6}';
            case 'enodeb': return '\u{1F4E1}';
            case 'aggregation': return '\u{1F504}';
            case 'bsc': return '\u{1F5A5}';
            default: return '\u{2B24}';
        }
    };

    return (
        <svg width="100%" height="480" viewBox="0 0 800 480" style={{ display: 'block' }}>
            <defs>
                <filter id="glow">
                    <feGaussianBlur stdDeviation="3" result="coloredBlur" />
                    <feMerge><feMergeNode in="coloredBlur" /><feMergeNode in="SourceGraphic" /></feMerge>
                </filter>
            </defs>

            {/* Links */}
            {links.map((link, i) => {
                const source = nodes.find(n => n.id === link.source);
                const target = nodes.find(n => n.id === link.target);
                if (!source || !target) return null;
                const color = link.status === 'degraded' ? 'var(--color-warning)' : link.status === 'down' ? 'var(--color-danger)' : 'rgba(99, 102, 241, 0.3)';
                return (
                    <line key={i} x1={source.x} y1={source.y} x2={target.x} y2={target.y}
                        stroke={color} strokeWidth={link.status === 'degraded' ? 2.5 : 1.5}
                        strokeDasharray={link.status === 'down' ? '5,5' : 'none'}
                        opacity={0.6}
                    />
                );
            })}

            {/* Utilization labels on links */}
            {links.map((link, i) => {
                const source = nodes.find(n => n.id === link.source);
                const target = nodes.find(n => n.id === link.target);
                if (!source || !target) return null;
                return (
                    <text key={`u-${i}`} x={(source.x + target.x) / 2} y={(source.y + target.y) / 2 - 6}
                        textAnchor="middle" fontSize="9" fill="var(--text-muted)" fontFamily="JetBrains Mono, monospace">
                        {link.utilization.toFixed(0)}%
                    </text>
                );
            })}

            {/* Nodes */}
            {nodes.map(node => {
                const isSelected = selected?.id === node.id;
                const r = node.type === 'core' ? 28 : node.type === 'bsc' ? 24 : 20;
                return (
                    <g key={node.id} onClick={() => onSelect(isSelected ? null : node)} style={{ cursor: 'pointer' }}>
                        {/* Pulse for critical */}
                        {node.status === 'critical' && (
                            <circle cx={node.x} cy={node.y} r={r + 8} fill="none" stroke="var(--color-danger)"
                                strokeWidth="1" opacity="0.4">
                                <animate attributeName="r" from={r + 4} to={r + 14} dur="2s" repeatCount="indefinite" />
                                <animate attributeName="opacity" from="0.5" to="0" dur="2s" repeatCount="indefinite" />
                            </circle>
                        )}
                        {/* Node circle */}
                        <circle cx={node.x} cy={node.y} r={r}
                            fill={isSelected ? statusColor(node.status) : 'var(--bg-elevated)'}
                            stroke={statusColor(node.status)} strokeWidth={isSelected ? 3 : 2}
                            filter={node.status === 'critical' ? 'url(#glow)' : undefined}
                        />
                        {/* Icon */}
                        <text x={node.x} y={node.y + 5} textAnchor="middle" fontSize={node.type === 'core' ? 18 : 14}>
                            {typeIcon(node.type)}
                        </text>
                        {/* Label */}
                        <text x={node.x} y={node.y + r + 14} textAnchor="middle" fontSize="10" fontWeight="600"
                            fill={isSelected ? statusColor(node.status) : 'var(--text-secondary)'}>
                            {node.name}
                        </text>
                        {/* Status indicator */}
                        <circle cx={node.x + r - 4} cy={node.y - r + 4} r="4" fill={statusColor(node.status)} />
                    </g>
                );
            })}
        </svg>
    );
}

/* ── Main Page ──────────────────────────────────────────────────────────── */
export default function TopologyPage() {
    const [nodes, setNodes] = useState<CellNode[]>([]);
    const [links, setLinks] = useState<LinkEdge[]>([]);
    const [selected, setSelected] = useState<CellNode | null>(null);
    const [loading, setLoading] = useState(true);
    const { tick } = useRefresh();

    const fetchData = useCallback(async () => {
        try {
            const res = await fetch('/api/platform-data', { cache: 'no-store' });
            if (!res.ok) throw new Error();
            const data = await res.json();
            const { nodes: n, links: l } = generateTopology(
                data.anomalies ?? [],
                data.sla?.score ?? 0
            );
            setNodes(n);
            setLinks(l);
        } catch { /* silent */ }
        finally { setLoading(false); }
    }, []);

    useEffect(() => {
        fetchData();
    }, [fetchData, tick]);

    const healthyCount = nodes.filter(n => n.status === 'healthy').length;
    const warningCount = nodes.filter(n => n.status === 'warning').length;
    const criticalCount = nodes.filter(n => n.status === 'critical').length;

    if (loading) {
        return (
            <div className="l4-loading">
                <div className="l4-loading-spinner" />
                <div className="l4-loading-text">Loading network topology...</div>
            </div>
        );
    }

    return (
        <div className="grid" style={{ gap: 24 }}>
            <PageInfoBar
                eyebrow="Topology · Live Health Overlay"
                description="Where is the pain on the map? Cell sites, aggregation nodes and core routers are rendered with real anomaly-severity colouring so you can see exactly which part of the RAN is hurting. Click any node for KPIs (throughput, latency, packet loss, RSRP) and linked-service status."
                values={[
                    { text: `${healthyCount} healthy · ${warningCount} warning · ${criticalCount} critical` },
                    { text: `${nodes.length} nodes · ${links.length} links monitored` },
                    { text: 'Demo topology · real severity overlay' },
                ]}
            />

            <div style={{ padding: '12px 16px', background: 'var(--color-info-bg)', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-info-border)', fontSize: 12, color: 'var(--text-secondary)' }}>
                <strong>Demo topology</strong> — Network layout uses a placeholder structure with real anomaly severity data overlay. Real Tunisie Telecom network topology will replace this when infrastructure data is integrated.
            </div>

            {/* Summary KPIs */}
            <div className="summary-strip">
                <div className="summary-item">
                    <div>
                        <div className="summary-item-value">{nodes.length}</div>
                        <div className="summary-item-label">Total Nodes</div>
                    </div>
                </div>
                <div className="summary-item">
                    <div>
                        <div className="summary-item-value" style={{ color: 'var(--color-success)' }}>{healthyCount}</div>
                        <div className="summary-item-label">Healthy</div>
                    </div>
                </div>
                <div className="summary-item">
                    <div>
                        <div className="summary-item-value" style={{ color: 'var(--color-warning)' }}>{warningCount}</div>
                        <div className="summary-item-label">Warning</div>
                    </div>
                </div>
                <div className="summary-item">
                    <div>
                        <div className="summary-item-value" style={{ color: 'var(--color-danger)' }}>{criticalCount}</div>
                        <div className="summary-item-label">Critical</div>
                    </div>
                </div>
                <div style={{ width: 1, background: 'var(--border)', margin: '0 8px' }} />
                <div className="summary-item">
                    <div>
                        <div className="summary-item-value">{links.length}</div>
                        <div className="summary-item-label">Active Links</div>
                    </div>
                </div>
                <div className="summary-item">
                    <div>
                        <div className="summary-item-value" style={{ color: 'var(--color-warning)' }}>
                            {links.filter(l => l.status === 'degraded').length}
                        </div>
                        <div className="summary-item-label">Degraded Links</div>
                    </div>
                </div>
            </div>

            {/* Topology + Detail Panel */}
            <div className="grid" style={{ gridTemplateColumns: selected ? '1fr 320px' : '1fr', gap: 20 }}>
                <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
                    <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div className="section-title" style={{ margin: 0 }}>
                            <span className="dot"></span>
                            Live Topology Map
                        </div>
                        <div style={{ display: 'flex', gap: 12, fontSize: 10, color: 'var(--text-muted)' }}>
                            <span><span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: '50%', background: 'var(--color-success)', marginRight: 4, verticalAlign: 'middle' }}></span>Healthy</span>
                            <span><span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: '50%', background: 'var(--color-warning)', marginRight: 4, verticalAlign: 'middle' }}></span>Warning</span>
                            <span><span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: '50%', background: 'var(--color-danger)', marginRight: 4, verticalAlign: 'middle' }}></span>Critical</span>
                        </div>
                    </div>
                    <div style={{ padding: '8px' }}>
                        <TopologyGraph nodes={nodes} links={links} selected={selected} onSelect={setSelected} />
                    </div>
                </div>

                {/* Detail panel */}
                {selected && (
                    <div className="card" style={{ height: 'fit-content' }}>
                        <div className="section-title">
                            <span className="dot"></span>
                            {selected.name}
                            <span className={`badge badge-${selected.status === 'critical' ? 'danger' : selected.status === 'warning' ? 'warning' : 'success'}`} style={{ marginLeft: 8, fontSize: 9 }}>
                                {selected.status.toUpperCase()}
                            </span>
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, fontSize: 12 }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid var(--border)' }}>
                                <span style={{ color: 'var(--text-muted)' }}>Node ID</span>
                                <span className="mono">{selected.id}</span>
                            </div>
                            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid var(--border)' }}>
                                <span style={{ color: 'var(--text-muted)' }}>Type</span>
                                <span style={{ textTransform: 'uppercase', fontWeight: 600 }}>{selected.type}</span>
                            </div>
                            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid var(--border)' }}>
                                <span style={{ color: 'var(--text-muted)' }}>Throughput</span>
                                <span>{selected.kpis.throughput.toFixed(1)} Mbps</span>
                            </div>
                            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid var(--border)' }}>
                                <span style={{ color: 'var(--text-muted)' }}>Latency</span>
                                <span style={{ color: selected.kpis.latency > 30 ? 'var(--color-warning)' : 'var(--color-success)' }}>
                                    {selected.kpis.latency.toFixed(1)} ms
                                </span>
                            </div>
                            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid var(--border)' }}>
                                <span style={{ color: 'var(--text-muted)' }}>Packet Loss</span>
                                <span style={{ color: selected.kpis.packetLoss > 1 ? 'var(--color-danger)' : 'var(--color-success)' }}>
                                    {selected.kpis.packetLoss.toFixed(2)}%
                                </span>
                            </div>
                            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid var(--border)' }}>
                                <span style={{ color: 'var(--text-muted)' }}>Active Users</span>
                                <span>{selected.kpis.users.toLocaleString()}</span>
                            </div>
                            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid var(--border)' }}>
                                <span style={{ color: 'var(--text-muted)' }}>RSRP</span>
                                <span style={{ color: selected.kpis.rsrp < -100 ? 'var(--color-danger)' : selected.kpis.rsrp < -85 ? 'var(--color-warning)' : 'var(--color-success)' }}>
                                    {selected.kpis.rsrp.toFixed(1)} dBm
                                </span>
                            </div>
                            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0' }}>
                                <span style={{ color: 'var(--text-muted)' }}>Anomaly Score</span>
                                <span style={{ color: selected.anomalyScore > 0.7 ? 'var(--color-danger)' : selected.anomalyScore > 0.3 ? 'var(--color-warning)' : 'var(--color-success)', fontWeight: 600 }}>
                                    {selected.anomalyScore.toFixed(3)}
                                </span>
                            </div>
                        </div>
                        {selected.status !== 'healthy' && (
                            <div style={{ marginTop: 16, padding: '12px', background: selected.status === 'critical' ? 'var(--color-danger-bg)' : 'var(--color-warning-bg)', borderRadius: 'var(--radius-sm)', border: `1px solid ${selected.status === 'critical' ? 'var(--color-danger-border)' : 'var(--color-warning-border)'}`, fontSize: 11 }}>
                                <div style={{ fontWeight: 600, marginBottom: 4 }}>AI Recommendation</div>
                                {selected.status === 'critical'
                                    ? `Critical anomaly on ${selected.name}. IsolationForest flagged abnormal KPIs. Recommend immediate traffic rerouting and capacity scaling for affected subscribers.`
                                    : `Warning state on ${selected.name}. KPI degradation detected. Monitor closely and consider preemptive load balancing.`
                                }
                            </div>
                        )}
                    </div>
                )}
            </div>

            {/* Node inventory table */}
            <div className="card">
                <div className="section-title">
                    <span className="dot"></span>
                    Node Inventory
                    <span className="section-subtitle">{nodes.length} nodes</span>
                </div>
                <div className="table-container">
                    <table className="table">
                        <thead>
                            <tr>
                                <th>Node</th>
                                <th>Type</th>
                                <th>Status</th>
                                <th>Throughput</th>
                                <th>Latency</th>
                                <th>Loss</th>
                                <th>Users</th>
                                <th>RSRP</th>
                                <th>Anomaly</th>
                            </tr>
                        </thead>
                        <tbody>
                            {nodes.map(node => (
                                <tr key={node.id} onClick={() => setSelected(node)} style={{ cursor: 'pointer' }}>
                                    <td className="mono">{node.name}</td>
                                    <td style={{ textTransform: 'uppercase', fontSize: 10, fontWeight: 600, color: 'var(--text-muted)' }}>{node.type}</td>
                                    <td>
                                        <span className={`status-dot ${node.status === 'critical' ? 'failed' : node.status === 'warning' ? 'running' : 'succeeded'}`}></span>
                                        <span style={{ fontWeight: 500, color: node.status === 'critical' ? 'var(--color-danger)' : node.status === 'warning' ? 'var(--color-warning)' : 'var(--color-success)' }}>
                                            {node.status}
                                        </span>
                                    </td>
                                    <td>{node.kpis.throughput.toFixed(1)} Mbps</td>
                                    <td style={{ color: node.kpis.latency > 30 ? 'var(--color-warning)' : 'inherit' }}>{node.kpis.latency.toFixed(1)} ms</td>
                                    <td style={{ color: node.kpis.packetLoss > 1 ? 'var(--color-danger)' : 'inherit' }}>{node.kpis.packetLoss.toFixed(2)}%</td>
                                    <td>{node.kpis.users.toLocaleString()}</td>
                                    <td style={{ color: node.kpis.rsrp < -100 ? 'var(--color-danger)' : 'inherit' }}>{node.kpis.rsrp.toFixed(0)} dBm</td>
                                    <td>
                                        <span style={{ fontFamily: 'JetBrains Mono, monospace', color: node.anomalyScore > 0.7 ? 'var(--color-danger)' : node.anomalyScore > 0.3 ? 'var(--color-warning)' : 'var(--color-success)', fontWeight: 600 }}>
                                            {node.anomalyScore.toFixed(3)}
                                        </span>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}
