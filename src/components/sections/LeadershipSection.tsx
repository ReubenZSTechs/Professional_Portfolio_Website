import { getLeadership } from "@/lib/content";
import { Container, Field, Reveal, Section, SectionHeading } from "@/components/ui";
import type { SectionProps } from "./registry";

export function LeadershipSection({ section, anchor }: SectionProps) {
  const items = getLeadership();
  if (items.length === 0) return null;
  return (
    <Section id={anchor} tone="muted" aria-labelledby={`${anchor}-title`}>
      <Container className="flex flex-col gap-7">
        <SectionHeading id={`${anchor}-title`} eyebrow={section.eyebrow} title={section.title} description={section.description} />
        <div className="grid gap-6 md:grid-cols-2">
          {items.map((item, i) => (
            <Reveal
              as="article"
              key={item.title}
              delay={(i % 2) * 100}
              className="flex flex-col gap-2 rounded-2xl border border-line bg-bg p-6"
            >
              <h3 className="m-0 text-lg font-semibold">{item.title}</h3>
              <p className="m-0 text-sm text-muted">
                {item.organisation} · <Field value={item.period} />
              </p>
              <p className="m-0 text-body">{item.description}</p>
            </Reveal>
          ))}
        </div>
      </Container>
    </Section>
  );
}
