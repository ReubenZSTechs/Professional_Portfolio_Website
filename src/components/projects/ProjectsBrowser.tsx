"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import clsx from "clsx";
import type { ProjectFrontmatter } from "@/lib/schemas";
import { StatusBadge, Tag } from "@/components/ui";

const filters = [
  { id: "all", label: "All" },
  { id: "agentic", label: "Agentic AI" },
  { id: "llm", label: "LLM apps" },
  { id: "research", label: "Research" },
  { id: "cv", label: "Computer vision" },
  { id: "ml", label: "Machine learning" },
] as const;
type FilterId = (typeof filters)[number]["id"];

export function ProjectsBrowser({ projects }: { projects: ProjectFrontmatter[] }) {
  const [filter, setFilter] = useState<FilterId>("all");
  const available = useMemo(
    () => filters.filter((f) => f.id === "all" || projects.some((p) => p.category === f.id)),
    [projects],
  );
  const shown = filter === "all" ? projects : projects.filter((p) => p.category === filter);

  return (
    <div className="flex flex-col gap-6">
      <div role="group" aria-label="Filter by category" className="flex flex-wrap gap-2">
        {available.map((f) => (
          <button
            key={f.id}
            type="button"
            aria-pressed={filter === f.id}
            onClick={() => setFilter(f.id)}
            className={clsx(
              "min-h-11 rounded-full border px-4 text-sm transition",
              filter === f.id ? "border-ink bg-ink text-bg" : "border-line-strong bg-bg text-ink hover:border-ink",
            )}
          >
            {f.label}
          </button>
        ))}
      </div>

      <ul className="m-0 grid list-none gap-4 p-0 md:grid-cols-2" aria-live="polite">
        {shown.map((p) => (
          <li key={p.slug}>
            <Link
              href={`/projects/${p.slug}`}
              className="group flex h-full flex-col gap-3 rounded-2xl border border-line bg-bg p-6 text-ink no-underline transition hover:border-line-strong hover:shadow-card hover:text-ink"
            >
              <div className="flex flex-wrap items-center gap-2">
                <StatusBadge status={p.status} />
                {p.featured && <span className="text-xs font-semibold text-accent">★ Featured</span>}
              </div>
              <h2 className="m-0 font-display text-xl font-bold group-hover:text-accent">{p.title}</h2>
              <p className="m-0 text-[15px] text-body">{p.summary}</p>
              <div className="mt-auto flex flex-wrap gap-1.5 pt-1">
                {p.tags.slice(0, 4).map((t) => (
                  <Tag key={t}>{t}</Tag>
                ))}
              </div>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
