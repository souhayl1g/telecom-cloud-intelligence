"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { ShieldCheck, UserPlus, RefreshCw, Users, Settings, Workflow, RotateCw, Pencil, Trash2, Activity, X } from "lucide-react";

import SectionHeader from "../../components/ui/SectionHeader";
import ErrorState from "../../components/ui/ErrorState";
import { SkeletonTable } from "../../components/ui/LoadingSkeleton";
import { ALL_ROLES, ROLE_LABEL, type Role } from "../../lib/roles";
import { formatTunisDate, formatTunisDateTime } from "../../lib/time";

interface Setting { key: string; value: any; updated_at: string; updated_by: string | null; }
interface PipelineRun { run_id: string; status: string; started_at: string; finished_at: string | null; duration_s: number | null; }

interface AdminUser {
    id: number;
    email: string;
    full_name: string | null;
    role: Role;
    is_active: boolean;
    provider: string;
    created_at: string;
    last_login: string | null;
}

interface ActivityRow {
    id: number;
    user_email: string | null;
    actor_email: string | null;
    action: string;
    detail: Record<string, any> | null;
    created_at: string;
}

const ACTION_LABEL: Record<string, string> = {
    login: "signed in",
    user_created: "created account",
    user_updated: "edited account",
    user_deleted: "deleted account",
    role_changed: "changed role",
    activated: "activated account",
    deactivated: "deactivated account",
};

