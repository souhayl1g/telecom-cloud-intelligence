"use client";
import { useEffect, useState, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';

function CallbackContent() {
    const router = useRouter();
    const search = useSearchParams();
    const [status, setStatus] = useState<'processing' | 'success' | 'error'>('processing');
    const [errorMsg, setErrorMsg] = useState('');

    useEffect(() => {
        const token = search.get('token');
        const expiresIn = search.get('expires_in');

        if (!token) {
            setStatus('error');
            setErrorMsg('No authentication token received');
            return;
        }

        // Store the token via our API route (sets httpOnly cookie)
        fetch('/api/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: 'oauth_callback', token, expires_in: expiresIn }),
        })
            .then((res) => {
                if (res.ok) {
                    setStatus('success');
                    setTimeout(() => {
                        router.push('/overview');
                        router.refresh();
                    }, 800);
                } else {
                    setStatus('error');
                    setErrorMsg('Failed to save authentication');
                }
            })
            .catch(() => {
                setStatus('error');
                setErrorMsg('Connection failed');
            });
    }, [search, router]);

    return (
        <div className="login-page-root">
            <div className="login-bg-orb login-bg-orb-1" />
            <div className="login-bg-orb login-bg-orb-2" />
            <div className="login-bg-orb login-bg-orb-3" />
            <div className="login-bg-grid" />

            <div className="login-container" style={{ textAlign: 'center' }}>
                <div className="login-brand">
                    <div className="login-brand-icon">
                        <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
                            <rect width="48" height="48" rx="14" fill="url(#brand-gradient-cb)" />
                            <path d="M16 24L22 30L32 18" stroke="white" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
                            <defs>
                                <linearGradient id="brand-gradient-cb" x1="0" y1="0" x2="48" y2="48">
                                    <stop stopColor="#a78bfa" />
                                    <stop offset="0.5" stopColor="#6366f1" />
                                    <stop offset="1" stopColor="#4f46e5" />
                                </linearGradient>
                            </defs>
                        </svg>
                    </div>
                </div>

                {status === 'processing' && (
                    <div style={{ padding: '32px 0' }}>
                        <div className="spinner" style={{ width: 32, height: 32, margin: '0 auto 16px' }} />
                        <p style={{ color: 'var(--text-secondary)', fontSize: 14 }}>
                            Completing sign in...
                        </p>
                    </div>
                )}

                {status === 'success' && (
                    <div style={{ padding: '32px 0' }}>
                        <div style={{ fontSize: 48, marginBottom: 16 }}>{'\u2713'}</div>
                        <p style={{ color: 'var(--color-success)', fontSize: 16, fontWeight: 600 }}>
                            Authentication successful!
                        </p>
                        <p style={{ color: 'var(--text-muted)', fontSize: 13, marginTop: 8 }}>
                            Redirecting to dashboard...
                        </p>
                    </div>
                )}

                {status === 'error' && (
                    <div style={{ padding: '32px 0' }}>
                        <div className="login-error" style={{ justifyContent: 'center', marginBottom: 16 }}>
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                <circle cx="12" cy="12" r="10" /><line x1="15" y1="9" x2="9" y2="15" /><line x1="9" y1="9" x2="15" y2="15" />
                            </svg>
                            {errorMsg}
                        </div>
                        <a href="/login" style={{ color: 'var(--brand-primary)', fontSize: 13 }}>
                            Back to login
                        </a>
                    </div>
                )}
            </div>
        </div>
    );
}

export default function AuthCallbackPage() {
    return (
        <Suspense fallback={
            <div className="login-page-root">
                <div className="login-container" style={{ textAlign: 'center', padding: 40 }}>
                    <div className="spinner" style={{ width: 24, height: 24, margin: '0 auto 16px' }} />
                    <p style={{ color: 'var(--text-muted)' }}>Loading...</p>
                </div>
            </div>
        }>
            <CallbackContent />
        </Suspense>
    );
}
