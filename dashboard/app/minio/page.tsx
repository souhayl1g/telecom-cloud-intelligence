"use client";

import { useEffect, useState, useCallback } from "react";
import { Database, RefreshCw, Download, FolderOpen } from "lucide-react";

import SectionHeader from "../../components/ui/SectionHeader";
import ErrorState from "../../components/ui/ErrorState";
import { SkeletonTable } from "../../components/ui/LoadingSkeleton";
import { formatTunisDateTime } from "../../lib/time";

interface Bucket { name: string; objects: number | null; bytes: number | null; }
interface S3Object { key: string; size: number; last_modified: string | null; }

const fmtBytes = (b: number | null) => {
    if (b === null || b === undefined) return "—";
    if (b === 0) return "0 B";
    const u = ["B", "KB", "MB", "GB"]; const i = Math.floor(Math.log(b) / Math.log(1024));
    return `${(b / Math.pow(1024, i)).toFixed(i === 0 ? 0 : 1)} ${u[i]}`;
};

export default function MinioPage() {
    const [buckets, setBuckets] = useState<Bucket[]>([]);
    const [active, setActive] = useState<string | null>(null);
    const [objects, setObjects] = useState<S3Object[]>([]);
    const [loading, setLoading] = useState(true);
    const [objLoading, setObjLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const loadBuckets = useCallback(async () => {
        setLoading(true); setError(null);
        try {
            const r = await fetch("/api/minio", { cache: "no-store" });
            const d = await r.json();
            if (d.error && !d.buckets) throw new Error(d.error);
            setBuckets(d.buckets ?? []);
        } catch (e: any) { setError(String(e?.message ?? e)); }
        finally { setLoading(false); }
    }, []);

    useEffect(() => { loadBuckets(); }, [loadBuckets]);

    const openBucket = async (name: string) => {
        setActive(name); setObjLoading(true);
        try {
            const r = await fetch(`/api/minio?bucket=${encodeURIComponent(name)}`, { cache: "no-store" });
            const d = await r.json();
            setObjects(d.objects ?? []);
        } catch { setObjects([]); }
        finally { setObjLoading(false); }
    };

    const download = async (key: string) => {
        if (!active) return;
        const r = await fetch(`/api/minio?presign=1&bucket=${encodeURIComponent(active)}&key=${encodeURIComponent(key)}`, { cache: "no-store" });
        const d = await r.json();
        if (d.url) window.open(d.url, "_blank");
    };

    return (
        <div style={{ padding: "24px 32px", display: "flex", flexDirection: "column", gap: 20 }}>
            <SectionHeader
                icon={Database}
                title="Data Lake Objects (MinIO)"
                subtitle="Native object browser over the 3-layer lake + reports — no external MinIO console. Presigned, short-lived downloads."
                tone="default"
                action={<button className="l4-btn" onClick={loadBuckets} disabled={loading}><RefreshCw size={14} strokeWidth={2.2} /></button>}
            />

            {error && <ErrorState message={error} onRetry={loadBuckets} />}

            {loading ? <div className="grid grid-4"><SkeletonTable rows={1} /></div> : (
                <div className="grid grid-4">
                    {buckets.map((b) => (
                        <button key={b.name} className="card" onClick={() => openBucket(b.name)}
                            style={{ padding: 16, textAlign: "left", cursor: "pointer",
                                border: active === b.name ? "1px solid var(--brand-primary, #007DBA)" : undefined }}>
                            <div style={{ display: "flex", alignItems: "center", gap: 8, fontWeight: 600, textTransform: "capitalize" }}>
                                <FolderOpen size={15} style={{ color: "#007DBA" }} /> {b.name}
                            </div>
                            <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 6 }}>
                                {b.objects ?? "—"} objects · {fmtBytes(b.bytes)}
                            </div>
                        </button>
                    ))}
                </div>
            )}

            {active && (
                <div className="card" style={{ padding: 0, overflowX: "auto" }}>
                    <div style={{ padding: "12px 16px", fontWeight: 600, fontSize: 13 }}>{active} — first 100 objects</div>
                    {objLoading ? <SkeletonTable rows={5} /> : (
                        <table className="table" style={{ width: "100%", borderCollapse: "collapse", minWidth: 560 }}>
                            <thead>
                                <tr style={{ fontSize: 12, opacity: 0.75, textAlign: "left" }}>
                                    <th style={{ padding: "10px 16px" }}>Key</th>
                                    <th style={{ padding: "10px 16px", textAlign: "right" }}>Size</th>
                                    <th style={{ padding: "10px 16px", textAlign: "right" }}>Modified</th>
                                    <th style={{ padding: "10px 16px" }} />
                                </tr>
                            </thead>
                            <tbody>
                                {objects.map((o) => (
                                    <tr key={o.key}>
                                        <td style={{ padding: "8px 16px", fontFamily: "var(--font-mono, monospace)", fontSize: 12 }}>{o.key}</td>
                                        <td style={{ padding: "8px 16px", textAlign: "right" }}>{fmtBytes(o.size)}</td>
                                        <td style={{ padding: "8px 16px", textAlign: "right", fontSize: 12, color: "var(--text-muted)" }}>
                                            {o.last_modified ? formatTunisDateTime(o.last_modified) : "—"}
                                        </td>
                                        <td style={{ padding: "8px 16px", textAlign: "right" }}>
                                            <button className="l4-btn" onClick={() => download(o.key)} title="Presigned download">
                                                <Download size={13} strokeWidth={2.2} />
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                                {objects.length === 0 && (
                                    <tr><td colSpan={4} style={{ padding: 20, textAlign: "center", color: "var(--text-muted)" }}>Empty bucket.</td></tr>
                                )}
                            </tbody>
                        </table>
                    )}
                </div>
            )}
        </div>
    );
}
