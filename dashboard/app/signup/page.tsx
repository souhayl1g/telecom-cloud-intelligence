"use client";
import { useState, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';

const AUTH_BASE = process.env.NEXT_PUBLIC_AUTH_BASE_URL || 'http://localhost:8002';

function SignupContent() {
    const [fullName, setFullName] = useState('');
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const [success, setSuccess] = useState(false);
    const router = useRouter();
    const search = useSearchParams();
    const redirect = search.get('redirect') || '/overview';

    const submit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');

        if (password !== confirmPassword) {
            setError('Passwords do not match');
            return;
        }
        if (password.length < 8) {
            setError('Password must be at least 8 characters');
            return;
        }

        setLoading(true);
        try {
            const res = await fetch('/api/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action: 'signup', email, password, full_name: fullName }),
            });
            if (res.ok) {
                setSuccess(true);
                setTimeout(() => {
                    router.push(redirect);
                    router.refresh();
                }, 800);
            } else {
                let msg = 'Signup failed';
                try { const data = await res.json(); msg = data.error || msg; } catch {}
                setError(msg);
                setLoading(false);
            }
        } catch {
            setError('Connection failed. Is the server running?');
            setLoading(false);
        }
    };

    return (
        <div className="login-page-root">
            <div className="login-bg-orb login-bg-orb-1" />
            <div className="login-bg-orb login-bg-orb-2" />
            <div className="login-bg-orb login-bg-orb-3" />
            <div className="login-bg-grid" />

            <div className={`login-container ${success ? 'login-success-state' : ''}`}>
                {/* Brand Section */}
                <div className="login-brand">
                    <div className="login-brand-icon">
                        <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
                            <rect width="48" height="48" rx="14" fill="url(#brand-gradient-s)" />
                            <path d="M16 24L22 30L32 18" stroke="white" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
                            <defs>
                                <linearGradient id="brand-gradient-s" x1="0" y1="0" x2="48" y2="48">
                                    <stop stopColor="#a78bfa" />
                                    <stop offset="0.5" stopColor="#6366f1" />
                                    <stop offset="1" stopColor="#4f46e5" />
                                </linearGradient>
                            </defs>
                        </svg>
                    </div>
                    <h1 className="login-title">Create Account</h1>
                    <p className="login-subtitle">Telecom Cloud Intelligence Platform</p>
                </div>

                {/* Signup Form */}
                <form onSubmit={submit} className="login-form">
                    <div className="login-field">
                        <label className="login-label" htmlFor="fullname">Full Name</label>
                        <div className="login-input-wrapper">
                            <svg className="login-input-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                                <circle cx="12" cy="7" r="4" />
                            </svg>
                            <input
                                id="fullname"
                                value={fullName}
                                onChange={(e) => setFullName(e.target.value)}
                                placeholder="Enter your full name"
                                autoFocus
                                required
                                className="login-input"
                            />
                        </div>
                    </div>

                    <div className="login-field">
                        <label className="login-label" htmlFor="email">Email</label>
                        <div className="login-input-wrapper">
                            <svg className="login-input-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                <rect x="2" y="4" width="20" height="16" rx="2" />
                                <path d="M22 7l-10 7L2 7" />
                            </svg>
                            <input
                                id="email"
                                type="email"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                placeholder="you@company.com"
                                required
                                autoComplete="email"
                                className="login-input"
                            />
                        </div>
                    </div>

                    <div className="login-field">
                        <label className="login-label" htmlFor="password">Password</label>
                        <div className="login-input-wrapper">
                            <svg className="login-input-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                                <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                            </svg>
                            <input
                                id="password"
                                type="password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                placeholder="Min. 8 characters"
                                required
                                autoComplete="new-password"
                                className="login-input"
                            />
                        </div>
                    </div>

                    <div className="login-field">
                        <label className="login-label" htmlFor="confirm-password">Confirm Password</label>
                        <div className="login-input-wrapper">
                            <svg className="login-input-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                            </svg>
                            <input
                                id="confirm-password"
                                type="password"
                                value={confirmPassword}
                                onChange={(e) => setConfirmPassword(e.target.value)}
                                placeholder="Repeat your password"
                                required
                                autoComplete="new-password"
                                className="login-input"
                            />
                        </div>
                    </div>

                    {error && (
                        <div className="login-error">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                <circle cx="12" cy="12" r="10" /><line x1="15" y1="9" x2="9" y2="15" /><line x1="9" y1="9" x2="15" y2="15" />
                            </svg>
                            {error}
                        </div>
                    )}

                    <button type="submit" className="login-submit" disabled={loading || success}>
                        {success ? (
                            <><span className="login-check-icon">{'\u2713'}</span> Account Created</>
                        ) : loading ? (
                            <><span className="spinner" /> Creating Account...</>
                        ) : (
                            'Sign Up'
                        )}
                    </button>
                </form>

                {/* Divider */}
                <div className="login-divider">
                    <span>or sign up with</span>
                </div>

                {/* Social Signup */}
                <div className="login-social-grid">
                    <button
                        type="button"
                        className="login-social-btn"
                        onClick={() => { window.location.href = `${AUTH_BASE}/auth/google`; }}
                    >
                        <svg width="18" height="18" viewBox="0 0 24 24">
                            <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"/>
                            <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                            <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                            <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                        </svg>
                        Google
                    </button>
                    <button
                        type="button"
                        className="login-social-btn"
                        onClick={() => { window.location.href = `${AUTH_BASE}/auth/github`; }}
                    >
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="white">
                            <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
                        </svg>
                        GitHub
                    </button>
                </div>

                {/* Switch to Login */}
                <div className="login-switch">
                    Already have an account?{' '}
                    <a href="/login" className="login-switch-link">Sign In</a>
                </div>

                {/* Footer */}
                <div className="login-footer">
                    <div className="login-footer-line">
                        <span className="login-footer-dot" /> CEM {'\u2192'} AI Agent {'\u2192'} CVM Intelligence
                    </div>
                    <div className="login-footer-version">v2.0 | Cloud-Native Autonomous Operations</div>
                </div>
            </div>
        </div>
    );
}

export default function SignupPage() {
    return (
        <Suspense fallback={
            <div className="login-page-root">
                <div className="login-container">
                    <div style={{ textAlign: 'center', padding: 40, color: 'var(--text-muted)' }}>
                        <div className="spinner" style={{ width: 24, height: 24, margin: '0 auto 16px' }} />
                        Loading...
                    </div>
                </div>
            </div>
        }>
            <SignupContent />
        </Suspense>
    );
}
