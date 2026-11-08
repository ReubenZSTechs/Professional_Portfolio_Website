import Link from "next/link";
import { getAwards, getResearch } from "@/lib/content";
import { ArrowIcon, Chip, Container, Eyebrow, Reveal, Section } from "@/components/ui";
import type { SectionProps } from "./registry";

export function ResearchSection({ anchor }: SectionProps) {
  const research = getResearch();
  const awards = getAwards();
  return (
    <Section id={anchor} aria-labelledby={`${anchor}-title`}>
      <Container className="flex flex-wrap gap-14">
        <Reveal className="flex min-w-0 flex-[3_1_520px] flex-col gap-4">
          <Eyebrow>{research.eyebrow}</Eyebrow>
          <h2 id={`${anchor}-title`} className="m-0 font-display text-4xl leading-[1.1] font-bold sm:text-[44px]">
            {research.title}
          </h2>
          <p className="m-0 text-lg leading-normal text-body sm:text-[19px]">{research.subtitle}</p>
          <p className="m-0 text-muted">{research.description}</p>
          {research.tags.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {research.tags.map((t) => (
                <Chip key={t}>{t}</Chip>
              ))}
            </div>
          )}
          {research.project && (
            <Link href={`/projects/${research.project}`} className="inline-flex items-center gap-2 font-semibold">
              Read the thesis write-up <ArrowIcon />
            </Link>
          )}
        </Reveal>

        {awards.length > 0 && (
          <Reveal delay={120} className="flex min-w-0 flex-[2_1_300px] flex-col gap-4 pt-1.5">
            <Eyebrow>Awards</Eyebrow>
            <ul className="m-0 list-none p-0">
              {awards.map((a) => (
                <li
                  key={`${a.title}-${a.year}`}
                  className="flex justify-between gap-3 border-b border-line py-3.5 last:border-b-0"
                >
                  <span>
                    <strong>{a.title}</strong>
                    {a.issuer && <span className="block text-sm text-muted">{a.issuer}</span>}
                  </span>
                  <span className="text-muted">{a.year}</span>
                </li>
              ))}
            </ul>
          </Reveal>
        )}
      </Container>
    </Section>
  );
}
