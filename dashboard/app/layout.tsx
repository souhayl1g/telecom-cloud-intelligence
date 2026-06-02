import './globals.css';
import ClientLayout from './ClientLayout';

export const metadata = {
    title: 'NeXo | Advanced Operations',
    description: 'AI-Powered Telecom CEM-CVM Intelligence Platform — Huawei Cloud Stack',
};

const themeBootstrap = `(function(){try{var t=localStorage.getItem('tci-theme');if(t==='light'||t==='dark'){document.documentElement.setAttribute('data-theme',t)}else if(window.matchMedia('(prefers-color-scheme:light)').matches){document.documentElement.setAttribute('data-theme','light')}}catch(e){}})()`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
    return (
        <html lang="en" suppressHydrationWarning>
            <head>
                <link rel="preconnect" href="https://fonts.googleapis.com" />
                <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
                <link href="https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600;700&family=Fira+Sans:wght@300;400;500;600;700&family=Geist:wght@400;500;600;700;800&family=Space+Grotesk:wght@400;500;600;700&display=swap" rel="stylesheet" />
                <link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200" rel="stylesheet" />
                <link rel="icon" href="/favicon.ico" sizes="any" />
                <link rel="icon" href="/images/logo.svg" type="image/svg+xml" />
                <script dangerouslySetInnerHTML={{ __html: themeBootstrap }} />
            </head>
            <body suppressHydrationWarning>
                <ClientLayout>{children}</ClientLayout>
            </body>
        </html>
    );
}
