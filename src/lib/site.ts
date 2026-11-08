/** Absolute site URL, used for metadata, sitemap and structured data. */
export const siteUrl = (
  process.env.NEXT_PUBLIC_SITE_URL ??
  (process.env.VERCEL_PROJECT_PRODUCTION_URL ? `https://${process.env.VERCEL_PROJECT_PRODUCTION_URL}` : undefined) ??
  "http://localhost:3000"
).replace(/\/$/, "");

export const absoluteUrl = (path = "/") => `${siteUrl}${path.startsWith("/") ? path : `/${path}`}`;
