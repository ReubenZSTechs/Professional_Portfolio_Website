import path from "node:path";
import type { NextConfig } from "next";

/**
 * The Python FastAPI backend lives at /api/py/*.
 * - On Vercel, api/index.py is deployed as a Python function and /api/py/* is rewritten to it.
 * - Locally, `npm run dev:api` runs uvicorn on :8000 and this rewrite proxies to it.
 */
const isDev = process.env.NODE_ENV === "development";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  turbopack: { root: path.resolve(".") },
  images: { formats: ["image/avif", "image/webp"] },
  async rewrites() {
    return [
      {
        source: "/api/py/:path*",
        // Dev: uvicorn on :8000. Production: the Vercel Python function built from api/index.py,
        // which still sees the original /api/py/... path and routes it inside FastAPI.
        destination: isDev ? "http://127.0.0.1:8000/api/py/:path*" : "/api/index",
      },
    ];
  },
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
        ],
      },
    ];
  },
};

export default nextConfig;
