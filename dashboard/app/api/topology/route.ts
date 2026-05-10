import { NextResponse } from 'next/server';
import { query } from '../../../lib/db';

export const dynamic = 'force-dynamic';

function getAreaStatus(
    anomalyCount: number,
    avgPacketLoss: number,
    avgLatency: number
): string {
    if (anomalyCount > 10 || avgPacketLoss > 2 || avgLatency > 40) return 'critical';
    if (anomalyCount > 3 || avgPacketLoss > 1 || avgLatency > 25) return 'warning';
    return 'healthy';
}

function getAreaType(ratTypes: string): string {
    if (ratTypes.includes('4G') || ratTypes.includes('5G')) return 'enodeb';
    if (ratTypes.includes('2G') || ratTypes.includes('3G')) return 'bsc';
    return 'aggregation';
}

export async function GET() {
    try {
        const latestMonth = await query<{ month_year: string }>(
            `SELECT MAX(month_year) as month_year FROM area_network_health`
        );

        const monthYear = latestMonth[0]?.month_year;
        if (!monthYear) {
            return NextResponse.json({ core: null, areas: [], links: [] });
        }

        const areaRows = await query<{
            area: string;
            avg_throughput: number;
            avg_latency: number;
            avg_packet_loss: number;
            anomaly_count: number;
            subscriber_count: number;
            avg_cem_score: number;
            underserved_pct: number;
            usim_bottleneck_pct: number;
            cell_count: number;
            cell_anomaly_count: number;
            rat_type_count: number;
            rat_types: string;
        }>(
            `
            WITH cell_stats AS (
                SELECT
                    area,
                    COUNT(*)::int as cell_count,
                    COUNT(*) FILTER (WHERE anomaly_flag = true)::int as cell_anomaly_count,
                    COUNT(DISTINCT rat_type)::int as rat_type_count,
                    STRING_AGG(DISTINCT rat_type, ',' ORDER BY rat_type) as rat_types
                FROM oss_cell_kpis
                WHERE month_year = $1
                GROUP BY area
            )
            SELECT
                a.area,
                a.avg_throughput,
                a.avg_latency,
                a.avg_packet_loss,
                a.anomaly_count,
                a.subscriber_count,
                a.avg_cem_score,
                a.underserved_pct,
                a.usim_bottleneck_pct,
                COALESCE(c.cell_count, 0) as cell_count,
                COALESCE(c.cell_anomaly_count, 0) as cell_anomaly_count,
                COALESCE(c.rat_type_count, 0) as rat_type_count,
                COALESCE(c.rat_types, '') as rat_types
            FROM area_network_health a
            LEFT JOIN cell_stats c ON a.area = c.area
            WHERE a.month_year = $1
              AND a.area IS NOT NULL
              AND UPPER(TRIM(a.area)) NOT IN ('NULL', 'NONE', 'N/A', '')
            ORDER BY a.area
            `,
            [monthYear]
        );

        const areas = areaRows.map((row) => {
            const id = row.area.toLowerCase().replace(/\s+/g, '-');
            const ratTypes = row.rat_types || '';
            const status = getAreaStatus(
                row.anomaly_count,
                row.avg_packet_loss,
                row.avg_latency
            );
            const type = getAreaType(ratTypes);

            return {
                id,
                name: row.area,
                type,
                status,
                cellCount: row.cell_count,
                anomalyCount: row.anomaly_count,
                subscriberCount: row.subscriber_count || 0,
                avgThroughput: Number(row.avg_throughput) || 0,
                avgLatency: Number(row.avg_latency) || 0,
                avgPacketLoss: Number(row.avg_packet_loss) || 0,
                avgCemScore: Number(row.avg_cem_score) || 0,
                underservedPct: Number(row.underserved_pct) || 0,
                usimBottleneckPct: Number(row.usim_bottleneck_pct) || 0,
            };
        });

        const links = areas.map((area) => {
            const utilization = Math.round(
                Math.min(
                    95,
                    Math.max(
                        5,
                        area.avgLatency * 0.8 +
                            area.avgPacketLoss * 5 +
                            area.anomalyCount * 1.5
                    )
                )
            );

            return {
                source: 'CORE-TT',
                target: area.id,
                bandwidth: 10000,
                utilization,
                status:
                    area.status === 'healthy'
                        ? ('active' as const)
                        : ('degraded' as const),
            };
        });

        return NextResponse.json({
            core: {
                id: 'CORE-TT',
                name: 'Tunisie Telecom Core',
                type: 'core',
                status: 'healthy',
            },
            areas,
            links,
        });
    } catch (err: any) {
        console.error('Topology API error:', err);
        return NextResponse.json({ error: err.message }, { status: 500 });
    }
}
