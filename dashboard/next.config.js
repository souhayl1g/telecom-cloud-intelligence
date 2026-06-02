/** @type {import('next').NextConfig} */
const nextConfig = {
    reactStrictMode: true,
    async headers() {
        return [
            {
                source: '/:path*',
                headers: [
                    {
                        key: 'Content-Security-Policy',
                        value: [
                            "default-src 'self'",
                            "script-src 'self' 'unsafe-inline' 'unsafe-eval' 'wasm-unsafe-eval' 'inline-speculation-rules' chrome-extension:",
                            // Google Fonts stylesheets + gstatic font files required for
                            // Material Symbols icons and Fira Code / Space Grotesk fonts.
                            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
                            "font-src 'self' https://fonts.gstatic.com",
                            "img-src 'self' data: blob:",
                            // Allow Ollama (L4 agent chat) and all backend services on localhost.
                            "connect-src 'self' http://localhost:8000 http://localhost:8001 http://localhost:8002 http://localhost:8003",
                            "frame-ancestors 'none'",
                            "base-uri 'self'",
                            "form-action 'self'",
                        ].join('; ')
                    }
                ]
            }
        ];
    }
};

module.exports = nextConfig;
