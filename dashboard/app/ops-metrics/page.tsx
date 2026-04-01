export default function OpsMetricsPage() {
    return (
        <div className="grid" style={{ gap: 24 }}>
            <div className="page-header">
                <h1>Platform Health &amp; Observability</h1>
                <p>Prometheus metrics + Grafana dashboards monitoring API gateway, AI service, and infrastructure health</p>
            </div>

            {/* Service Status Cards */}
            <div className="grid grid-3">
                <div className="card card-compact">
                    <div className="stat-card">
                        <div className="stat-icon success">{'\u2713'}</div>
                        <div className="stat-content">
                            <div className="stat-label">API Gateway</div>
                            <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--color-success)' }}>:8000 /metrics</div>
                            <div className="stat-sub">FastAPI + prometheus-instrumentator</div>
                        </div>
                    </div>
                </div>
                <div className="card card-compact">
                    <div className="stat-card">
                        <div className="stat-icon success">{'\u2713'}</div>
                        <div className="stat-content">
                            <div className="stat-label">AI Service</div>
                            <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--color-success)' }}>:8001 /metrics</div>
                            <div className="stat-sub">3 ML models + inference endpoints</div>
                        </div>
                    </div>
                </div>
                <div className="card card-compact">
                    <div className="stat-card">
                        <div className="stat-icon info">{'\u2661'}</div>
                        <div className="stat-content">
                            <div className="stat-label">Prometheus</div>
                            <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--color-info)' }}>:9090 scrape 15s</div>
                            <div className="stat-sub">2 targets: api-gateway, ai-service</div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Architecture explanation */}
            <div className="card" style={{ padding: '18px 24px' }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 12, textTransform: 'uppercase', letterSpacing: '0.4px' }}>
                    Observability Stack Architecture
                </div>
                <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap', fontSize: 12 }}>
                    <span className="badge badge-info">API Gateway :8000</span>
                    <span style={{ color: 'var(--text-muted)' }}>/metrics {'\u2192'}</span>
                    <span className="badge badge-purple">Prometheus :9090</span>
                    <span style={{ color: 'var(--text-muted)' }}>PromQL {'\u2192'}</span>
                    <span className="badge badge-success">Grafana :3000</span>
                </div>
                <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap', fontSize: 12, marginTop: 8 }}>
                    <span className="badge badge-info">AI Service :8001</span>
                    <span style={{ color: 'var(--text-muted)' }}>/metrics {'\u2192'}</span>
                    <span className="badge badge-purple">Prometheus :9090</span>
                    <span style={{ color: 'var(--text-muted)' }}>PromQL {'\u2192'}</span>
                    <span className="badge badge-success">Grafana :3000</span>
                </div>
                <div style={{ marginTop: 14, padding: '10px 14px', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-sm)', fontSize: 12, color: 'var(--text-secondary)' }}>
                    <strong>Metrics exposed:</strong> http_requests_total (counter), http_request_duration_seconds (histogram), http_requests_in_progress (gauge) — auto-instrumented by prometheus-fastapi-instrumentator
                </div>
            </div>

            {/* Grafana Embed */}
            <div className="card card-accent-top">
                <div className="section-title">
                    <span className="dot"></span>
                    Grafana Dashboard
                    <span className="section-subtitle">
                        <a href="http://localhost:3000/d/ai-ops-overview" target="_blank" rel="noopener noreferrer"
                            style={{ color: 'var(--color-info)', textDecoration: 'underline' }}>
                            Open in full screen
                        </a>
                    </span>
                </div>
                <iframe
                    className="grafana-embed"
                    src="http://localhost:3000/d/ai-ops-overview?orgId=1&kiosk&theme=dark"
                    style={{ minHeight: 650 }}
                />
            </div>

            {/* Direct Links */}
            <div className="grid grid-2">
                <a href="http://localhost:3000" target="_blank" rel="noopener noreferrer" className="card card-compact" style={{ cursor: 'pointer' }}>
                    <div className="stat-card">
                        <div className="stat-icon success">{'\u2197'}</div>
                        <div className="stat-content">
                            <div className="stat-label">Open Grafana</div>
                            <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>localhost:3000 &middot; admin/admin</div>
                        </div>
                    </div>
                </a>
                <a href="http://localhost:9090" target="_blank" rel="noopener noreferrer" className="card card-compact" style={{ cursor: 'pointer' }}>
                    <div className="stat-card">
                        <div className="stat-icon purple">{'\u2197'}</div>
                        <div className="stat-content">
                            <div className="stat-label">Open Prometheus</div>
                            <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>localhost:9090 &middot; query & targets</div>
                        </div>
                    </div>
                </a>
            </div>
        </div>
    );
}
