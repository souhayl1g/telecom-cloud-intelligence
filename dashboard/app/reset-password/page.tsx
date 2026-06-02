"use client";
import { useState, useEffect, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { Lock, Eye, EyeOff, ArrowRight, AlertCircle, CheckCircle } from 'lucide-react';

function ResetPasswordContent() {
    const [password, setPassword] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const [loading, setLoading] = useState(false);
    const [success, setSuccess] = useState(false);
    const [error, setError] = useState('');
    const [tokenError, setTokenError] = useState('');
    const router = useRouter();
    const searchParams = useSearchParams();
    const token = searchParams.get('token');

    useEffect(() => {
        if (!token) {
            setTokenError('Invalid or missing reset token. Please request a new reset link.');
        }
    }, [token]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!token) return;
        setLoading(true);
        setError('');
        try {
            const res = await fetch('/api/reset-password', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ token, password }),
            });
            const data = await res.json();
            if (!res.ok) {
                setError(data.detail || 'Failed to reset password');
            } else {
                setSuccess(true);
                document.cookie = `auth_token=${data.access_token}; path=/; max-age=${data.expires_in || 86400}`;
                setTimeout(() => router.push('/overview'), 1500);
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
                                <Lock size={24} color="#fff" />
                            </div>
                            <h1 className="login-title">New Password</h1>
                            <p className="login-subtitle">Create a strong password for your account</p>
                        </div>

                        {tokenError ? (
                            <div style={{ textAlign: 'center', padding: '24px 0' }}>
                                <AlertCircle size={48} color="#E6002D" style={{ margin: '0 auto 16px' }} />
                                <h3 style={{ color: '#E6002D', marginBottom: 8 }}>Invalid Link</h3>
                                <p style={{ color: '#94a3b8', fontSize: 14, marginBottom: 24 }}>{tokenError}</p>
                                <button type="button" onClick={() => router.push('/forgot-password')} className="login-submit">
                                    Request New Link <ArrowRight size={16} strokeWidth={2.4} />
                                </button>
                            </div>
                        ) : success ? (
                            <div style={{ textAlign: 'center', padding: '24px 0' }}>
                                <CheckCircle size={48} color="#34d399" style={{ margin: '0 auto 16px' }} />
                                <h3 style={{ color: '#34d399', marginBottom: 8 }}>Password Updated</h3>
                                <p style={{ color: '#94a3b8', fontSize: 14, marginBottom: 24 }}>
                                    Your password has been reset. Redirecting to dashboard...
                                </p>
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
                                    <label className="login-label">New Password</label>
                                    <div className="login-input-wrap">
                                        <Lock size={16} className="login-input-icon" />
                                        <input
                                            type={showPassword ? 'text' : 'password'}
                                            required
                                            minLength={8}
                                            maxLength={128}
                                            value={password}
                                            onChange={e => setPassword(e.target.value)}
                                            className="login-input"
                                            placeholder="Min 8 characters"
                                        />
                                        <button
                                            type="button"
                                            className="login-eye-btn"
                                            onClick={() => setShowPassword(!showPassword)}
                                            tabIndex={-1}
                                        >
                                            {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                                        </button>
                                    </div>
                                </div>

                                <button type="submit" className="login-submit" disabled={loading || !token}>
                                    {loading ? (
                                        <><span className="spinner" /> Updating...</>
                                    ) : (
                                        <>Reset Password <ArrowRight size={16} strokeWidth={2.4} /></>
                                    )}
                                </button>
                            </form>
                        )}

                        <div className="login-switch">
                            <Link href="/login" className="login-switch-link">Back to Sign In</Link>
                        </div>
                    </div>
                </motion.div>
            </div>
        </div>
    );
}

export default function ResetPasswordPage() {
    return (
        <Suspense fallback={
            <div className="login-shell">
                <div className="login-right-pane" style={{ gridColumn: '1 / -1' }}>
                    <div style={{ textAlign: 'center', padding: 40, color: '#64748B' }}>
                        <div className="spinner" style={{ width: 24, height: 24, margin: '0 auto 16px' }} />
                        Loading...
                    </div>
                </div>
            </div>
        }>
            <ResetPasswordContent />
        </Suspense>
    );
}
