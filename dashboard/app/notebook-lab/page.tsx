"use client";

import { useEffect, useState, useCallback } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { BookOpen, FileText, RefreshCw } from "lucide-react";

import SectionHeader from "../../components/ui/SectionHeader";
import ErrorState from "../../components/ui/ErrorState";
import { SkeletonStatCard } from "../../components/ui/LoadingSkeleton";

interface NB { name: string; title: string; purpose: string; }
interface Card { model: string; markdown: string; }
interface Lab { notebooks: NB[]; cards: Card[] | null; summary_markdown: string | null; error?: string; }

const CARD_TITLE: Record<string, string> = {
    cem_v3: "CEM Score — LightGBM (DART)",
    oss_vae_v3: "OSS Experience Anomaly — VAE",
    rat_underservice_v3: "RAT Underservice — XGBoost",
};

export default function NotebookLabPage() {
    const [data, setData] = useState<Lab | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [openCard, setOpenCard] = useState<string | null>(null);

    const load = useCallback(async () => {
        setLoading(true); setError(null);
        try {
            const r = await fetch("/api/notebooks", { cache: "no-store" });
            const json: Lab = await r.json();
            if (json.error && !json.cards) throw new Error(json.error);
            setData(json);
            if (json.cards?.length) setOpenCard(json.cards[0].model);
        } catch (e: any) { setError(String(e?.message ?? e)); }
        finally { setLoading(false); }
    }, []);

    useEffect(() => { load(); }, [load]);

    return (
        <div style={{ padding: "24px 32px", display: "flex", flexDirection: "column", gap: 20 }}>
            <SectionHeader
                icon={BookOpen}
                title="Notebook Lab"
                subtitle="The notebook work rendered as outputs inside the dashboard — model cards, metrics, training summary. No external Jupyter."
                tone="default"
                action={<button className="l4-btn" onClick={load} disabled={loading}><RefreshCw size={14} strokeWidth={2.2} /></button>}
            />

            {error && <ErrorState message={error} onRetry={load} />}

            {/* Notebook catalogue */}
            <div className="grid grid-3">
                {(data?.notebooks ?? []).map((nb) => (
                    <div key={nb.name} className="card" style={{ padding: 16 }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 8, fontWeight: 600, fontSize: 13 }}>
                            <FileText size={14} style={{ color: "#007DBA" }} /> {nb.title}
                        </div>
                        <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 6 }}>{nb.purpose}</div>
                        <div style={{ fontSize: 10, color: "var(--text-muted)", marginTop: 6, fontFamily: "var(--font-mono, monospace)" }}>{nb.name}.ipynb</div>
                    </div>
                ))}
            </div>

            {/* Model cards (rendered markdown) */}
            <SectionHeader icon={FileText} title="Model Cards" subtitle="Honest training artifacts produced by the notebooks." tone="success" />
            {loading && !data ? <SkeletonStatCard /> : (
                <>
                    <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                        {(data?.cards ?? []).map((c) => (
                            <button key={c.model} className={`l4-btn ${openCard === c.model ? "l4-btn-approve" : ""}`}
                                onClick={() => setOpenCard(c.model)}>
                                {CARD_TITLE[c.model] ?? c.model}
                            </button>
                        ))}
                    </div>
                    {(data?.cards ?? []).filter((c) => c.model === openCard).map((c) => (
                        <div key={c.model} className="card markdown-body" style={{ padding: 24, fontSize: 14, lineHeight: 1.6 }}>
                            <ReactMarkdown remarkPlugins={[remarkGfm]}>{c.markdown}</ReactMarkdown>
                        </div>
                    ))}
                </>
            )}

            {data?.summary_markdown && (
                <>
                    <SectionHeader icon={BookOpen} title="Master Training Summary" tone="default" />
                    <div className="card markdown-body" style={{ padding: 24, fontSize: 14, lineHeight: 1.6 }}>
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>{data.summary_markdown}</ReactMarkdown>
                    </div>
                </>
            )}
        </div>
    );
}
