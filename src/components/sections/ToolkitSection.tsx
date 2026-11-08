import { getSkills } from "@/lib/content";
import { Chip, Container, Reveal, Section, SectionHeading } from "@/components/ui";
import type { SectionProps } from "./registry";

export function ToolkitSection({ section, anchor }: SectionProps) {
  const groups = getSkills();
  if (groups.length === 0) return null;
  return (
    <Section id={anchor} aria-labelledby={`${anchor}-title`}>
      <Container className="flex flex-col gap-7">
        <SectionHeading id={`${anchor}-title`} eyebrow={section.eyebrow} title={section.title} description={section.description} />
        <div className="grid grid-cols-[repeat(auto-fit,minmax(240px,1fr))] gap-6">
          {groups.map((g, i) => (
            <Reveal key={g.group} delay={i * 80} className="flex flex-col gap-3">
              <h3 className="m-0 text-base font-semibold text-muted">{g.group}</h3>
              <ul className="m-0 flex list-none flex-wrap gap-2 p-0">
                {g.items.map((s) => (
                  <li key={s}>
                    <Chip>{s}</Chip>
                  </li>
                ))}
              </ul>
            </Reveal>
          ))}
        </div>
      </Container>
    </Section>
  );
}
