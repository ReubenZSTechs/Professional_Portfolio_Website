/**
 * Components available inside project MDX files (content/projects/*.mdx).
 * Usage examples: content/projects/_template.mdx and docs/content-guide.md.
 */
import Image from "next/image";
import Link from "next/link";
import { Fragment, type ComponentProps, type ReactNode } from "react";
import clsx from "clsx";
import { showTodos } from "@/lib/todo";
import { Reveal } from "@/components/ui/Reveal";

/** A left-to-right flow of steps. `highlight` (1-based) outlines the key step. */
export function Pipeline({ steps, highlight }: { steps: string[]; highlight?: number }) {
  return (
    <Reveal as="figure" className="not-prose my-8 rounded-2xl bg-surface p-5 sm:p-8">
      <ol aria-label="Pipeline" className="m-0 flex list-none flex-wrap items-center justify-center gap-3 p-0">
        {steps.map((step, i) => {
          const isLast = i === steps.length - 1;
          const isKey = highlight === i + 1;
          return (
            <Fragment key={step}>
              <li
                className={clsx(
                  "rounded-xl px-4 py-3 text-[15px] font-semibold",
                  isLast ? "bg-ink text-bg" : "border bg-bg text-ink",
                  !isLast && (isKey ? "border-2 border-accent" : "border-line-strong"),
                )}
              >
                {step}
              </li>
              {!isLast && (
                <li aria-hidden className="text-muted">
                  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M5 12h14" />
                    <path d="M13 6l6 6-6 6" />
                  </svg>
                </li>
              )}
            </Fragment>
          );
        })}
      </ol>
    </Reveal>
  );
}

export function Decisions({ children }: { children: ReactNode }) {
  return (
    <Reveal className="not-prose my-6 grid grid-cols-[repeat(auto-fit,minmax(240px,1fr))] gap-4">
      {children}
    </Reveal>
  );
}

export function Decision({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-2 rounded-2xl border border-line p-5">
      <h3 className="m-0 text-lg font-semibold text-ink">{title}</h3>
      <div className="text-[15px] leading-relaxed text-muted [&_code]:text-[13px]">{children}</div>
    </div>
  );
}

export function Metrics({ children }: { children: ReactNode }) {
  return (
    <Reveal className="not-prose my-6 grid grid-cols-[repeat(auto-fit,minmax(200px,1fr))] gap-4">
      {children}
    </Reveal>
  );
}

export function Metric({ value, label }: { value: string; label: string }) {
  return (
    <div className="rounded-2xl bg-surface p-6">
      <div className="font-display text-4xl font-bold text-accent">{value}</div>
      <div className="text-[15px] text-body">{label}</div>
    </div>
  );
}

export function Callout({ children }: { children: ReactNode }) {
  return (
    <aside className="not-prose my-6 rounded-xl border-l-4 border-accent bg-accent-soft px-5 py-4 text-[15px] text-body">
      {children}
    </aside>
  );
}

/** A reminder to fill something in. Visible in development only. */
export function Todo({ children }: { children: ReactNode }) {
  if (!showTodos) return null;
  return (
    <span className="not-prose my-2 inline-block rounded-md border border-dashed border-warning-ink/40 bg-warning-bg px-2 py-1 text-sm text-warning-ink">
      <strong>TODO:</strong> {children}
    </span>
  );
}

/** A screenshot or diagram with a caption. Put files in public/images/projects/. */
export function Figure({
  src,
  alt,
  caption,
  width,
  height,
}: {
  src: string;
  alt: string;
  caption?: string;
  width: number;
  height: number;
}) {
  return (
    <Reveal as="figure" className="not-prose my-8">
      <Image
        src={src}
        alt={alt}
        width={width}
        height={height}
        sizes="(min-width: 900px) 832px, 100vw"
        className="mx-auto h-auto max-h-[680px] w-auto max-w-full rounded-2xl border border-line bg-surface"
      />
      {caption && <figcaption className="mt-3 text-center text-sm text-muted">{caption}</figcaption>}
    </Reveal>
  );
}

function MdxLink({ href = "", ...props }: ComponentProps<"a">) {
  if (href.startsWith("/")) return <Link href={href} {...props} />;
  return <a href={href} target={href.startsWith("http") ? "_blank" : undefined} rel="noreferrer" {...props} />;
}

export const mdxComponents = {
  Pipeline,
  Decisions,
  Decision,
  Metrics,
  Metric,
  Callout,
  Figure,
  Todo,
  a: MdxLink,
};
