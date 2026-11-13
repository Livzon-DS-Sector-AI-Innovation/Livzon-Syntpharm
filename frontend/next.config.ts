import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  typescript: { ignoreBuildErrors: false },
  distDir: process.env.NEXT_DIST_DIR ?? '.next',
  output: 'standalone',
  reactCompiler: true,
  allowedDevOrigins: process.env.ALLOWED_DEV_ORIGINS
    ? process.env.ALLOWED_DEV_ORIGINS.split(',').filter(Boolean)
    : ['localhost', '127.0.0.1'],
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

  async redirects() {
    // 旧偏差入口（偏差流程 / 偏差自动化 / 偏差报告）已下线，统一回到偏差管理看盘，避免死链
    return [
      { source: '/quality/deviation-flow/:path*', destination: '/quality/deviation', permanent: true },
      { source: '/quality/deviation-flow', destination: '/quality/deviation', permanent: true },
      { source: '/quality/deviation-automation/:path*', destination: '/quality/deviation', permanent: true },
      { source: '/quality/deviation-automation', destination: '/quality/deviation', permanent: true },
      { source: '/quality/deviation/report/:path*', destination: '/quality/deviation', permanent: true },
      { source: '/quality/deviation/report', destination: '/quality/deviation', permanent: true },
    ];
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
