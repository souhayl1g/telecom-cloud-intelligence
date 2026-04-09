"use client";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell, Legend } from 'recharts';
import { useTheme } from './ThemeProvider';

export default function AnomaliesBarChart({ ossData, bssData }: { ossData: any[]; bssData: any[] }) {
    const { theme } = useTheme();
    const isLight = theme === 'light';

    const data = [
        { name: 'OSS Critical', count: ossData?.filter(a => a.severity > 0.9).length || 0, color: isLight ? '#dc2626' : '#f87171' },
        { name: 'OSS Warning', count: ossData?.filter(a => a.severity > 0.5 && a.severity <= 0.9).length || 0, color: isLight ? '#ca8a04' : '#fbbf24' },
        { name: 'OSS Low', count: ossData?.filter(a => a.severity <= 0.5).length || 0, color: isLight ? '#16a34a' : '#34d399' },
        { name: 'BSS High', count: bssData?.filter(b => (b.severity ?? b.score) > 0.8).length || 0, color: isLight ? '#7c3aed' : '#a78bfa' },
        { name: 'BSS Medium', count: bssData?.filter(b => { const s = b.severity ?? b.score; return s > 0.4 && s <= 0.8; }).length || 0, color: isLight ? '#5b5eed' : '#6366f1' },
        { name: 'BSS Low', count: bssData?.filter(b => (b.severity ?? b.score) <= 0.4).length || 0, color: isLight ? '#2563eb' : '#60a5fa' },
    ];

    const total = data.reduce((s, d) => s + d.count, 0);
    if (total === 0) {
        return <div className="empty-state"><div className="empty-state-text">No anomaly data</div></div>;
    }

    const axisColor = isLight ? '#94a3b8' : '#5a6a7a';
    const gridColor = isLight ? 'rgba(0,0,0,0.06)' : 'rgba(255,255,255,0.04)';

    return (
        <div style={{ width: '100%', height: 280 }}>
            <ResponsiveContainer width="100%" height="100%">
                <BarChart data={data} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={gridColor} />
                    <XAxis dataKey="name" stroke={axisColor} fontSize={10} tickLine={false} axisLine={false} angle={-20} textAnchor="end" height={50} />
                    <YAxis stroke={axisColor} fontSize={11} tickLine={false} axisLine={false} allowDecimals={false} />
                    <Tooltip
                        contentStyle={{
                            backgroundColor: isLight ? 'rgba(255,255,255,0.95)' : 'rgba(8,10,18,0.95)',
                            borderColor: isLight ? 'rgba(0,0,0,0.08)' : 'rgba(255,255,255,0.1)',
                            borderRadius: '10px',
                            color: isLight ? '#0f172a' : '#f0f2f5',
                            fontSize: 13,
                            boxShadow: isLight ? '0 4px 16px rgba(0,0,0,0.08)' : undefined,
                        }}
                        cursor={{ fill: isLight ? 'rgba(0,0,0,0.03)' : 'rgba(255,255,255,0.03)' }}
                    />
                    <Bar dataKey="count" radius={[6, 6, 0, 0]} maxBarSize={40}>
                        {data.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={entry.color} fillOpacity={0.85} />
                        ))}
                    </Bar>
                </BarChart>
            </ResponsiveContainer>
        </div>
    );
}
