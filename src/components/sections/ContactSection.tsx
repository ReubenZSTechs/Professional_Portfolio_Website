import { ContactForm } from "@/components/contact/ContactForm";
import { getSite } from "@/lib/content";
import { Container, Reveal, Section } from "@/components/ui";
import type { SectionProps } from "./registry";

export function ContactSection({ section, anchor }: SectionProps) {
  const site = getSite();
  const { email, linkedin, github, whatsapp } = site.links;
  const linkClass = "font-semibold text-inverse-ink underline-offset-4 hover:text-inverse-ink hover:underline";

  return (
    <Section id={anchor} tone="inverse" aria-labelledby={`${anchor}-title`}>
      <Container className="flex flex-wrap gap-12">
        <Reveal className="flex min-w-0 flex-[1_1_400px] flex-col gap-4">
          <h2 id={`${anchor}-title`} className="m-0 font-display text-4xl leading-tight font-bold sm:text-[40px]">
            {section.title ?? "Get in touch"}
          </h2>
          {section.description && <p className="m-0 text-inverse-muted">{section.description}</p>}
          <a href={`mailto:${email}`} className={`${linkClass} text-lg`}>
            {email}
          </a>
          <ul className="m-0 flex list-none flex-wrap gap-x-6 gap-y-2 p-0">
            <li>
              <a href={linkedin} target="_blank" rel="noreferrer" className={linkClass}>
                LinkedIn
              </a>
            </li>
            <li>
              <a href={github} target="_blank" rel="noreferrer" className={linkClass}>
                GitHub
              </a>
            </li>
            {whatsapp && (
              <li>
                <a href={`https://wa.me/${whatsapp}`} target="_blank" rel="noreferrer" className={linkClass}>
                  WhatsApp
                </a>
              </li>
            )}
            <li>
              <a href={site.cv.href} download={site.cv.fileName} className={linkClass}>
                {site.cv.label}
              </a>
            </li>
          </ul>
        </Reveal>
        <Reveal delay={120} className="flex min-w-0 flex-[1_1_400px]">
          <ContactForm />
        </Reveal>
      </Container>
    </Section>
  );
}
