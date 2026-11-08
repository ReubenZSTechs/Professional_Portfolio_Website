import { ChatPanel } from "@/components/chat/ChatPanel";
import { getSuggestedQuestions } from "@/lib/content";
import { Container, Reveal, Section, SectionHeading } from "@/components/ui";
import type { SectionProps } from "./registry";

export function AskSection({ section, anchor }: SectionProps) {
  return (
    <Section id={anchor} tone="muted" className="backdrop-mesh" aria-labelledby={`${anchor}-title`}>
      <Container className="flex flex-col gap-7">
        <SectionHeading id={`${anchor}-title`} eyebrow={section.eyebrow} title={section.title} description={section.description} />
        <Reveal>
          <ChatPanel suggestions={getSuggestedQuestions()} />
        </Reveal>
      </Container>
    </Section>
  );
}
