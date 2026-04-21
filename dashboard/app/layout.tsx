import './globals.css';
import ClientLayout from './ClientLayout';

export const metadata = {
    title: 'Huawei Cloud Intelligence | ADN Operations',
    description: 'AI-Powered Telecom CEM-CVM Intelligence Platform — Huawei Cloud Stack',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
    return (
        <html lang="en">
            <head>
                <link rel="preconnect" href="https://fonts.googleapis.com" />
                <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
                <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet" />
            </head>
            <body>
                <script
                    dangerouslySetInnerHTML={{
                        __html: `(function(){try{var t=localStorage.getItem('tci-theme');if(t==='light'||t==='dark'){document.documentElement.setAttribute('data-theme',t)}else if(window.matchMedia('(prefers-color-scheme:light)').matches){document.documentElement.setAttribute('data-theme','light')}}catch(e){}})()`,
                    }}
                />
                <ClientLayout>{children}</ClientLayout>
            </body>
        </html>
    );
}
