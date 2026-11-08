import type { Site } from "@/lib/schemas";
import { Container } from "@/components/ui";

export function SiteFooter({ site }: { site: Site }) {
  const year = new Date().getFullYear();
  return (
    <footer className="border-t border-line py-7">
      <Container className="flex flex-wrap items-center justify-between gap-3 text-sm text-muted">
        <span>
          © {year} {site.name}
        </span>
        <nav aria-label="Social" className="flex gap-5">
          <a href={site.links.github} target="_blank" rel="noreferrer" className="text-muted hover:text-ink">
            GitHub
          </a>
          <a href={site.links.linkedin} target="_blank" rel="noreferrer" className="text-muted hover:text-ink">
            LinkedIn
          </a>
          <a href={`mailto:${site.links.email}`} className="text-muted hover:text-ink">
            Email
          </a>
        </nav>
        <span>{site.footer.note}</span>
      </Container>
    </footer>
  );
}
