/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: "standalone",

  // Proxies browser requests for /api/* to the backend container over the
  // internal Docker network. This means the browser only ever talks to
  // whatever origin served the page (localhost:3000, or a tunnel/domain
  // pointed at it) — the backend on :8000 never needs to be exposed
  // separately, and CORS becomes a non-issue since there's no cross-origin
  // request from the browser's point of view.
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.BACKEND_INTERNAL_URL || "http://backend:8000"}/api/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;