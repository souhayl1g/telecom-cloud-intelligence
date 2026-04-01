"use client";
import { usePathname } from 'next/navigation';
import TopNav from '../components/TopNav';

const AUTH_PAGES = ['/login', '/signup', '/auth/callback'];

export default function ClientLayout({ children }: { children: React.ReactNode }) {
    const pathname = usePathname();
    const isAuthPage = AUTH_PAGES.some((p) => pathname.startsWith(p));

    if (isAuthPage) {
        return <div className="login-layout-minimal">{children}</div>;
    }

    return (
        <div className="layout-horizontal">
            <TopNav />
            <div className="main-wrapper-horizontal">
                <main className="main-horizontal">{children}</main>
            </div>
        </div>
    );
}
