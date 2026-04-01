"use client";
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';

export default function SlaChart({ data }: { data: any[] }) {
    if (!data || data.length === 0) {
        return <div className="empty-state"><div className="empty-state-text">No SLA risk data available</div></div>;
    }

    const chartData = [...data].reverse().map(d => {
        let timeLabel = d.created_at;
        try {
            timeLabel = new Date(d.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        } catch (e) { }
        return {
            time: timeLabel,
            score: typeof d.score === 'number' ? Number(d.score.toFixed(3)) : 0,
        };
    });

    return (
        <div style={{ width: '100%', height: 280 }}>
            <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                    <defs>
                        <linearGradient id="slaGradient" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#a78bfa" stopOpacity={0.4} />
                            <stop offset="50%" stopColor="#6366f1" stopOpacity={0.15} />
                            <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                        </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(255,255,255,0.04)" />
                    <XAxis dataKey="time" stroke="#5a6a7a" fontSize={11} tickLine={false} axisLine={false} />
                    <YAxis stroke="#5a6a7a" fontSize={11} tickLine={false} axisLine={false} domain={[0, 1]} ticks={[0, 0.2, 0.4, 0.6, 0.8, 1.0]} />
                    <ReferenceLine y={0.7} stroke="var(--color-danger)" strokeDasharray="4 4" strokeOpacity={0.5} />
                    <ReferenceLine y={0.4} stroke="var(--color-warning)" strokeDasharray="4 4" strokeOpacity={0.3} />
                    <Tooltip
                        contentStyle={{
                            backgroundColor: 'rgba(8, 10, 18, 0.95)',
                            borderColor: 'rgba(255,255,255,0.1)',
                            borderRadius: '10px',
                            backdropFilter: 'blur(10px)',
                            color: '#f0f2f5',
                            fontSize: 13,
                            boxShadow: '0 8px 24px rgba(0,0,0,0.4)',
                        }}
                        itemStyle={{ color: '#a78bfa', fontWeight: 600 }}
                        labelStyle={{ color: '#8899aa', fontSize: 11 }}
                    />
                    <Area
                        type="monotone"
                        dataKey="score"
                        stroke="#a78bfa"
                        strokeWidth={2.5}
                        fillOpacity={1}
                        fill="url(#slaGradient)"
                        dot={{ r: 3, fill: '#a78bfa', stroke: '#060911', strokeWidth: 2 }}
                        activeDot={{ r: 5, fill: '#a78bfa', stroke: '#fff', strokeWidth: 2 }}
                    />
                </AreaChart>
            </ResponsiveContainer>
        </div>
    );
}
