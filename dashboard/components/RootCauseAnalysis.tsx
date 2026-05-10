"use client";

/* ── AI Root Cause Analysis Panel ─────────────────────────────────────────
   Generates natural-language explanations by combining:
   - SLA risk score + feature importances
   - OSS anomalies (cell-level, with severity + baseline deviation)
   - BSS anomalies (subscriber-level, with revenue impact)
   - OSS↔CEM correlations (Pearson/Spearman, with significance)
   ──────────────────────────────────────────────────────────────────────── */

interface RCAProps {
    sla: { score: number; region?: string; model_version?: string; explanation?: { feature_importances?: Record<string, number> } } | null;
    ossAnomalies: any[];
    bssAnomalies: any[];
    correlations: any[];
}

/* ── Analysis engine (runs server-side via props, renders client-side) ─── */
function buildRCA(sla: RCAProps["sla"], oss: any[], bss: any[], corrs: any[]) {
    const score = sla?.score ?? 0;
    const riskLevel = score >= 0.7 ? "CRITICAL" : score >= 0.4 ? "WARNING" : "HEALTHY";

    // Top affected cells
    const criticalOss = oss
        .filter((a) => a.severity > 0.9)
        .sort((a, b) => (b.severity ?? 0) - (a.severity ?? 0));
    const warningOss = oss.filter((a) => a.severity > 0.5 && a.severity <= 0.9);

    // Top affected BSS
    const criticalBss = bss
        .filter((a) => (a.severity ?? a.score ?? 0) > 0.8)
        .sort((a, b) => (b.severity ?? b.score ?? 0) - (a.severity ?? a.score ?? 0));

    // Strong correlations
    const strongCorrs = corrs
        .filter((c) => Math.abs(c.corr_value) >= 0.6 && (c.p_value ?? 1) < 0.05)
        .sort((a, b) => Math.abs(b.corr_value) - Math.abs(a.corr_value));

    // Feature importances
    const importances = sla?.explanation?.feature_importances ?? {};
    const topDrivers = Object.entries(importances)
        .sort(([, a], [, b]) => b - a)
        .slice(0, 3);

    // Unique impacted regions
    const regions = [...new Set([
        ...criticalOss.map((a) => a.region).filter(Boolean),
        ...criticalBss.map((a) => a.region).filter(Boolean),
    ])];

    // Unique impacted KPIs
    const kpis = [...new Set(criticalOss.map((a) => a.kpi_name).filter(Boolean))];

    // Unique impacted operators
    const operators = [...new Set(criticalBss.map((a) => a.operator).filter(Boolean))];

    // Build the narrative
    const findings: { icon: string; severity: "critical" | "warning" | "info" | "success"; title: string; detail: string }[] = [];

    // 1. SLA Risk Assessment
    if (score >= 0.7) {
        findings.push({
            icon: "\u26A0",
            severity: "critical",
            title: `SLA breach risk critically elevated at ${(score * 100).toFixed(1)}%`,
            detail: topDrivers.length > 0
                ? `Primary driver: ${formatKPI(topDrivers[0][0])} (${(topDrivers[0][1] * 100).toFixed(0)}% importance)${topDrivers.length > 1 ? `, followed by ${formatKPI(topDrivers[1][0])} (${(topDrivers[1][1] * 100).toFixed(0)}%)` : ""}.`
                : `Model confidence high. Immediate attention required.`,
        });
    } else if (score >= 0.4) {
        findings.push({
            icon: "\u26A0",
            severity: "warning",
            title: `SLA breach risk elevated at ${(score * 100).toFixed(1)}%`,
            detail: topDrivers.length > 0
                ? `Watch metric: ${formatKPI(topDrivers[0][0])} contributing ${(topDrivers[0][1] * 100).toFixed(0)}% to risk score.`
                : `Monitoring recommended.`,
        });
    } else {
        findings.push({
            icon: "\u2713",
            severity: "success",
            title: `SLA risk within safe threshold at ${(score * 100).toFixed(1)}%`,
            detail: `All primary KPI drivers within normal operating range.`,
        });
    }

    // 2. Network anomaly impact
    if (criticalOss.length > 0) {
        const cells = [...new Set(criticalOss.map((a) => a.cell_id))].slice(0, 5);
        const worstDev = criticalOss[0];
        const deviation = worstDev.value != null && worstDev.baseline_value != null && worstDev.baseline_value !== 0
            ? ((worstDev.value - worstDev.baseline_value) / Math.abs(worstDev.baseline_value) * 100).toFixed(0)
            : null;

        findings.push({
            icon: "\uD83D\uDCE1",
            severity: "critical",
            title: `${criticalOss.length} critical network anomalies across ${cells.length} cell${cells.length > 1 ? "s" : ""}`,
            detail: `Cells affected: ${cells.join(", ")}${kpis.length > 0 ? `. KPIs impacted: ${kpis.join(", ")}` : ""}${deviation ? `. Worst deviation: ${deviation}% from baseline on ${worstDev.cell_id}` : ""}.${regions.length > 0 ? ` Region${regions.length > 1 ? "s" : ""}: ${regions.join(", ")}.` : ""}`,
        });
    }
    if (warningOss.length > 0) {
        findings.push({
            icon: "\uD83D\uDCE1",
            severity: "warning",
            title: `${warningOss.length} warning-level network anomalies detected`,
            detail: `${[...new Set(warningOss.map((a) => a.cell_id))].length} cells showing degraded KPIs. Monitor for escalation.`,
        });
    }

    // 3. Revenue / BSS impact
    if (criticalBss.length > 0) {
        findings.push({
            icon: "\uD83D\uDCB3",
            severity: "critical",
            title: `${criticalBss.length} high-impact revenue anomalies detected`,
            detail: `${operators.length > 0 ? `Operators affected: ${operators.join(", ")}. ` : ""}${criticalBss.filter((b) => b.line_type === "postpaid").length} postpaid + ${criticalBss.filter((b) => b.line_type === "prepaid").length} prepaid subscribers impacted.`,
        });
    }

    // 4. Correlation-driven root cause
    if (strongCorrs.length > 0) {
        const top = strongCorrs[0];
        const direction = top.corr_value > 0 ? "positive" : "inverse";
        const strength = Math.abs(top.corr_value) >= 0.7 ? "strong" : "moderate";
        findings.push({
            icon: "\uD83D\uDD17",
            severity: "info",
            title: `${strength} ${direction} correlation: ${formatKPI(top.metric_x)} \u2194 ${formatKPI(top.metric_y)}`,
            detail: `Coefficient: ${top.corr_value.toFixed(3)} (${top.method}, p=${top.p_value?.toExponential(1) ?? "N/A"}). ${top.corr_value > 0 ? `As ${formatKPI(top.metric_x)} increases, ${formatKPI(top.metric_y)} rises proportionally.` : `As ${formatKPI(top.metric_x)} increases, ${formatKPI(top.metric_y)} decreases.`}${strongCorrs.length > 1 ? ` +${strongCorrs.length - 1} more significant correlations found.` : ""}`,
        });
    }

    // 5. Cross-domain narrative (the "story")
    let narrative = "";
    if (criticalOss.length > 0 && criticalBss.length > 0 && strongCorrs.length > 0) {
        const topCorr = strongCorrs[0];
        narrative = `Root cause chain detected: Network degradation in ${[...new Set(criticalOss.slice(0, 3).map((a) => a.cell_id))].join(", ")} is causing ${formatKPI(topCorr.metric_x)} anomalies, which correlate (r=${topCorr.corr_value.toFixed(2)}) with ${formatKPI(topCorr.metric_y)} impact on the BSS side. This cross-domain effect is driving the SLA risk to ${(score * 100).toFixed(1)}%.${operators.length > 0 ? ` Affected operators: ${operators.join(", ")}.` : ""} Recommend immediate investigation of network cells and subscriber impact assessment.`;
    } else if (criticalOss.length > 0 && score >= 0.7) {
        narrative = `Network anomalies detected on ${[...new Set(criticalOss.slice(0, 3).map((a) => a.cell_id))].join(", ")} are the primary contributors to the elevated SLA breach risk (${(score * 100).toFixed(1)}%). ${topDrivers.length > 0 ? `The ML model identifies ${formatKPI(topDrivers[0][0])} as the dominant risk factor.` : ""} Recommend cell-level investigation and proactive capacity adjustment.`;
    } else if (score < 0.4 && criticalOss.length === 0) {
        narrative = `All systems operating within normal parameters. No critical anomalies detected across OSS or BSS domains. SLA compliance is maintained. The L4 agent continues passive monitoring.`;
    } else {
        narrative = `Mixed signals detected across the network. ${criticalOss.length + warningOss.length} OSS anomalies and ${criticalBss.length} BSS anomalies are being monitored. SLA risk at ${(score * 100).toFixed(1)}% — continued observation recommended.`;
    }

    return { riskLevel, score, findings, narrative, topDrivers, strongCorrs, criticalOss, criticalBss, regions };
}

