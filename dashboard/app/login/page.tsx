"use client";
import { useState, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { Activity, Users, Cpu, Sparkles, Mail, Lock, Eye, EyeOff, ArrowRight, Brain, Shield, Wrench } from 'lucide-react';

// Client-side role hint from a fixed demo-account map. Purely cosmetic — no server
// call, so it never confirms account existence or leaks roles (no enumeration).
const ROLE_MAP: Record<string, { label: string; Icon: typeof Shield; cls: string }> = {
    'souhaylguenichi@gmail.com': { label: 'Administrator', Icon: Shield, cls: 'role-badge-admin' },
    'mariembouzouita@gmail.com': { label: 'Data Scientist', Icon: Brain, cls: 'role-badge-ds' },
    'rahmabouraoui@gmail.com': { label: 'Telecom Engineer', Icon: Wrench, cls: 'role-badge-eng' },
};
import NetworkOrb from '../../components/NetworkOrb';

function NeXoMark({ size = 40 }: { size?: number }) {
    return (
        <svg width={size} height={size} viewBox="0 0 40 40" fill="none" aria-hidden="true">
            <defs>
                <linearGradient id="nx-mark-grad" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stopColor="#00E5FF" />
                    <stop offset="60%" stopColor="#00B8D4" />
                    <stop offset="100%" stopColor="#0066FF" />
                </linearGradient>
            </defs>
            <path d="M20 3L35 11.75V29.25L20 38L5 29.25V11.75L20 3Z"
                stroke="url(#nx-mark-grad)" strokeWidth="2" strokeLinejoin="round" />
            <circle cx="20" cy="20" r="4" fill="url(#nx-mark-grad)" />
            <line x1="20" y1="16" x2="8"  y2="9.5"  stroke="#00B8D4" strokeWidth="1.2" opacity="0.6" />
            <line x1="20" y1="16" x2="32" y2="9.5"  stroke="#00B8D4" strokeWidth="1.2" opacity="0.6" />
            <line x1="20" y1="24" x2="8"  y2="30.5" stroke="#00B8D4" strokeWidth="1.2" opacity="0.6" />
            <line x1="20" y1="24" x2="32" y2="30.5" stroke="#00B8D4" strokeWidth="1.2" opacity="0.6" />
        </svg>
    );
}

function LeftPane() {
    return (
        <aside className="login-left-pane">
            {/* TOP — Brand row */}
            <motion.div
                className="left-brand-row"
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5 }}
            >
                <div className="left-brand-logo">
                    <NeXoMark size={42} />
                </div>
                <div className="left-brand-text">
                    <span className="left-brand-name">NeXo</span>
                    <span className="left-brand-tag">
                        <Sparkles size={11} strokeWidth={2.5} />
                        AI-NATIVE NETWORK
                    </span>
                </div>
            </motion.div>

            {/* MID — Hook headline */}
            <motion.div
                className="left-hook"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.7, delay: 0.15 }}
            >
                <h1 className="left-headline">
                    Spot network failures{' '}
                    <span className="left-headline-accent">before</span>{' '}
                    your customers feel them.
                </h1>
                <p className="left-subhead">
                    AI agents that watch every cell, predict every drop, and act on their own — so your network heals itself.
                </p>
            </motion.div>

            {/* MID-BOTTOM — Network orb visual */}
            <motion.div
                className="left-viz"
                initial={{ opacity: 0, scale: 0.92 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.8, delay: 0.3 }}
            >
                <NetworkOrb />
            </motion.div>

            {/* BOTTOM — Stat tiles */}
            <motion.div
                className="left-stats"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6, delay: 0.45 }}
            >
                <div className="left-stat">
                    <div className="left-stat-icon"><Activity size={18} strokeWidth={2.2} /></div>
                    <div className="left-stat-text">
                        <span className="left-stat-value">19M+</span>
                        <span className="left-stat-label">cells live</span>
                    </div>
                </div>
                <div className="left-stat-divider" />
                <div className="left-stat">
                    <div className="left-stat-icon"><Users size={18} strokeWidth={2.2} /></div>
                    <div className="left-stat-text">
                        <span className="left-stat-value">2.47M</span>
                        <span className="left-stat-label">subscribers</span>
                    </div>
                </div>
                <div className="left-stat-divider" />
                <div className="left-stat">
                    <div className="left-stat-icon"><Brain size={18} strokeWidth={2.2} /></div>
                    <div className="left-stat-text">
                        <span className="left-stat-value">L4</span>
                        <span className="left-stat-label">autonomous</span>
                    </div>
                </div>
            </motion.div>
        </aside>
    );
}

