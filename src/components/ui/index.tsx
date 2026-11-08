/**
 * Small, unopinionated building blocks shared by every section.
 * Keep visual decisions here so sections stay about content.
 */
import Link from "next/link";
import clsx from "clsx";
import type { ComponentProps, ReactNode } from "react";
import type { ProjectStatus } from "@/lib/schemas";
import { isTodo, showTodos } from "@/lib/todo";
import { Reveal } from "./Reveal";

export { Reveal };

export function Container({ className, ...props }: ComponentProps<"div">) {
  return <div className={clsx("mx-auto w-full max-w-[1120px] px-4 sm:px-6", className)} {...props} />;
}

export function Section({
  tone = "default",
  className,
  ...props
}: ComponentProps<"section"> & { tone?: "default" | "muted" | "inverse" }) {
  return (
    <section
      className={clsx(
        "py-16 sm:py-22",
        tone === "muted" && "bg-surface",
        tone === "inverse" && "bg-inverse-bg text-inverse-ink",
        className,
      )}
      {...props}
    />
  );
}

export function Eyebrow({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <p className={clsx("m-0 text-sm font-semibold uppercase tracking-[0.08em] text-accent", className)}>
      {children}
    </p>
  );
}

export function SectionHeading({
  eyebrow,
  title,
  description,
  id,
  action,
}: {
  eyebrow?: string;
  title?: string;
  description?: string;
  id?: string;
  action?: ReactNode;
}) {
  if (!eyebrow && !title && !description) return null;
  return (
    <Reveal className="flex flex-wrap items-end justify-between gap-4">
      <div className="flex max-w-[640px] flex-col gap-2">
        {eyebrow && <Eyebrow>{eyebrow}</Eyebrow>}
        {title && (
          <h2 id={id} className="m-0 font-display text-3xl leading-tight font-bold sm:text-[38px]">
            {title}
          </h2>
        )}
        {description && <p className="m-0 text-muted">{description}</p>}
      </div>
      {action}
    </Reveal>
  );
}

export function Tag({ children }: { children: ReactNode }) {
  return <span className="rounded-md bg-chip px-2.5 py-1 text-[13px] text-body">{children}</span>;
}

export function Chip({ children }: { children: ReactNode }) {
  return (
    <span className="rounded-lg border border-line-strong bg-bg px-3 py-1.5 text-sm text-ink">{children}</span>
  );
}

const statusStyles: Record<ProjectStatus, { label: string; className: string }> = {
  live: { label: "Live", className: "bg-success-bg text-success-ink" },
  testing: { label: "In testing", className: "bg-warning-bg text-warning-ink" },
  "in-progress": { label: "In progress", className: "bg-warning-bg text-warning-ink" },
  completed: { label: "Completed", className: "bg-success-bg text-success-ink" },
  archived: { label: "Archived", className: "bg-chip text-body" },
};

export function StatusBadge({ status }: { status: ProjectStatus }) {
  const s = statusStyles[status];
  return <Pill className={s.className}>{s.label}</Pill>;
}

export function Pill({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <span className={clsx("rounded-full px-2.5 py-0.5 text-xs font-semibold", className ?? "bg-chip text-body")}>
      {children}
    </span>
  );
}

type ButtonVariant = "primary" | "secondary" | "dark" | "ghost";
const buttonStyles: Record<ButtonVariant, string> = {
  primary: "bg-accent text-white hover:bg-accent-strong hover:text-white",
  secondary: "border border-line-strong text-ink hover:border-ink hover:text-ink",
  dark: "bg-ink text-bg hover:opacity-90 hover:text-bg",
  ghost: "text-ink hover:text-accent",
};

export function ButtonLink({
  href,
  variant = "primary",
  className,
  children,
  external,
  ...rest
}: {
  href: string;
  variant?: ButtonVariant;
  className?: string;
  children: ReactNode;
  external?: boolean;
} & Omit<ComponentProps<"a">, "href">) {
  const classes = clsx(
    "inline-flex min-h-12 items-center gap-2 rounded-[10px] px-5 font-semibold no-underline transition",
    buttonStyles[variant],
    className,
  );
  const isExternal = external ?? /^(https?:|mailto:)/.test(href);
  if (isExternal) {
    return (
      <a href={href} className={classes} target={href.startsWith("http") ? "_blank" : undefined} rel="noreferrer" {...rest}>
        {children}
      </a>
    );
  }
  return (
    <Link href={href} className={classes} {...rest}>
      {children}
    </Link>
  );
}

/**
 * Renders a content value. Values starting with "TODO" are placeholders:
 * highlighted in development, hidden in production.
 */
export function Field({ value, className }: { value?: string; className?: string }) {
  if (!value) return null;
  if (isTodo(value)) {
    if (!showTodos) return null;
    return (
      <mark className={clsx("rounded bg-warning-bg px-1 text-warning-ink", className)} title="Fill this in under /content">
        {value}
      </mark>
    );
  }
  return <span className={className}>{value}</span>;
}

export function ArrowIcon({ direction = "right", size = 18 }: { direction?: "right" | "left"; size?: number }) {
  return (
    <svg aria-hidden width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      {direction === "right" ? (
        <>
          <path d="M5 12h14" />
          <path d="M13 6l6 6-6 6" />
        </>
      ) : (
        <>
          <path d="M19 12H5" />
          <path d="M11 6l-6 6 6 6" />
        </>
      )}
    </svg>
  );
}