function formatKPI(name: string): string {
    return name
        .replace(/_/g, " ")
        .replace(/\b(ms|pct|avg|max|min|p99|p95)\b/gi, (m) => m.toUpperCase())
        .replace(/\b\w/g, (c) => c.toUpperCase());
}

/* ── Component ────────────────────────────────────────────────────────────── */
export default function RootCauseAnalysis({ sla, ossAnomalies, bssAnomalies, correlations }: RCAProps) {
    const rca = buildRCA(sla, ossAnomalies, bssAnomalies, correlations);

    return (
        <div className="rca-panel">
            {/* Header */}
            <div className="rca-header">
                <div className="rca-header-left">
                    <div className={`rca-status-badge rca-${rca.riskLevel.toLowerCase()}`}>
                        <span className="rca-status-pulse" />
                        {rca.riskLevel}
                    </div>
                    <span className="rca-score">Risk: {(rca.score * 100).toFixed(1)}%</span>
                </div>
                <div className="rca-header-right">
                    <span className="rca-label">AI-Generated Analysis</span>
                </div>
            </div>

            {/* Narrative (the "story") */}
            <div className="rca-narrative">
                <div className="rca-narrative-icon">{"\uD83E\uDDE0"}</div>
                <p>{rca.narrative}</p>
            </div>

            {/* Findings list */}
            <div className="rca-findings">
                {rca.findings.map((f, i) => (
                    <div key={i} className={`rca-finding rca-finding-${f.severity}`}>
                        <div className="rca-finding-icon">{f.icon}</div>
                        <div className="rca-finding-content">
                            <div className="rca-finding-title">{f.title}</div>
                            <div className="rca-finding-detail">{f.detail}</div>
                        </div>
                    </div>
                ))}
            </div>

            {/* Feature importances mini-bar */}
            {rca.topDrivers.length > 0 && (
                <div className="rca-drivers">
                    <div className="rca-drivers-title">Top Risk Drivers</div>
                    {rca.topDrivers.map(([name, imp]) => (
                        <div key={name} className="rca-driver-row">
                            <span className="rca-driver-name">{formatKPI(name)}</span>
                            <div className="rca-driver-bar-bg">
                                <div
                                    className="rca-driver-bar"
                                    style={{ width: `${Math.min(imp * 100, 100)}%` }}
                                />
                            </div>
                            <span className="rca-driver-pct">{(imp * 100).toFixed(0)}%</span>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