export default function AdminPage() {
    const [users, setUsers] = useState<AdminUser[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [busy, setBusy] = useState<number | null>(null);
    const [msg, setMsg] = useState<string | null>(null);

    // create-user form
    const [email, setEmail] = useState("");
    const [fullName, setFullName] = useState("");
    const [password, setPassword] = useState("");
    const [newRole, setNewRole] = useState<Role>("data_scientist");
    const [creating, setCreating] = useState(false);

    // edit modal + activity feed
    const [editUser, setEditUser] = useState<AdminUser | null>(null);
    const [saving, setSaving] = useState(false);
    const [activity, setActivity] = useState<ActivityRow[]>([]);
    const [activityUser, setActivityUser] = useState<AdminUser | null>(null);
    const activityRef = useRef<HTMLDivElement>(null);

    const viewActivity = (u: AdminUser) => {
        setActivityUser(u);
        loadActivity(u.id);
        setTimeout(() => activityRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 60);
    };

    // settings + pipeline panels
    const [settings, setSettings] = useState<Setting[]>([]);
    const [runs, setRuns] = useState<PipelineRun[]>([]);
    const [reloading, setReloading] = useState(false);

    const loadSettings = useCallback(async () => {
        try {
            const r = await fetch("/api/admin?view=settings", { cache: "no-store" });
            const d = await r.json();
            if (Array.isArray(d.settings)) setSettings(d.settings);
        } catch { /* ignore */ }
    }, []);

    const loadPipeline = useCallback(async () => {
        try {
            const r = await fetch("/api/admin?view=pipeline", { cache: "no-store" });
            const d = await r.json();
            if (Array.isArray(d.runs)) setRuns(d.runs);
        } catch { /* ignore */ }
    }, []);

    const loadActivity = useCallback(async (userId?: number) => {
        try {
            const q = userId ? `?user_id=${userId}&limit=40` : "?limit=40";
            const r = await fetch(`/api/users/activity${q}`, { cache: "no-store" });
            const d = await r.json();
            if (Array.isArray(d)) setActivity(d);
        } catch { /* ignore */ }
    }, []);

    const saveSetting = async (key: string, raw: string) => {
        // values are JSON — parse so "30000"/"true"/'"dark"' store as the right type.
        let value: any = raw;
        try { value = JSON.parse(raw); } catch { /* keep as string */ }
        try {
            const r = await fetch("/api/admin", {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ [key]: value }),
            });
            const d = await r.json();
            if (Array.isArray(d.settings)) setSettings(d.settings);
            setMsg(`Setting '${key}' saved.`);
        } catch (e: any) { setMsg(`Save failed: ${e?.message ?? e}`); }
    };

    const reloadModels = async () => {
        setReloading(true); setMsg(null);
        try {
            const r = await fetch("/api/admin?action=reload-models", { method: "POST" });
            const d = await r.json();
            setMsg(r.ok ? "ai-service models hot-reloaded from disk." : `Reload failed: ${d.detail ?? d.error}`);
        } catch (e: any) { setMsg(`Reload failed: ${e?.message ?? e}`); }
        finally { setReloading(false); }
    };

    const load = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const r = await fetch("/api/users", { cache: "no-store" });
            if (r.status === 403) throw new Error("Admin role required");
            if (!r.ok) throw new Error(`HTTP ${r.status}`);
            setUsers(await r.json());
        } catch (e: any) {
            setError(String(e?.message ?? e));
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { load(); loadSettings(); loadPipeline(); loadActivity(); }, [load, loadSettings, loadPipeline, loadActivity]);

    const changeRole = async (id: number, role: Role) => {
        setBusy(id);
        try {
            const r = await fetch("/api/users", {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ user_id: id, role }),
            });
            if (!r.ok) throw new Error(`HTTP ${r.status}`);
            setUsers((prev) => prev.map((u) => (u.id === id ? { ...u, role } : u)));
            setMsg(`Role updated → ${ROLE_LABEL[role]}. User must re-login for it to take effect.`);
        } catch (e: any) {
            setMsg(`Failed: ${e?.message ?? e}`);
        } finally {
            setBusy(null);
        }
    };

    const toggleActive = async (u: AdminUser) => {
        setBusy(u.id);
        try {
            const r = await fetch("/api/users", {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ user_id: u.id, is_active: !u.is_active }),
            });
            if (!r.ok) { const d = await r.json().catch(() => ({})); throw new Error(d.detail || `HTTP ${r.status}`); }
            setUsers((prev) => prev.map((x) => (x.id === u.id ? { ...x, is_active: !u.is_active } : x)));
        } catch (e: any) {
            setMsg(`Failed: ${e?.message ?? e}`);
        } finally {
            setBusy(null);
        }
    };

    const createUser = async () => {
        setCreating(true);
        setMsg(null);
        try {
            const r = await fetch("/api/users", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email, full_name: fullName, password, role: newRole }),
            });
            const d = await r.json().catch(() => ({}));
            if (!r.ok) throw new Error(d.detail || `HTTP ${r.status}`);
            setMsg(`Created ${email} as ${ROLE_LABEL[newRole]}.`);
            setEmail(""); setFullName(""); setPassword("");
            await load();
        } catch (e: any) {
            setMsg(`Create failed: ${e?.message ?? e}`);
        } finally {
            setCreating(false);
        }
    };

    const saveUser = async (patch: Record<string, any>) => {
        if (!editUser) return;
        setSaving(true); setMsg(null);
        try {
            const r = await fetch("/api/users", {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ user_id: editUser.id, ...patch }),
            });
            const d = await r.json().catch(() => ({}));
            if (!r.ok) throw new Error(d.detail || `HTTP ${r.status}`);
            setMsg(`Updated ${d.email}.`);
            setEditUser(null);
            await load(); await loadActivity(activityUser?.id);
        } catch (e: any) {
            setMsg(`Update failed: ${e?.message ?? e}`);
        } finally {
            setSaving(false);
        }
    };

    const deleteUser = async (u: AdminUser) => {
        if (!confirm(`Delete ${u.email}? This cannot be undone.`)) return;
        setBusy(u.id); setMsg(null);
        try {
            const r = await fetch(`/api/users?id=${u.id}`, { method: "DELETE" });
            const d = await r.json().catch(() => ({}));
            if (!r.ok) throw new Error(d.detail || `HTTP ${r.status}`);
            setMsg(`Deleted ${u.email}.`);
            setUsers((prev) => prev.filter((x) => x.id !== u.id));
            await loadActivity(activityUser?.id);
        } catch (e: any) {
            setMsg(`Delete failed: ${e?.message ?? e}`);
        } finally {
            setBusy(null);
        }
    };

    return (
        <div style={{ padding: "24px 32px", display: "flex", flexDirection: "column", gap: 20 }}>
            <SectionHeader
                icon={ShieldCheck}
                title="Admin Console — Users & Roles"
                subtitle="Provision accounts and assign the three personas. Role changes apply on the user's next login (the role is carried in their JWT)."
                tone="default"
                action={
                    <button className="l4-btn" onClick={load} disabled={loading} title="Refresh">
                        <RefreshCw size={14} strokeWidth={2.2} /><span>Refresh</span>
                    </button>
                }
            />

            {msg && (
                <div className="card card-compact" style={{ fontSize: 13, color: "var(--text-muted)" }}>{msg}</div>
            )}

            {/* Create user */}
            <div className="card" style={{ padding: 18 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12, fontWeight: 600 }}>
                    <UserPlus size={15} /> Provision a new account
                </div>
                <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
                    <input placeholder="email" value={email} onChange={(e) => setEmail(e.target.value)} style={inp} />
                    <input placeholder="full name" value={fullName} onChange={(e) => setFullName(e.target.value)} style={inp} />
                    <input placeholder="password (≥8)" type="password" value={password} onChange={(e) => setPassword(e.target.value)} style={inp} />
                    <select value={newRole} onChange={(e) => setNewRole(e.target.value as Role)} style={inp}>
                        {ALL_ROLES.map((r) => <option key={r} value={r}>{ROLE_LABEL[r]}</option>)}
                    </select>
                    <button className="l4-btn l4-btn-approve" disabled={creating || !email || !fullName || password.length < 8}
                        onClick={createUser}>{creating ? "Creating…" : "Create"}</button>
                </div>
            </div>

            {error && <ErrorState message={error} onRetry={load} />}

            {loading ? (
                <SkeletonTable rows={5} />
            ) : (
                <div className="card" style={{ padding: 0, overflowX: "auto" }}>
                    <table className="table" style={{ width: "100%", borderCollapse: "collapse" }}>
                        <thead>
                            <tr style={{ fontSize: 12, opacity: 0.75, textAlign: "left" }}>
                                <th style={{ padding: "12px 16px" }}><Users size={13} style={{ verticalAlign: "middle" }} /> User</th>
                                <th style={{ padding: "12px 16px" }}>Role</th>
                                <th style={{ padding: "12px 16px" }}>Status</th>
                                <th style={{ padding: "12px 16px" }}>Provider</th>
                                <th style={{ padding: "12px 16px" }}>Created</th>
                                <th style={{ padding: "12px 16px" }}>Last login</th>
                                <th style={{ padding: "12px 16px", textAlign: "right" }}>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {users.map((u) => (
                                <tr key={u.id}>
                                    <td style={{ padding: "10px 16px" }}>
                                        <div style={{ fontWeight: 600 }}>{u.full_name || "—"}</div>
                                        <div style={{ fontSize: 11, color: "var(--text-muted)" }}>{u.email}</div>
                                    </td>
                                    <td style={{ padding: "10px 16px" }}>
                                        <select value={u.role} disabled={busy === u.id}
                                            onChange={(e) => changeRole(u.id, e.target.value as Role)} style={inp}>
                                            {ALL_ROLES.map((r) => <option key={r} value={r}>{ROLE_LABEL[r]}</option>)}
                                        </select>
                                    </td>
                                    <td style={{ padding: "10px 16px" }}>
                                        <button className={`l4-btn ${u.is_active ? "" : "l4-btn-reject"}`} disabled={busy === u.id}
                                            onClick={() => toggleActive(u)}
                                            style={{ color: u.is_active ? "#10B981" : "#DC2626" }}>
                                            {u.is_active ? "● Active" : "○ Disabled"}
                                        </button>
                                    </td>
                                    <td style={{ padding: "10px 16px", fontSize: 12, color: "var(--text-muted)" }}>{u.provider}</td>
                                    <td style={{ padding: "10px 16px", fontSize: 12, color: "var(--text-muted)" }}>{formatTunisDate(u.created_at)}</td>
                                    <td style={{ padding: "10px 16px", fontSize: 12, color: "var(--text-muted)" }}>{u.last_login ? formatTunisDateTime(u.last_login) : "—"}</td>
                                    <td style={{ padding: "10px 16px" }}>
                                        <div style={{ display: "flex", gap: 6, justifyContent: "flex-end" }}>
                                            <button className="l4-btn" disabled={busy === u.id} title="Edit"
                                                onClick={() => setEditUser(u)} style={{ padding: "8px 10px" }}>
                                                <Pencil size={13} strokeWidth={2.2} />
                                            </button>
                                            <button className="l4-btn" disabled={busy === u.id} title="View activity"
                                                onClick={() => viewActivity(u)} style={{ padding: "8px 10px" }}>
                                                <Activity size={13} strokeWidth={2.2} />
                                            </button>
                                            <button className="l4-btn l4-btn-reject" disabled={busy === u.id} title="Delete"
                                                onClick={() => deleteUser(u)} style={{ padding: "8px 10px", color: "#DC2626" }}>
                                                <Trash2 size={13} strokeWidth={2.2} />
                                            </button>
                                        </div>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}

            {/* ── Dashboard settings ─────────────────────────────── */}
            <SectionHeader icon={Settings} title="Dashboard Settings" subtitle="Key/value app settings (JSON). Press Enter in a field to save." tone="default" />
            <div className="card" style={{ padding: 0, overflowX: "auto" }}>
                <table className="table" style={{ width: "100%", borderCollapse: "collapse" }}>
                    <thead>
                        <tr style={{ fontSize: 12, opacity: 0.75, textAlign: "left" }}>
                            <th style={{ padding: "10px 16px" }}>Key</th>
                            <th style={{ padding: "10px 16px" }}>Value (JSON)</th>
                            <th style={{ padding: "10px 16px" }}>Updated</th>
                        </tr>
                    </thead>
                    <tbody>
                        {settings.map((s) => (
                            <tr key={s.key}>
                                <td style={{ padding: "8px 16px", fontFamily: "var(--font-mono, monospace)", fontSize: 12 }}>{s.key}</td>
                                <td style={{ padding: "8px 16px" }}>
                                    <input defaultValue={JSON.stringify(s.value)} style={{ ...inp, width: 220 }}
                                        onKeyDown={(e) => { if (e.key === "Enter") saveSetting(s.key, (e.target as HTMLInputElement).value); }} />
                                </td>
                                <td style={{ padding: "8px 16px", fontSize: 11, color: "var(--text-muted)" }}>
                                    {s.updated_at ? formatTunisDateTime(s.updated_at) : "—"}{s.updated_by ? ` · by ${s.updated_by}` : ""}
                                </td>
                            </tr>
                        ))}
                        {settings.length === 0 && <tr><td colSpan={3} style={{ padding: 18, textAlign: "center", color: "var(--text-muted)" }}>No settings.</td></tr>}
                    </tbody>
                </table>
            </div>

            {/* ── Pipeline & data controls ───────────────────────── */}
            <SectionHeader icon={Workflow} title="Pipeline & Data" subtitle="Recent pipeline runs + model hot-reload." tone="default"
                action={
                    <button className="l4-btn l4-btn-approve" onClick={reloadModels} disabled={reloading}>
                        <RotateCw size={14} strokeWidth={2.2} /> {reloading ? "Reloading…" : "Reload ML models"}
                    </button>
                } />
            <div className="card" style={{ padding: 0, overflowX: "auto" }}>
                <table className="table" style={{ width: "100%", borderCollapse: "collapse" }}>
                    <thead>
                        <tr style={{ fontSize: 12, opacity: 0.75, textAlign: "left" }}>
                            <th style={{ padding: "10px 16px" }}>Run</th>
                            <th style={{ padding: "10px 16px" }}>Status</th>
                            <th style={{ padding: "10px 16px" }}>Started</th>
                            <th style={{ padding: "10px 16px", textAlign: "right" }}>Duration</th>
                        </tr>
                    </thead>
                    <tbody>
                        {runs.map((r) => (
                            <tr key={r.run_id}>
                                <td style={{ padding: "8px 16px", fontFamily: "var(--font-mono, monospace)", fontSize: 11 }}>{r.run_id.slice(0, 18)}…</td>
                                <td style={{ padding: "8px 16px", color: r.status === "succeeded" ? "#10B981" : r.status === "failed" ? "#DC2626" : "var(--text-muted)" }}>{r.status}</td>
                                <td style={{ padding: "8px 16px", fontSize: 12, color: "var(--text-muted)" }}>{r.started_at ? formatTunisDateTime(r.started_at) : "—"}</td>
                                <td style={{ padding: "8px 16px", textAlign: "right", fontFamily: "var(--font-mono, monospace)" }}>{r.duration_s != null ? `${r.duration_s}s` : "—"}</td>
                            </tr>
                        ))}
                        {runs.length === 0 && <tr><td colSpan={4} style={{ padding: 18, textAlign: "center", color: "var(--text-muted)" }}>No runs.</td></tr>}
                    </tbody>
                </table>
            </div>

            {/* ── User activity feed ─────────────────────────────── */}
            <div ref={activityRef} style={{ scrollMarginTop: 16 }} />
            <SectionHeader icon={Activity}
                title={activityUser ? `Activity — ${activityUser.email}` : "User Activity"}
                subtitle="Logins and every admin action (create / edit / delete / role change), newest first."
                tone="default"
                action={activityUser
                    ? <button className="l4-btn" onClick={() => { setActivityUser(null); loadActivity(); }}>Show all</button>
                    : <button className="l4-btn" onClick={() => loadActivity()}><RefreshCw size={14} strokeWidth={2.2} /></button>}
            />
            <div className="card" style={{ padding: 0, overflowX: "auto" }}>
                <table className="table" style={{ width: "100%", borderCollapse: "collapse" }}>
                    <thead>
                        <tr style={{ fontSize: 12, opacity: 0.75, textAlign: "left" }}>
                            <th style={{ padding: "10px 16px" }}>When</th>
                            <th style={{ padding: "10px 16px" }}>Actor</th>
                            <th style={{ padding: "10px 16px" }}>Action</th>
                            <th style={{ padding: "10px 16px" }}>Target</th>
                            <th style={{ padding: "10px 16px" }}>Detail</th>
                        </tr>
                    </thead>
                    <tbody>
                        {activity.map((a) => (
                            <tr key={a.id}>
                                <td style={{ padding: "8px 16px", fontSize: 12, color: "var(--text-muted)", whiteSpace: "nowrap" }}>{formatTunisDateTime(a.created_at)}</td>
                                <td style={{ padding: "8px 16px", fontSize: 12 }}>{a.actor_email || "—"}</td>
                                <td style={{ padding: "8px 16px", fontSize: 12, fontWeight: 600 }}>{ACTION_LABEL[a.action] || a.action}</td>
                                <td style={{ padding: "8px 16px", fontSize: 12, color: "var(--text-muted)" }}>{a.user_email || "—"}</td>
                                <td style={{ padding: "8px 16px", fontSize: 11, color: "var(--text-muted)", fontFamily: "var(--font-mono, monospace)" }}>
                                    {a.detail ? Object.entries(a.detail).map(([k, v]) => `${k}: ${v}`).join(" · ") : "—"}
                                </td>
                            </tr>
                        ))}
                        {activity.length === 0 && <tr><td colSpan={5} style={{ padding: 18, textAlign: "center", color: "var(--text-muted)" }}>No activity yet.</td></tr>}
                    </tbody>
                </table>
            </div>

            {editUser && (
                <EditUserModal
                    user={editUser}
                    saving={saving}
                    onClose={() => setEditUser(null)}
                    onSave={saveUser}
                />
            )}
        </div>
    );
}

function EditUserModal({ user, saving, onClose, onSave }: {
    user: AdminUser;
    saving: boolean;
    onClose: () => void;
    onSave: (patch: Record<string, any>) => void;
}) {
    const [email, setEmail] = useState(user.email);
    const [fullName, setFullName] = useState(user.full_name || "");
    const [role, setRole] = useState<Role>(user.role);
    const [isActive, setIsActive] = useState(user.is_active);
    const [password, setPassword] = useState("");

    const submit = () => {
        const patch: Record<string, any> = {};
        if (email !== user.email) patch.email = email;
        if (fullName !== (user.full_name || "")) patch.full_name = fullName;
        if (role !== user.role) patch.role = role;
        if (isActive !== user.is_active) patch.is_active = isActive;
        if (password.length >= 8) patch.password = password;
        if (Object.keys(patch).length === 0) { onClose(); return; }
        onSave(patch);
    };

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="card" style={{ maxWidth: 420, width: "92%", padding: 22 }} onClick={(e) => e.stopPropagation()}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
                    <div style={{ fontWeight: 700, fontSize: 15 }}>Edit user</div>
                    <button className="l4-btn" onClick={onClose} title="Close"><X size={15} strokeWidth={2.4} /></button>
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                    <label style={lbl}>Email
                        <input value={email} onChange={(e) => setEmail(e.target.value)} style={{ ...inp, width: "100%" }} />
                    </label>
                    <label style={lbl}>Full name
                        <input value={fullName} onChange={(e) => setFullName(e.target.value)} style={{ ...inp, width: "100%" }} />
                    </label>
                    <label style={lbl}>Role
                        <select value={role} onChange={(e) => setRole(e.target.value as Role)} style={{ ...inp, width: "100%" }}>
                            {ALL_ROLES.map((r) => <option key={r} value={r}>{ROLE_LABEL[r]}</option>)}
                        </select>
                    </label>
                    <label style={{ ...lbl, flexDirection: "row", alignItems: "center", gap: 8 }}>
                        <input type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} /> Active
                    </label>
                    <label style={lbl}>New password (optional, ≥8)
                        <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="leave blank to keep" style={{ ...inp, width: "100%" }} />
                    </label>
                    <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 6 }}>
                        <button className="l4-btn" onClick={onClose}>Cancel</button>
                        <button className="l4-btn l4-btn-approve" disabled={saving} onClick={submit}>{saving ? "Saving…" : "Save changes"}</button>
                    </div>
                </div>
            </div>
        </div>
    );
}

const lbl: React.CSSProperties = {
    display: "flex", flexDirection: "column", gap: 5, fontSize: 12,
    fontWeight: 600, color: "var(--text-secondary, #475569)",
};

const inp: React.CSSProperties = {
    padding: "8px 10px", borderRadius: 8, fontSize: 13,
    background: "var(--glass-bg, rgba(255,255,255,0.04))",
    border: "1px solid var(--glass-border, rgba(255,255,255,0.12))", color: "inherit",
};
