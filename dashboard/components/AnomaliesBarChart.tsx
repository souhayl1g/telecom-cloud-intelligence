"use client";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell, Legend } from 'recharts';

export default function AnomaliesBarChart({ ossData, bssData }: { ossData: any[]; bssData: any[] }) {
    const data = [
        { name: 'OSS Critical', count: ossData?.filter(a => a.severity > 0.9).length || 0, color: '#f87171' },
        { name: 'OSS Warning', count: ossData?.filter(a => a.severity > 0.5 && a.severity <= 0.9).length || 0, color: '#fbbf24' },
        { name: 'OSS Low', count: ossData?.filter(a => a.severity <= 0.5).length || 0, color: '#34d399' },
        { name: 'BSS High', count: bssData?.filter(b => (b.severity ?? b.score) > 0.8).length || 0, color: '#a78bfa' },
        { name: 'BSS Medium', count: bssData?.filter(b => { const s = b.severity ?? b.score; return s > 0.4 && s <= 0.8; }).length || 0, color: '#6366f1' },
        { name: 'BSS Low', count: bssData?.filter(b => (b.severity ?? b.score) <= 0.4).length || 0, color: '#60a5fa' },
    ];

    const total = data.reduce((s, d) => s + d.count, 0);
    if (total === 0) {
        return <div className="empty-state"><div className="empty-state-text">No anomaly data</div></div>;
    }

    return (
        <div style={{ width: '100%', height: 280 }}>
            <ResponsiveContainer width="100%" height="100%">
                <BarChart data={data} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(255,255,255,0.04)" />
                    <XAxis dataKey="name" stroke="#5a6a7a" fontSize={10} tickLine={false} axisLine={false} angle={-20} textAnchor="end" height={50} />
                    <YAxis stroke="#5a6a7a" fontSize={11} tickLine={false} axisLine={false} allowDecimals={false} />
                    <Tooltip
                        contentStyle={{
                            backgroundColor: 'rgba(8, 10, 18, 0.95)',
                            borderColor: 'rgba(255,255,255,0.1)',
                            borderRadius: '10px',
                            color: '#f0f2f5',
                            fontSize: 13,
                        }}
                        cursor={{ fill: 'rgba(255,255,255,0.03)' }}
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
