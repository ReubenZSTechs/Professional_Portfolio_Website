"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import clsx from "clsx";
import { ThemeToggle } from "./ThemeToggle";

type NavItem = { label: string; href: string };

/** Tracks which homepage section is on screen so its nav link can be highlighted. */
function useActiveSection(hrefs: string[], enabled: boolean) {
  const [active, setActive] = useState<string | null>(null);
  useEffect(() => {
    if (!enabled) return;
    const ids = hrefs.map((h) => h.split("#")[1]).filter((id): id is string => Boolean(id));
    const elements = ids.map((id) => document.getElementById(id)).filter((el): el is HTMLElement => el !== null);
    if (elements.length === 0) return;
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries.filter((e) => e.isIntersecting).sort((a, b) => b.intersectionRatio - a.intersectionRatio);
        if (visible[0]) setActive(visible[0].target.id);
      },
      { rootMargin: "-30% 0px -60% 0px", threshold: [0, 0.25, 0.5] },
    );
    elements.forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, [hrefs, enabled]);
  return active;
}

export function SiteHeader({
  name,
  nav,
  cv,
}: {
  name: string;
  nav: NavItem[];
  cv: { href: string; label: string; fileName: string };
}) {
  const pathname = usePathname();
  // The menu remembers the page it was opened on, so navigating closes it.
  const [openOn, setOpenOn] = useState<string | null>(null);
  const open = openOn === pathname;
  const setOpen = (value: boolean | ((o: boolean) => boolean)) =>
    setOpenOn((value instanceof Function ? value(open) : value) ? pathname : null);
  const [scrolled, setScrolled] = useState(false);
  const active = useActiveSection(
    nav.map((n) => n.href),
    pathname === "/",
  );

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header
      className={clsx(
        "sticky top-0 z-40 border-b transition-[background-color,border-color,backdrop-filter] duration-300",
        scrolled ? "glass-strong" : "border-transparent bg-transparent",
      )}
    >
      <div className="mx-auto flex max-w-[1120px] items-center justify-between gap-4 px-4 py-3 sm:px-6">
        <Link href="/" className="font-display text-xl font-bold text-ink no-underline hover:text-ink">
          {name}
        </Link>

        <nav aria-label="Main" className="hidden items-center gap-7 text-[15px] md:flex">
          {nav.map((item) => {
            const isActive = active !== null && item.href.endsWith(`#${active}`);
            return (
              <a
                key={item.href}
                href={item.href}
                aria-current={isActive ? "true" : undefined}
                className={clsx(
                  "no-underline transition-colors",
                  isActive ? "font-medium text-ink" : "text-muted hover:text-ink",
                )}
              >
                {item.label}
              </a>
            );
          })}
          <ThemeToggle />
          <a
            href={cv.href}
            className="inline-flex min-h-11 items-center rounded-[10px] bg-ink px-4 font-semibold text-bg no-underline hover:opacity-90 hover:text-bg"
            download={cv.fileName}
          >
            {cv.label}
          </a>
        </nav>

        <div className="flex items-center gap-2 md:hidden">
          <ThemeToggle />
          <button
            type="button"
            className="inline-flex size-11 items-center justify-center rounded-lg border border-line text-ink"
            aria-expanded={open}
            aria-controls="mobile-nav"
            aria-label={open ? "Close menu" : "Open menu"}
            onClick={() => setOpen((o) => !o)}
          >
            <svg aria-hidden width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              {open ? <path d="M6 6l12 12M18 6L6 18" /> : <path d="M4 7h16M4 12h16M4 17h16" />}
            </svg>
          </button>
        </div>
      </div>

      {open && (
        <nav id="mobile-nav" aria-label="Mobile" className="border-t border-line bg-bg md:hidden">
          <ul className="mx-auto flex max-w-[1120px] flex-col px-4 py-2">
            {nav.map((item) => (
              <li key={item.href}>
                <a href={item.href} onClick={() => setOpen(false)} className="block py-3 text-ink no-underline">
                  {item.label}
                </a>
              </li>
            ))}
            <li className="py-3">
              <a href={cv.href} download={cv.fileName} className="inline-flex min-h-11 items-center rounded-[10px] bg-ink px-4 font-semibold text-bg no-underline">
                {cv.label}
              </a>
            </li>
          </ul>
        </nav>
      )}
    </header>
  );
}
