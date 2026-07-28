import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  distDir: process.env.NEXT_DIST_DIR ?? '.next',
  turbopack: {
    root: '.',
  },
  output: 'standalone',
  reactCompiler: false,
  allowedDevOrigins: process.env.ALLOWED_DEV_ORIGINS?.split(',').filter(Boolean) || ['localhost', '127.0.0.1'],
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
