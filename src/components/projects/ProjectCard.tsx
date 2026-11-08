import Image from "next/image";
import Link from "next/link";
import type { Project } from "@/lib/content";
import { Field, Pill, StatusBadge, Tag } from "@/components/ui";
import { CoverArt } from "./CoverArt";

const categoryLabels: Record<Project["category"], string> = {
  agentic: "Agentic AI",
  llm: "LLM app",
  cv: "Computer vision",
  ml: "Machine learning",
  research: "Research",
};

export { categoryLabels };

export function ProjectCard({ project, priority = false }: { project: Project; priority?: boolean }) {
  const href = `/projects/${project.slug}`;
  return (
    <article className="group relative flex w-full flex-col overflow-hidden rounded-2xl border border-line bg-bg transition hover:-translate-y-0.5 hover:shadow-card motion-reduce:hover:translate-y-0">
      <div className="aspect-[2/1] overflow-hidden border-b border-line">
        {project.cover ? (
          <Image
            src={project.cover}
            alt=""
            width={704}
            height={352}
            priority={priority}
            sizes="(min-width: 1024px) 540px, 100vw"
            className="h-full w-full object-cover transition duration-500 group-hover:scale-[1.03] motion-reduce:group-hover:scale-100"
          />
        ) : (
          <CoverArt project={project} />
        )}
      </div>
      <div className="flex flex-auto flex-col gap-3 p-6">
        <div className="flex flex-wrap gap-2">
          <StatusBadge status={project.status} />
          <Pill>{categoryLabels[project.category]}</Pill>
        </div>
        <h3 className="m-0 font-display text-2xl font-bold">
          {/* The stretched link makes the whole card clickable while keeping one accessible link */}
          <Link href={href} className="text-ink no-underline after:absolute after:inset-0 hover:text-accent">
            {project.title}
          </Link>
        </h3>
        <p className="m-0 font-semibold text-ink">
          <Field value={project.highlight} />
        </p>
        <p className="m-0 text-body">{project.summary}</p>
        <div className="flex flex-wrap gap-1.5">
          {project.tags.slice(0, 4).map((t) => (
            <Tag key={t}>{t}</Tag>
          ))}
        </div>
        <div className="relative z-10 mt-auto flex flex-wrap gap-5 pt-2">
          <Link href={href} className="inline-flex min-h-11 items-center font-semibold">
            Read case study
          </Link>
          <a href={project.repo} target="_blank" rel="noreferrer" className="inline-flex min-h-11 items-center font-semibold text-ink hover:text-accent">
            Repository
          </a>
        </div>
      </div>
    </article>
  );
}
