import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  distDir: process.env.NEXT_DIST_DIR ?? '.next',
  output: 'standalone',
  reactCompiler: false,
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
    // 资料文件上传走 proxy.ts 转发，超过此上限会被截断成不完整的 multipart，
    // 导致后端 socket hang up、浏览器 fetch 永不返回（前端表现为一直「上传中」）。
    // 需 ≥ 后端 DOC_GEN_MAX_TOTAL_MB(150MB)，并与 nginx client_max_body_size 保持一致。
    proxyClientMaxBodySize: '200mb',
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
