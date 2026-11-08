import path from "node:path";
import type { NextConfig } from "next";

/**
 * The Python FastAPI backend lives at /api/py/*.
 * - On Vercel, api/index.py is deployed as a Python function and /api/py/* is rewritten to it.
 * - Locally, `npm run dev:api` runs uvicorn on :8000 and this rewrite proxies to it.
 */
const isDev = process.env.NODE_ENV === "development";

/**
 * Content-Security-Policy. See docs/security.md for the reasoning.
 * - 'unsafe-inline' scripts are allowed because the pages are statically generated (a nonce
 *   would force per-request rendering). The site renders no user-supplied HTML: React escapes
 *   everything and the chat renderer only emits text and /projects links.
 * - challenges.cloudflare.com is Cloudflare Turnstile (the invisible bot check).
 * - Dev needs 'unsafe-eval' (React Refresh) and a websocket for hot reload.
 */
const csp = [
  "default-src 'self'",
  `script-src 'self' 'unsafe-inline' https://challenges.cloudflare.com${isDev ? " 'unsafe-eval'" : ""}`,
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data: blob:",
  "font-src 'self'",
  `connect-src 'self' https://challenges.cloudflare.com${isDev ? " ws: http://127.0.0.1:8000" : ""}`,
  "frame-src https://challenges.cloudflare.com",
  "worker-src 'self' blob:",
  "manifest-src 'self'",
  "object-src 'none'",
  "base-uri 'none'",
  "form-action 'self'",
  "frame-ancestors 'none'",
  ...(isDev ? [] : ["upgrade-insecure-requests"]),
].join("; ");

const securityHeaders = [
  { key: "Content-Security-Policy", value: csp },
  { key: "Strict-Transport-Security", value: "max-age=63072000; includeSubDomains; preload" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "Cross-Origin-Opener-Policy", value: "same-origin" },
  { key: "Cross-Origin-Resource-Policy", value: "same-origin" },
  { key: "X-DNS-Prefetch-Control", value: "on" },
  {
    key: "Permissions-Policy",
    value:
      "camera=(), microphone=(), geolocation=(), payment=(), usb=(), bluetooth=(), " +
      "magnetometer=(), gyroscope=(), accelerometer=(), interest-cohort=(), browsing-topics=()",
  },
];

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
    return [{ source: "/(.*)", headers: securityHeaders }];
  },
};

export default nextConfig;
