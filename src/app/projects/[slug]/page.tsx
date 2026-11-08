import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import { notFound } from "next/navigation";
import { compileMDX } from "next-mdx-remote/rsc";
import remarkGfm from "remark-gfm";
import { mdxComponents } from "@/components/mdx";
import { categoryLabels } from "@/components/projects/ProjectCard";
import { ArrowIcon, ButtonLink, Container, Field, Pill, StatusBadge } from "@/components/ui";
import { getNextProject, getProject, getProjects, getSite } from "@/lib/content";
import { absoluteUrl } from "@/lib/site";

type Params = { slug: string };

export const dynamicParams = false;

export function generateStaticParams(): Params[] {
  return getProjects().map((p) => ({ slug: p.slug }));
}

export async function generateMetadata({ params }: { params: Promise<Params> }): Promise<Metadata> {
  const { slug } = await params;
  const project = getProject(slug);
  if (!project) return {};
  return {
    title: project.title,
    description: project.summary,
    alternates: { canonical: `/projects/${slug}` },
    openGraph: { type: "article", title: project.title, description: project.summary, url: `/projects/${slug}` },
  };
}

export default async function ProjectPage({ params }: { params: Promise<Params> }) {
  const { slug } = await params;
  const project = getProject(slug);
  if (!project) notFound();
  const next = getNextProject(slug);
  const site = getSite();

  const { content } = await compileMDX({
    source: project.body,
    components: mdxComponents,
    options: {
      mdxOptions: { remarkPlugins: [remarkGfm] },
      // Project MDX is our own trusted content, and components need JS props like steps={[...]}.
      // Dangerous expressions (eval, Function, process…) stay blocked.
      blockJS: false,
      blockDangerousJS: true,
    },
  });

  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "CreativeWork",
    name: project.title,
    description: project.summary,
    url: absoluteUrl(`/projects/${slug}`),
    codeRepository: project.repo,
    keywords: project.tags.join(", "),
    author: { "@type": "Person", name: site.name, url: absoluteUrl("/") },
  };

  const meta = [
    { label: "Timeline", value: project.timeline },
    { label: "Role", value: project.role },
    { label: "Stack", value: project.stack.slice(0, 4).join(", ") },
  ];

  return (
    <article>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />

      <header className="pt-10 pb-10 sm:pt-16">
        <div className="mx-auto flex max-w-[880px] flex-col gap-5 px-4 sm:px-6">
          <Link href="/projects" className="inline-flex min-h-11 w-fit items-center gap-2 font-medium text-muted no-underline hover:text-ink">
            <ArrowIcon direction="left" /> All projects
          </Link>
          <div className="flex flex-wrap gap-2">
            <StatusBadge status={project.status} />
            <Pill>{categoryLabels[project.category]}</Pill>
          </div>
          <h1 className="m-0 font-display text-4xl leading-[1.1] font-bold tracking-[-0.02em] sm:text-[52px]">
            {project.title}
          </h1>
          <p className="m-0 text-lg text-muted sm:text-xl">{project.summary}</p>
          <dl className="m-0 grid grid-cols-[repeat(auto-fit,minmax(180px,1fr))] gap-5 border-y border-line py-6">
            {meta.map((m) => (
              <div key={m.label} className="flex flex-col gap-0.5">
                <dt className="text-[13px] text-muted">{m.label}</dt>
                <dd className="m-0 font-semibold">
                  <Field value={m.value} />
                </dd>
              </div>
            ))}
            <div className="flex flex-col gap-0.5">
              <dt className="text-[13px] text-muted">Links</dt>
              <dd className="m-0 flex gap-4 font-semibold">
                <a href={project.repo} target="_blank" rel="noreferrer">
                  Repository
                </a>
                {project.demo && (
                  <a href={project.demo} target="_blank" rel="noreferrer">
                    Live demo
                  </a>
                )}
              </dd>
            </div>
          </dl>
        </div>
      </header>

      {project.cover && (
        <div className="mx-auto max-w-[880px] px-4 pb-6 sm:px-6">
          <Image
            src={project.cover}
            alt={`${project.title} preview`}
            width={704}
            height={352}
            priority
            sizes="(min-width: 880px) 832px, 100vw"
            className="aspect-[2/1] h-auto w-full rounded-[20px] border border-line object-cover"
          />
        </div>
      )}

      <div className="mx-auto max-w-[880px] px-4 pb-16 sm:px-6">
        <div className="prose prose-lg max-w-none prose-headings:font-display prose-headings:text-ink prose-h2:mt-14 prose-h2:text-[30px] prose-p:text-body prose-li:text-body prose-strong:text-ink prose-a:text-accent prose-code:text-ink prose-code:before:content-none prose-code:after:content-none prose-th:text-ink prose-td:text-body">
          {content}
        </div>
      </div>

      <Container className="border-t border-line py-12">
        <div className="mx-auto flex max-w-[832px] flex-wrap items-center justify-between gap-4">
          <Link href="/#work" className="inline-flex min-h-11 items-center font-semibold text-ink">
            Back to selected work
          </Link>
          {next && (
            <ButtonLink href={`/projects/${next.slug}`}>
              Next: {next.title} <ArrowIcon />
            </ButtonLink>
          )}
        </div>
      </Container>
    </article>
  );
}