function LoginContent() {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const [success, setSuccess] = useState(false);
    const router = useRouter();
    const search = useSearchParams();
    // Default to root; middleware routes each persona to their own landing page.
    const redirect = search.get('redirect') || '/';
    const roleInfo = ROLE_MAP[email.trim().toLowerCase()];

    const submit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setLoading(true);
        try {
            const res = await fetch('/api/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password }),
            });
            if (res.ok) {
                setSuccess(true);
                setTimeout(() => {
                    router.push(redirect);
                    router.refresh();
                }, 800);
            } else {
                let msg = 'Invalid credentials';
                try { const data = await res.json(); msg = data.error || msg; } catch { }
                setError(msg);
                setLoading(false);
            }
        } catch {
            setError('Connection failed. Is the server running?');
            setLoading(false);
        }
    };

    return (
        <div className="login-shell">
            <div className="login-bg-orb login-bg-orb-1" />
            <div className="login-bg-orb login-bg-orb-2" />
            <div className="login-bg-orb login-bg-orb-3" />
            <div className="login-bg-grid" />

            <LeftPane />

            <div className="login-right-pane">
                <motion.div
                    className="login-page-root"
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.5, delay: 0.15, ease: 'easeOut' }}
                >
                    <div className={`login-container ${success ? 'login-success-state' : ''}`}>
                        <div className="login-top-accent" />

                        <div className="login-card-logo">
                            <NeXoMark size={44} />
                        </div>

                        <div className="login-form-header">
                            <h2 className="login-form-title">Welcome back</h2>
                            <p className="login-form-sub">Sign in to your NeXo workspace</p>
                        </div>

                        <form onSubmit={submit} className="login-form">
                            <div className="login-field">
                                <label className="login-label" htmlFor="email">Email</label>
                                <div className="login-input-wrapper">
                                    <span className="login-input-icon">
                                        <Mail size={16} strokeWidth={2} />
                                    </span>
                                    <input
                                        id="email"
                                        type="email"
                                        value={email}
                                        onChange={(e) => setEmail(e.target.value)}
                                        placeholder="you@company.com"
                                        autoFocus
                                        autoComplete="email"
                                        className="login-input"
                                    />
                                </div>
                                {roleInfo && (
                                    <motion.div
                                        className={`login-role-badge ${roleInfo.cls}`}
                                        initial={{ opacity: 0, y: -4 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        transition={{ duration: 0.25 }}
                                    >
                                        <roleInfo.Icon size={13} strokeWidth={2.4} />
                                        <span>{roleInfo.label}</span>
                                        <span className="login-role-badge-hint">account</span>
                                    </motion.div>
                                )}
                            </div>

                            <div className="login-field">
                                <label className="login-label" htmlFor="password">Password</label>
                                <div className="login-input-wrapper">
                                    <span className="login-input-icon">
                                        <Lock size={16} strokeWidth={2} />
                                    </span>
                                    <input
                                        id="password"
                                        type={showPassword ? 'text' : 'password'}
                                        value={password}
                                        onChange={(e) => setPassword(e.target.value)}
                                        placeholder="Enter password"
                                        autoComplete="current-password"
                                        className="login-input login-input-with-eye"
                                    />
                                    <button
                                        type="button"
                                        className="login-eye-btn"
                                        onClick={() => setShowPassword(v => !v)}
                                        aria-label={showPassword ? 'Hide password' : 'Show password'}
                                        tabIndex={-1}
                                    >
                                        {showPassword ? <EyeOff size={16} strokeWidth={2} /> : <Eye size={16} strokeWidth={2} />}
                                    </button>
                                </div>
                            </div>

                            {error && (
                                <div className="login-error">{error}</div>
                            )}

                            <button type="submit" className="login-submit" disabled={loading || success}>
                                {success ? (
                                    <><span className="login-check-icon">✓</span> Access Granted</>
                                ) : loading ? (
                                    <><span className="spinner" /> Authenticating...</>
                                ) : (
                                    <>Sign In <ArrowRight size={16} strokeWidth={2.4} /></>
                                )}
                            </button>
                        </form>

                        <div className="login-switch">
                            New here?{' '}
                            <Link href="/signup" className="login-switch-link">Create your account</Link>
                        </div>

                        <div className="login-switch" style={{ marginTop: 4 }}>
                            <Link href="/forgot-password" className="login-switch-link" style={{ fontSize: 12 }}>Forgot your password?</Link>
                        </div>

                        <div className="login-trust-row">
                            <span className="login-trust-item">
                                <Cpu size={11} strokeWidth={2.2} /> v3.0
                            </span>
                            <span className="login-trust-dot" />
                            <span className="login-trust-item">L4 ADN</span>
                            <span className="login-trust-dot" />
                            <span className="login-trust-item">Cloud-Native</span>
                        </div>
                    </div>
                </motion.div>
            </div>
        </div>
    );
}

export default function LoginPage() {
    return (
        <Suspense fallback={
            <div className="login-shell">
                <div className="login-right-pane" style={{ gridColumn: '1 / -1' }}>
                    <div className="login-page-root">
                        <div className="login-container">
                            <div style={{ textAlign: 'center', padding: 40, color: '#64748B' }}>
                                <div className="spinner" style={{ width: 24, height: 24, margin: '0 auto 16px' }} />
                                Loading...
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        }>
            <LoginContent />
        </Suspense>
    );
}
