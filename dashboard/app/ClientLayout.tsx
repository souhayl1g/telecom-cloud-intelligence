"use client";
import { usePathname } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import Sidebar from '../components/Sidebar';
import TopHeader from '../components/TopHeader';
import StatusStrip from '../components/StatusStrip';
import ThemeProvider from '../components/ThemeProvider';
import CommandPalette from '../components/CommandPalette';
import { RefreshProvider } from '../components/RefreshContext';
import { RoleProvider } from '../components/RoleContext';

const AUTH_PAGES = ['/login', '/signup', '/auth/callback', '/forgot-password', '/reset-password'];

const pageVariants = {
    hidden: { opacity: 0, y: 8, scale: 0.997 },
    enter: {
        opacity: 1, y: 0, scale: 1,
        transition: { duration: 0.26, ease: [0.22, 1, 0.36, 1] as const },
    },
    exit: {
        opacity: 0, y: -6, scale: 0.999,
        transition: { duration: 0.14, ease: [0.4, 0, 1, 1] as const },
    },
};

export default function ClientLayout({ children }: { children: React.ReactNode }) {
    const pathname = usePathname();
    const isAuthPage = AUTH_PAGES.some((p) => pathname.startsWith(p));

    if (isAuthPage) {
        return (
            <ThemeProvider>
                <div className="login-layout-minimal">{children}</div>
            </ThemeProvider>
        );
    }

    return (
        <ThemeProvider>
            <RoleProvider>
            <RefreshProvider intervalMs={30000}>
                <div className="layout-app">
                    <Sidebar />
                    <div className="layout-main">
                        <TopHeader />
                        <StatusStrip />
                        <div className="layout-content-wrapper">
                            <AnimatePresence mode="wait">
                                <motion.main
                                    key={pathname}
                                    className="layout-content"
                                    variants={pageVariants}
                                    initial="hidden"
                                    animate="enter"
                                    exit="exit"
                                >
                                    {children}
                                </motion.main>
                            </AnimatePresence>
                        </div>
                    </div>
                    <CommandPalette />
                </div>
            </RefreshProvider>
            </RoleProvider>
        </ThemeProvider>
    );
}
