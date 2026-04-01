import { NextResponse } from 'next/server';

const AUTH_SERVICE = process.env.AUTH_SERVICE_URL || 'http://localhost:8002';

export async function POST(req: Request) {
    const body = await req.json();
    const { action } = body;

    // OAuth callback — frontend sends us the token from the redirect
    if (action === 'oauth_callback') {
        const { token, expires_in } = body;
        if (!token) {
            return NextResponse.json({ error: 'No token provided' }, { status: 400 });
        }
        const res = NextResponse.json({ ok: true });
        res.cookies.set('auth_token', token, {
            httpOnly: true,
            secure: process.env.NODE_ENV === 'production',
            sameSite: 'lax',
            path: '/',
            maxAge: parseInt(expires_in) || 60 * 60 * 24,
        });
        return res;
    }

    // Signup — call auth service
    if (action === 'signup') {
        const { email, password, full_name } = body;
        try {
            const authRes = await fetch(`${AUTH_SERVICE}/auth/signup`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password, full_name }),
            });
            const data = await authRes.json();
            if (!authRes.ok) {
                return NextResponse.json(
                    { error: data.detail || 'Signup failed' },
                    { status: authRes.status }
                );
            }
            const res = NextResponse.json({ ok: true, user: data.user });
            res.cookies.set('auth_token', data.access_token, {
                httpOnly: true,
                secure: process.env.NODE_ENV === 'production',
                sameSite: 'lax',
                path: '/',
                maxAge: data.expires_in || 60 * 60 * 24,
            });
            return res;
        } catch {
            return NextResponse.json({ error: 'Auth service unavailable' }, { status: 503 });
        }
    }

    // Login — call auth service
    const { email, password } = body;

    // Support legacy user/pass fields for backward compatibility
    const loginEmail = email || body.user;
    const loginPassword = password || body.pass;

    try {
        const authRes = await fetch(`${AUTH_SERVICE}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: loginEmail, password: loginPassword }),
        });
        const data = await authRes.json();
        if (!authRes.ok) {
            return NextResponse.json(
                { error: data.detail || 'Invalid credentials' },
                { status: authRes.status }
            );
        }
        const res = NextResponse.json({ ok: true, user: data.user });
        res.cookies.set('auth_token', data.access_token, {
            httpOnly: true,
            secure: process.env.NODE_ENV === 'production',
            sameSite: 'lax',
            path: '/',
            maxAge: data.expires_in || 60 * 60 * 24,
        });
        return res;
    } catch {
        return NextResponse.json({ error: 'Auth service unavailable' }, { status: 503 });
    }
}
