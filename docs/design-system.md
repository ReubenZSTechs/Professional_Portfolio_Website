# Design system

The site follows the Claude-designed mockup, with changes for hiring managers in Indonesia and internationally: an Education & credentials section (university, GPA, graduation date up front), Languages and Certifications, a Leadership & teaching section, an availability banner in the hero, WhatsApp as an optional contact, plus dark mode, accessibility and SEO polish.

## Tokens
All colours are CSS variables in `src/app/globals.css`, exposed to Tailwind as utilities (`bg-surface`, `text-muted`, `border-line`, …). Change a colour there and it updates everywhere, in both themes.

| Token | Light | Use |
|---|---|---|
| `--ink` | `#0B1220` | headings, primary text |
| `--body` | `#334155` | paragraph text |
| `--muted` | `#4A5568` | secondary text, captions |
| `--line` / `--line-strong` | `#E4E7EC` / `#CBD2DC` | borders, dividers |
| `--surface` | `#F6F7F9` | alternating section background |
| `--chip` | `#EEF2F7` | tags |
| `--accent` | from `site.yaml` (`#1F5EDC`) | links, primary buttons, eyebrows, metrics |
| `--inverse-*` | navy | contact section |
| `--success-*` / `--warning-*` | green / amber | status badges, TODO highlights |

Dark mode redefines the same variables under `[data-theme="dark"]`. The theme follows the visitor's OS setting until they press the toggle, which is remembered in `localStorage`. An inline script in `layout.tsx` sets the theme before first paint, so there's no flash.

**Changing the brand colour**: set `accent` in `content/site.yaml`. Hover and soft variants are derived with `color-mix`, and dark mode lightens it automatically.

## Typography
- **Space Grotesk** (`font-display`): headings, metrics, logo. Weights 500–700.
- **Inter** (`font-sans`): everything else.
Both are self-hosted by `next/font` (no request to Google at runtime, no layout shift).

Scale: h1 56px (40px mobile) · h2 38px · h3 20–24px · body 16px (17–18px in case studies) · eyebrow 14px uppercase, 0.08em tracking.

## Layout
- Content width 1120px (`Container`), case-study text 880px.
- Sections alternate white / `surface` backgrounds, with 88px vertical rhythm (64px mobile).
- Fluid grids: `repeat(auto-fit, minmax(…))`, so layouts reflow without breakpoint-specific code. 16px side gutters on phones; no horizontal scrolling.

## Components (`src/components/ui/index.tsx`)
| Component | Purpose |
|---|---|
| `Container`, `Section` | width + padding; `tone="default" \| "muted" \| "inverse"` |
| `SectionHeading`, `Eyebrow` | eyebrow + h2 + description (+ optional action link) |
| `ButtonLink` | `primary`, `secondary`, `dark`, `ghost`; opens external links in a new tab |
| `Tag`, `Chip`, `Pill`, `StatusBadge` | small labels |
| `Field` | renders a content value, hiding `TODO…` placeholders in production |

Case-study blocks live in `src/components/mdx/` (`Pipeline`, `Decision(s)`, `Metric(s)`, `Callout`, `Todo`).

## Adding a homepage section
1. Create `src/components/sections/MySection.tsx` taking `{ section, anchor }: SectionProps`.
2. Add its id to `sectionIds` in `src/lib/schemas.ts`.
3. Register it in `src/components/sections/registry.tsx`.
4. Add `- id: my-section` to `content/home.yaml`.

## Accessibility & quality baseline
- Colour contrast meets WCAG AA in both themes; visible `:focus-visible` rings; a "Skip to content" link.
- Touch targets ≥ 44px; the mobile menu is a real `<button>` with `aria-expanded`.
- The chat log is an `aria-live` region; the sources panel is a labelled `<aside>`.
- Motion respects `prefers-reduced-motion`.
- SEO: per-page metadata, canonical URLs, `sitemap.xml`, `robots.txt`, a generated Open Graph image, JSON-LD `Person` (site) and `CreativeWork` (projects).
