import { ImageResponse } from "next/og";
import { getSite } from "@/lib/content";

export const alt = "Reuben Zachary Susanto, AI Engineer";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

/** Social preview card for links shared on LinkedIn, WhatsApp, Slack, etc. */
export default function OpengraphImage() {
  const site = getSite();
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          padding: 72,
          background: "#0B1220",
          color: "#FFFFFF",
          fontFamily: "sans-serif",
        }}
      >
        <div style={{ display: "flex", fontSize: 26, letterSpacing: 3, textTransform: "uppercase", color: site.accent }}>
          {`${site.role} · ${site.location}`}
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
          <div style={{ fontSize: 72, fontWeight: 700, lineHeight: 1.05 }}>{site.name}</div>
          <div style={{ fontSize: 34, color: "#CBD2DC", maxWidth: 950 }}>{site.headline}</div>
        </div>
        <div style={{ display: "flex", gap: 16 }}>
          {site.highlights.slice(0, 3).map((h) => (
            <div key={h.label} style={{ display: "flex", padding: "10px 18px", borderRadius: 12, background: "#111A2E", fontSize: 24 }}>
              <span style={{ fontWeight: 700, marginRight: 8 }}>{h.value}</span>
              <span>{h.label}</span>
            </div>
          ))}
        </div>
      </div>
    ),
    size,
  );
}
