import Link from "next/link";
import { ProjectCard } from "@/components/projects/ProjectCard";
import { getFeaturedProjects, getLabProjects, getProjects, getSite } from "@/lib/content";
import { ArrowIcon, Container, Reveal, Section, SectionHeading, StatusBadge } from "@/components/ui";
import type { SectionProps } from "./registry";

export function ProjectsSection({ section, anchor }: SectionProps) {
  const featured = getFeaturedProjects();
  const lab = getLabProjects();
  const total = getProjects().length;
  const site = getSite();

  return (
    <Section id={anchor} tone="muted" aria-labelledby={`${anchor}-title`}>
      <Container className="flex flex-col gap-8">
        <SectionHeading
          id={`${anchor}-title`}
          eyebrow={section.eyebrow}
          title={section.title}
          description={section.description}
          action={
            <Link href="/projects" className="inline-flex items-center gap-2 font-semibold">
              All {total} projects <ArrowIcon />
            </Link>
          }
        />

        <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,440px),1fr))] gap-6">
          {featured.map((p, i) => (
            <Reveal key={p.slug} delay={(i % 2) * 100} className="flex">
              <ProjectCard project={p} priority={i < 2} />
            </Reveal>
          ))}
        </div>

        {lab.length > 0 && (
          <Reveal className="flex flex-col gap-4 rounded-2xl border border-line bg-bg p-6">
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <h3 className="m-0 text-lg font-semibold">In the lab</h3>
              <a href={site.links.github} target="_blank" rel="noreferrer" className="text-sm font-semibold">
                Follow along on GitHub
              </a>
            </div>
            <ul className="m-0 grid list-none gap-4 p-0 sm:grid-cols-2">
              {lab.map((p) => (
                <li key={p.slug}>
                  <Link
                    href={`/projects/${p.slug}`}
                    className="group flex h-full flex-col gap-2 rounded-xl border border-line p-4 text-ink no-underline transition hover:border-line-strong hover:text-ink"
                  >
                    <span className="flex items-center justify-between gap-3">
                      <strong className="group-hover:text-accent">{p.title}</strong>
                      <StatusBadge status={p.status} />
                    </span>
                    <span className="text-[15px] text-muted">{p.summary}</span>
                    <span className="mt-auto pt-1 text-xs font-medium text-muted">{p.timeline}</span>
                  </Link>
                </li>
              ))}
            </ul>
          </Reveal>
        )}
      </Container>
    </Section>
  );
}
