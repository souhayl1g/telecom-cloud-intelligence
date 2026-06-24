import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';
import { canAccess, defaultLanding, type Role } from './lib/roles';

const PUBLIC_PATHS = [
    '/login', '/signup', '/forgot-password', '/reset-password',
    '/auth/callback',
    '/api/login', '/api/logout', '/api/signup', '/api/forgot-password', '/api/reset-password',
    '/_next', '/favicon.ico',
];

// Read the role from a JWT payload WITHOUT verifying the signature. This is a UX
// guard only — the real security boundary is the api-gateway `require_role` check.
// Edge runtime provides atob(); we just base64url-decode the middle segment.
function roleFromToken(token: string | undefined): Role | undefined {
    if (!token) return undefined;
    try {
        const part = token.split('.')[1];
        if (!part) return undefined;
        const json = atob(part.replace(/-/g, '+').replace(/_/g, '/'));
        const role = JSON.parse(json)?.role;
        return ['engineer', 'data_scientist', 'admin'].includes(role) ? (role as Role) : undefined;
    } catch {
        return undefined;
    }
}

export function middleware(req: NextRequest) {
    const { pathname } = req.nextUrl;
    const isPublic = PUBLIC_PATHS.some((p) => pathname.startsWith(p));
    if (isPublic) return NextResponse.next();

    const token = req.cookies.get('auth_token')?.value;
    if (!token) {
        const loginUrl = new URL('/login', req.url);
        loginUrl.searchParams.set('redirect', pathname);
        return NextResponse.redirect(loginUrl);
    }

    // API routes proxy their own auth; only gate page navigations here.
    if (pathname.startsWith('/api')) return NextResponse.next();

    const role = roleFromToken(token);

    // Root → each persona's home.
    if (pathname === '/') {
        return NextResponse.redirect(new URL(defaultLanding(role), req.url));
    }
    if (!canAccess(pathname, role)) {
        // Send the user to their own home rather than a dead-end 403 page.
        return NextResponse.redirect(new URL(defaultLanding(role), req.url));
    }
    return NextResponse.next();
}

export const config = {
    matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
};
