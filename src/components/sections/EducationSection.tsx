import { getCertifications, getEducation, getLanguages } from "@/lib/content";
import { Container, Field, Reveal, Section, SectionHeading, Tag } from "@/components/ui";
import type { SectionProps } from "./registry";

export function EducationSection({ section, anchor }: SectionProps) {
  const education = getEducation();
  const certifications = getCertifications();
  const languages = getLanguages();
  if (education.length + certifications.length + languages.length === 0) return null;

  return (
    <Section id={anchor} tone="muted" aria-labelledby={`${anchor}-title`}>
      <Container className="flex flex-col gap-8">
        <SectionHeading id={`${anchor}-title`} eyebrow={section.eyebrow} title={section.title} description={section.description} />

        <div className="grid gap-6 lg:grid-cols-[3fr_2fr]">
          <div className="flex flex-col gap-6">
            {education.map((e) => (
              <Reveal as="article" key={e.institution} className="flex flex-col gap-3 rounded-2xl border border-line bg-bg p-6">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <h3 className="m-0 text-xl font-semibold">{e.institution}</h3>
                    <p className="m-0 font-medium">
                      <Field value={e.degree} />
                    </p>
                  </div>
                  {e.gpa && (
                    <div className="text-right">
                      <div className="font-display text-2xl font-bold text-accent">{e.gpa}</div>
                      <div className="text-xs text-muted uppercase tracking-wide">GPA</div>
                    </div>
                  )}
                </div>
                <p className="m-0 text-sm text-muted">
                  <Field value={e.start} /> – <Field value={e.end} />
                  {e.location && <> · {e.location}</>}
                </p>
                {e.thesis && (
                  <p className="m-0 text-body">
                    <span className="font-medium text-ink">Thesis:</span> {e.thesis}
                  </p>
                )}
                {e.honors.length > 0 && (
                  <div className="flex flex-wrap gap-1.5">
                    {e.honors.map((h) => (
                      <Tag key={h}>{h}</Tag>
                    ))}
                  </div>
                )}
                {e.coursework.length > 0 && (
                  <p className="m-0 text-sm text-muted">
                    <span className="font-medium text-body">Relevant coursework:</span> {e.coursework.join(", ")}
                  </p>
                )}
              </Reveal>
            ))}
          </div>

          <Reveal delay={120} className="flex flex-col gap-6">
            {certifications.length > 0 && (
              <div className="rounded-2xl border border-line bg-bg p-6">
                <h3 className="m-0 mb-3 text-base font-semibold text-muted">Certifications</h3>
                <ul className="m-0 list-none p-0">
                  {certifications.map((c) => (
                    <li key={c.name} className="flex justify-between gap-3 border-b border-line py-2.5 last:border-b-0">
                      <span>
                        {c.url ? (
                          <a href={c.url} target="_blank" rel="noreferrer" className="font-medium">
                            {c.name}
                          </a>
                        ) : (
                          <span className="font-medium">{c.name}</span>
                        )}
                        <span className="block text-sm text-muted">{c.issuer}</span>
                      </span>
                      <span className="text-sm text-muted">{c.year}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {languages.length > 0 && (
              <div className="rounded-2xl border border-line bg-bg p-6">
                <h3 className="m-0 mb-3 text-base font-semibold text-muted">Languages</h3>
                <ul className="m-0 list-none p-0">
                  {languages.map((l) => (
                    <li key={l.name} className="flex justify-between gap-3 border-b border-line py-2.5 last:border-b-0">
                      <span className="font-medium">{l.name}</span>
                      <span className="text-right text-sm text-muted">
                        <Field value={l.level} />
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </Reveal>
        </div>
      </Container>
    </Section>
  );
}
