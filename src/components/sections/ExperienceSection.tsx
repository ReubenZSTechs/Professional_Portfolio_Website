import { getExperience } from "@/lib/content";
import { Container, Field, Reveal, Section, SectionHeading, Tag } from "@/components/ui";
import type { SectionProps } from "./registry";

export function ExperienceSection({ section, anchor }: SectionProps) {
  const items = getExperience();
  if (items.length === 0) return null;
  return (
    <Section id={anchor} aria-labelledby={`${anchor}-title`}>
      <Container className="flex flex-col gap-8">
        <SectionHeading id={`${anchor}-title`} eyebrow={section.eyebrow} title={section.title} description={section.description} />
        <ol className="m-0 list-none border-b border-line p-0">
          {items.map((job, i) => (
            <Reveal
              as="li"
              delay={i * 80}
              key={`${job.company}-${job.role}`}
              className="flex flex-wrap gap-6 border-t border-line py-7"
            >
              <div className="flex min-w-0 flex-[1_1_240px] flex-col gap-1">
                <h3 className="m-0 text-xl font-semibold">
                  {job.url ? (
                    <a href={job.url} target="_blank" rel="noreferrer" className="text-ink no-underline hover:underline">
                      {job.company}
                    </a>
                  ) : (
                    job.company
                  )}
                </h3>
                <span className="font-medium text-ink">
                  {job.role}
                  {job.type && <> · {job.type}</>}
                </span>
                <span className="text-sm text-muted">
                  <Field value={job.start} /> – <Field value={job.end} />
                  {job.location && <> · {job.location}</>}
                </span>
              </div>
              <div className="flex min-w-0 flex-[999_1_520px] flex-col gap-3.5">
                <ul className="m-0 flex flex-col gap-1.5 pl-5 text-body">
                  {job.bullets.map((b) => (
                    <li key={b}>{b}</li>
                  ))}
                </ul>
                {job.tags.length > 0 && (
                  <div className="flex flex-wrap gap-1.5">
                    {job.tags.map((t) => (
                      <Tag key={t}>{t}</Tag>
                    ))}
                  </div>
                )}
              </div>
            </Reveal>
          ))}
        </ol>
      </Container>
    </Section>
  );
}
