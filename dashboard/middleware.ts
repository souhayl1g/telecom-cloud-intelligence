import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

const PUBLIC_PATHS = [
    '/login', '/signup', '/forgot-password', '/reset-password',
    '/auth/callback',
    '/api/login', '/api/logout', '/api/signup', '/api/forgot-password', '/api/reset-password',
    '/_next', '/favicon.ico',
];

export function middleware(req: NextRequest) {
    const { pathname } = req.nextUrl;
    const isPublic = PUBLIC_PATHS.some((p) => pathname.startsWith(p));
    if (isPublic) return NextResponse.next();

    const token = req.cookies.get('auth_token');
    if (!token) {
        const loginUrl = new URL('/login', req.url);
        loginUrl.searchParams.set('redirect', pathname);
        return NextResponse.redirect(loginUrl);
    }
    return NextResponse.next();
}

export const config = {
    matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
};
