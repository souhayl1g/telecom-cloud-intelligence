"use client";
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';
import { useTheme } from './ThemeProvider';
import { formatTunisShortTime } from '../lib/time';

export default function SlaChart({ data }: { data: any[] }) {
    const { theme } = useTheme();
    const isLight = theme === 'light';

    if (!data || data.length === 0) {
        return <div className="empty-state"><div className="empty-state-text">No SLA risk data available</div></div>;
    }

    const chartData = [...data].reverse().map(d => {
        let timeLabel = d.created_at;
        try {
            timeLabel = formatTunisShortTime(d.created_at);
        } catch (e) { }
        return {
            time: timeLabel,
            score: typeof d.score === 'number' ? Number(d.score.toFixed(3)) : 0,
        };
    });

    const axisColor = isLight ? '#94a3b8' : '#5a6a7a';
    const gridColor = isLight ? 'rgba(0,0,0,0.06)' : 'rgba(255,255,255,0.04)';
    const brandColor = isLight ? '#7c5cfc' : '#a78bfa';
    const bgDot = isLight ? '#f5f7fb' : '#060911';

    return (
        <div style={{ width: '100%', height: 280 }}>
            <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                    <defs>
                        <linearGradient id="slaGradient" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor={brandColor} stopOpacity={isLight ? 0.25 : 0.4} />
                            <stop offset="50%" stopColor={brandColor} stopOpacity={0.1} />
                            <stop offset="95%" stopColor={brandColor} stopOpacity={0} />
                        </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={gridColor} />
                    <XAxis dataKey="time" stroke={axisColor} fontSize={11} tickLine={false} axisLine={false} />
                    <YAxis stroke={axisColor} fontSize={11} tickLine={false} axisLine={false} domain={[0, 1]} ticks={[0, 0.2, 0.4, 0.6, 0.8, 1.0]} />
                    <ReferenceLine y={0.7} stroke="var(--color-danger)" strokeDasharray="4 4" strokeOpacity={0.5} />
                    <ReferenceLine y={0.4} stroke="var(--color-warning)" strokeDasharray="4 4" strokeOpacity={0.3} />
                    <Tooltip
                        contentStyle={{
                            backgroundColor: isLight ? 'rgba(255,255,255,0.95)' : 'rgba(8,10,18,0.95)',
                            borderColor: isLight ? 'rgba(0,0,0,0.08)' : 'rgba(255,255,255,0.1)',
                            borderRadius: '10px',
                            backdropFilter: 'blur(10px)',
                            color: isLight ? '#0f172a' : '#f0f2f5',
                            fontSize: 13,
                            boxShadow: isLight ? '0 8px 24px rgba(0,0,0,0.1)' : '0 8px 24px rgba(0,0,0,0.4)',
                        }}
                        itemStyle={{ color: brandColor, fontWeight: 600 }}
                        labelStyle={{ color: axisColor, fontSize: 11 }}
                    />
                    <Area
                        type="monotone"
                        dataKey="score"
                        stroke={brandColor}
                        strokeWidth={2.5}
                        fillOpacity={1}
                        fill="url(#slaGradient)"
                        dot={{ r: 3, fill: brandColor, stroke: bgDot, strokeWidth: 2 }}
                        activeDot={{ r: 5, fill: brandColor, stroke: isLight ? '#fff' : '#fff', strokeWidth: 2 }}
                    />
                </AreaChart>
            </ResponsiveContainer>
        </div>
    );
}
