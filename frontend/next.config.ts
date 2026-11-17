import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  typescript: { ignoreBuildErrors: false },
  distDir: process.env.NEXT_DIST_DIR ?? '.next',
  output: 'standalone',
  reactCompiler: true,
  // API 路径带尾斜杠时不再 308 去斜杠，避免与 FastAPI 斜杠重定向形成循环
  skipTrailingSlashRedirect: true,
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
