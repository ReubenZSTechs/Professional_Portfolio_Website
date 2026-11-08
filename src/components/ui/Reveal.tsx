"use client";

/**
 * Fades its children into view whenever they scroll on screen, in both directions:
 * rising up when they enter from below (scrolling down), dropping down when they enter
 * from above (scrolling up). They fade out again once they leave the viewport.
 *
 * - One IntersectionObserver is shared by every <Reveal> on the page.
 * - Content is only hidden once JavaScript runs (the `js` class on <html>, set in layout.tsx),
 *   so pages stay fully readable without JS and to search engines.
 * - `prefers-reduced-motion` turns the effect off entirely (see globals.css).
 */
import { createElement, type CSSProperties, type ReactNode } from "react";
import clsx from "clsx";

let observer: IntersectionObserver | null = null;

function getObserver(): IntersectionObserver {
  observer ??= new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        const el = entry.target as HTMLElement;
        if (entry.isIntersecting) {
          el.dataset.revealed = "true";
        } else {
          // Off screen: hide again and remember which edge it left through, so it
          // slides back in from that side (up from below, down from above).
          delete el.dataset.revealed;
          el.dataset.from = entry.boundingClientRect.top > 0 ? "below" : "above";
        }
      }
    },
    { threshold: 0.12, rootMargin: "0px 0px -8% 0px" },
  );
  return observer;
}

/** Callback ref: start observing on mount; React 19 calls the returned cleanup on unmount. */
function observe(el: HTMLElement | null) {
  if (!el) return;
  const obs = getObserver();
  obs.observe(el);
  return () => obs.unobserve(el);
}

type RevealProps = {
  children: ReactNode;
  /** Milliseconds to wait before animating, for staggering items in a grid. */
  delay?: number;
  as?: "div" | "li" | "article" | "section" | "figure";
  className?: string;
  id?: string;
};

export function Reveal({ children, delay = 0, as = "div", className, id }: RevealProps) {
  return createElement(
    as,
    {
      ref: observe,
      id,
      className: clsx("reveal", className),
      style: delay ? ({ "--reveal-delay": `${delay}ms` } as CSSProperties) : undefined,
    },
    children,
  );
}
