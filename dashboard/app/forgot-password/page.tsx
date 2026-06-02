"use client";
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { Mail, ArrowRight, AlertCircle, CheckCircle } from 'lucide-react';

export default function ForgotPasswordPage() {
    const [email, setEmail] = useState('');
    const [loading, setLoading] = useState(false);
    const [success, setSuccess] = useState(false);
    const [error, setError] = useState('');
    const [fallbackLink, setFallbackLink] = useState('');
    const router = useRouter();

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError('');
        setFallbackLink('');
        try {
            const res = await fetch('/api/forgot-password', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email }),
            });
            const data = await res.json();
            if (!res.ok) {
                setError(data.detail || 'Failed to send reset link');
            } else {
                setSuccess(true);
                if (data.fallback_link) {
                    setFallbackLink(data.fallback_link);
                }
            }
        } catch {
            setError('Network error. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="login-shell">
            <div className="login-right-pane" style={{ gridColumn: '1 / -1' }}>
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5 }}
                    className="login-page-root"
                >
                    <div className="login-container">
                        <div style={{ textAlign: 'center', marginBottom: 32 }}>
                            <div style={{ width: 48, height: 48, borderRadius: 12, background: 'linear-gradient(135deg, #00D4FF, #0077B6)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px' }}>
                                <Mail size={24} color="#fff" />
                            </div>
                            <h1 className="login-title">Reset Password</h1>
                            <p className="login-subtitle">Enter your email and we will send you a reset link</p>
                        </div>

                        {success ? (
                            <div style={{ textAlign: 'center', padding: '24px 0' }}>
                                <CheckCircle size={48} color="#34d399" style={{ margin: '0 auto 16px' }} />
                                <h3 style={{ color: '#34d399', marginBottom: 8 }}>Check your inbox</h3>
                                <p style={{ color: '#94a3b8', fontSize: 14, marginBottom: 24 }}>
                                    If an account exists for <strong>{email}</strong>, a reset link has been sent.
                                </p>
                                {fallbackLink ? (
                                    <div style={{ background: '#0f172a', border: '1px solid #334155', borderRadius: 8, padding: 16, marginBottom: 24, textAlign: 'left' }}>
                                        <p style={{ color: '#fbbf24', fontSize: 12, fontWeight: 600, marginBottom: 8, textTransform: 'uppercase', letterSpacing: 0.5 }}>
                                            ⚠ SMTP not configured — Dev fallback
                                        </p>
                                        <p style={{ color: '#94a3b8', fontSize: 13, marginBottom: 8 }}>
                                            Email could not be sent. Copy this link to reset your password:
                                        </p>
                                        <code style={{ display: 'block', background: '#1e293b', color: '#00D4FF', padding: '10px 12px', borderRadius: 6, fontSize: 12, wordBreak: 'break-all', userSelect: 'all' }}>
                                            {fallbackLink}
                                        </code>
                                    </div>
                                ) : (
                                    <p style={{ color: '#64748B', fontSize: 12, marginBottom: 24 }}>
                                        (Console fallback active — check auth-service logs if SMTP is not configured)
                                    </p>
                                )}
                                <button type="button" onClick={() => router.push('/login')} className="login-submit">
                                    Back to Sign In <ArrowRight size={16} strokeWidth={2.4} />
                                </button>
                            </div>
                        ) : (
                            <form onSubmit={handleSubmit}>
                                {error && (
                                    <div className="login-error">
                                        <AlertCircle size={16} />
                                        <span>{error}</span>
                                    </div>
                                )}

                                <div className="login-field">
                                    <label className="login-label">Email Address</label>
                                    <div className="login-input-wrap">
                                        <Mail size={16} className="login-input-icon" />
                                        <input
                                            type="email"
                                            required
                                            value={email}
                                            onChange={e => setEmail(e.target.value)}
                                            className="login-input"
                                            placeholder="you@company.com"
                                        />
                                    </div>
                                </div>

                                <button type="submit" className="login-submit" disabled={loading}>
                                    {loading ? (
                                        <><span className="spinner" /> Sending...</>
                                    ) : (
                                        <>Send Reset Link <ArrowRight size={16} strokeWidth={2.4} /></>
                                    )}
                                </button>
                            </form>
                        )}

                        <div className="login-switch">
                            Remember your password?{' '}
                            <Link href="/login" className="login-switch-link">Sign in</Link>
                        </div>
                    </div>
                </motion.div>
            </div>
        </div>
    );
}
