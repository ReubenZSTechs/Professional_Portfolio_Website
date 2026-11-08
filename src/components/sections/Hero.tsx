import Image from "next/image";
import { getSite } from "@/lib/content";
import { ButtonLink, Container, Eyebrow } from "@/components/ui";
import type { SectionProps } from "./registry";

export function Hero({ anchor }: SectionProps) {
  const site = getSite();
  return (
    <section id={anchor} className="backdrop-mesh -mt-[68px] pt-[116px] pb-16 sm:pt-[148px] sm:pb-24">
      <Container className="flex flex-wrap items-center gap-12 lg:gap-16">
        <div className="flex min-w-0 flex-[1_1_520px] animate-fade-up flex-col gap-6">
          <Eyebrow>
            {site.role} · {site.location}
          </Eyebrow>
          <h1 className="m-0 font-display text-[40px] leading-[1.08] font-bold tracking-[-0.02em] sm:text-[56px]">
            {site.headline}
          </h1>
          <p className="m-0 max-w-[560px] text-lg text-muted sm:text-[19px]">{site.intro}</p>

          {site.availability.open && (
            <div className="glass flex flex-wrap items-center gap-x-3 gap-y-1 rounded-xl px-4 py-3 text-sm text-body shadow-[0_8px_30px_rgb(11_18_32/0.05)]">
              <span className="inline-flex items-center gap-2 font-semibold text-ink">
                <span className="relative flex size-2.5" aria-hidden>
                  <span className="absolute inline-flex size-full animate-ping rounded-full bg-emerald-500 opacity-60 motion-reduce:animate-none" />
                  <span className="relative inline-flex size-2.5 rounded-full bg-emerald-500" />
                </span>
                {site.availability.label}
              </span>
              {site.availability.details.map((d) => (
                <span key={d} className="before:mr-3 before:text-line-strong before:content-['·']">
                  {d}
                </span>
              ))}
            </div>
          )}

          <div className="flex flex-wrap gap-3">
            <ButtonLink href="#ask">Ask about my work</ButtonLink>
            <ButtonLink href={site.links.github} variant="secondary">
              GitHub
            </ButtonLink>
            <ButtonLink href={site.links.linkedin} variant="secondary">
              LinkedIn
            </ButtonLink>
          </div>

          {site.highlights.length > 0 && (
            <ul
              aria-label="Highlights"
              className="glass m-0 mt-2 grid list-none grid-cols-2 gap-x-6 gap-y-4 rounded-2xl px-5 py-4 text-[14px] leading-snug text-muted sm:grid-cols-[repeat(auto-fit,minmax(110px,1fr))]"
            >
              {site.highlights.map((h) => (
                <li key={h.label}>
                  <strong className="block font-display text-[24px] leading-tight text-ink">{h.value}</strong>
                  {h.label}
                </li>
              ))}
            </ul>
          )}
        </div>

        <figure className="m-0 min-w-0 flex-[0_1_400px]">
          <Image
            src={site.portrait.src}
            alt={site.portrait.alt}
            width={960}
            height={1200}
            priority
            sizes="(min-width: 1024px) 400px, 90vw"
            className="block aspect-[4/5] h-auto w-full rounded-[20px] object-cover"
          />
        </figure>
      </Container>
    </section>
  );
}
