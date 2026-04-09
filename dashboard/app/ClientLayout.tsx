"use client";
import { usePathname } from 'next/navigation';
import { useEffect } from 'react';
import TopNav from '../components/TopNav';
import ThemeProvider from '../components/ThemeProvider';
import CommandPalette from '../components/CommandPalette';
import AICopilotIcon from '../components/AICopilotIcon';

const AUTH_PAGES = ['/login', '/signup', '/auth/callback'];
const AUTO_REFRESH_INTERVAL = 120000; // 120 seconds

export default function ClientLayout({ children }: { children: React.ReactNode }) {
    const pathname = usePathname();
    const isAuthPage = AUTH_PAGES.some((p) => pathname.startsWith(p));

    // Auto-refresh every 120 seconds to fetch latest data
    useEffect(() => {
        if (isAuthPage) return;

        const interval = setInterval(() => {
            // Trigger a refresh by calling the current pathname
            window.location.reload();
        }, AUTO_REFRESH_INTERVAL);

        return () => clearInterval(interval);
    }, [pathname, isAuthPage]);

    if (isAuthPage) {
        return (
            <ThemeProvider>
                <div className="login-layout-minimal">{children}</div>
            </ThemeProvider>
        );
    }

    return (
        <ThemeProvider>
            <div className="layout-horizontal">
                <TopNav />
                <div className="main-wrapper-horizontal">
                    <main className="main-horizontal">{children}</main>
                </div>
                <CommandPalette />
                <AICopilotIcon />
            </div>
        </ThemeProvider>
    );
}
