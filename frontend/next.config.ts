import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  turbopack: {
    root: '.',
  },
  output: 'standalone',
  reactCompiler: false,
  allowedDevOrigins: ['172.28.215.130', 'localhost', '127.0.0.1'],
  productionBrowserSourceMaps: true,
  logging: {
    fetches: {
      fullUrl: true,
    },
  },

  experimental: {
    serverActions: {
      bodySizeLimit: '50mb',
    },
    proxyClientMaxBodySize: '50mb',
  },

  async headers() {
    return [
      {
        // Prevent caching of HTML pages to avoid ChunkLoadError
        // Apply to all routes except static assets
        source: '/((?!_next/static|_next/image|favicon.ico).*)',
        headers: [
          {
            key: 'Cache-Control',
            value: 'no-store, must-revalidate, private',
          },
        ],
      },
    ];
  },
};

export default nextConfig;
