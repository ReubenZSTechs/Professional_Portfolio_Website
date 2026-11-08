import type { Metadata, Viewport } from "next";
import { Inter, Space_Grotesk } from "next/font/google";
import type { CSSProperties, ReactNode } from "react";
import { SiteFooter } from "@/components/layout/SiteFooter";
import { SiteHeader } from "@/components/layout/SiteHeader";
import { getSite } from "@/lib/content";
import { absoluteUrl, siteUrl } from "@/lib/site";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter", display: "swap" });
const grotesk = Space_Grotesk({
  subsets: ["latin"],
  weight: ["500", "600", "700"],
  variable: "--font-grotesk",
  display: "swap",
});

export function generateMetadata(): Metadata {
  const site = getSite();
  return {
    metadataBase: new URL(siteUrl),
    title: { default: site.seo.title, template: `%s · ${site.shortName}` },
    description: site.seo.description,
    keywords: site.seo.keywords,
    authors: [{ name: site.name, url: siteUrl }],
    creator: site.name,
    alternates: { canonical: "/" },
    openGraph: {
      type: "website",
      locale: "en_US",
      url: siteUrl,
      siteName: site.name,
      title: site.seo.title,
      description: site.seo.description,
    },
    twitter: { card: "summary_large_image", title: site.seo.title, description: site.seo.description },
    robots: { index: true, follow: true },
  };
}

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#ffffff" },
    { media: "(prefers-color-scheme: dark)", color: "#0b1220" },
  ],
};

/** Sets data-theme before first paint, so there is no flash of the wrong theme. */
const themeScript = `(function(){document.documentElement.classList.add('js');try{var t=localStorage.getItem('theme');if(t!=='light'&&t!=='dark'){t=matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light'}document.documentElement.dataset.theme=t}catch(e){document.documentElement.dataset.theme='light'}})()`;

export default function RootLayout({ children }: { children: ReactNode }) {
  const site = getSite();
  const personJsonLd = {
    "@context": "https://schema.org",
    "@type": "Person",
    name: site.name,
    jobTitle: site.role,
    url: siteUrl,
    image: absoluteUrl(site.portrait.src),
    email: `mailto:${site.links.email}`,
    address: { "@type": "PostalAddress", addressLocality: "Jakarta", addressCountry: "ID" },
    sameAs: [site.links.github, site.links.linkedin],
    knowsAbout: site.seo.keywords,
  };

  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${inter.variable} ${grotesk.variable}`}
      style={{ "--accent-base": site.accent } as CSSProperties}
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(personJsonLd) }}
        />
      </head>
      <body>
        <a
          href="#main"
          className="sr-only z-50 rounded-lg bg-ink px-4 py-2 text-bg focus:not-sr-only focus:fixed focus:top-3 focus:left-3"
        >
          Skip to content
        </a>
        <SiteHeader
          name={site.shortName}
          nav={site.nav}
          cv={site.cv}
        />
        <main id="main">{children}</main>
        <SiteFooter site={site} />
      </body>
    </html>
  );
}
