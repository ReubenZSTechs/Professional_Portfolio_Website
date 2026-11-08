import type { Metadata } from "next";
import { ProjectsBrowser } from "@/components/projects/ProjectsBrowser";
import { getProjects, getSite } from "@/lib/content";
import { Container, Eyebrow } from "@/components/ui";

export const metadata: Metadata = {
  title: "Projects",
  description: "Case studies in agentic AI, LLM applications, computer vision and research.",
  alternates: { canonical: "/projects" },
};

export default function ProjectsPage() {
  const projects = getProjects();
  const site = getSite();
  return (
    <section className="py-14 sm:py-20">
      <Container className="flex flex-col gap-8">
        <div className="flex max-w-[680px] flex-col gap-3">
          <Eyebrow>Projects</Eyebrow>
          <h1 className="m-0 font-display text-4xl leading-tight font-bold sm:text-5xl">Everything I&apos;ve built</h1>
          <p className="m-0 text-lg text-muted">
            {projects.length} projects, from production agents to computer-vision models. Each one links to its source on{" "}
            <a href={site.links.github} target="_blank" rel="noreferrer">
              GitHub
            </a>
            .
          </p>
        </div>
        <ProjectsBrowser projects={projects.map(({ body: _body, ...p }) => p)} />
      </Container>
    </section>
  );
}
