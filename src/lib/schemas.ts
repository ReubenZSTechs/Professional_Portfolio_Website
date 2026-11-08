/**
 * Content schemas — the single source of truth for every editable file in /content.
 *
 * Every YAML file and every project's MDX frontmatter is parsed through these
 * schemas at build time. If a field is missing or misspelled, `next build`
 * fails with a message naming the file and field, so a typo never reaches the
 * live site. See docs/content-guide.md for a field-by-field reference.
 */
import { z } from "zod";

const url = z.string().url();
const path = z.string().startsWith("/");
/** Text that YAML might parse as a number (e.g. `2026`). Always stored as a string. */
const text = z.union([z.string(), z.number()]).transform(String);
const href = z.union([url, path, z.string().startsWith("#"), z.string().startsWith("mailto:")]);

/* ------------------------------------------------------------------ site.yaml */

export const siteSchema = z.object({
  name: z.string(),
  shortName: z.string(),
  role: z.string(),
  location: z.string(),
  timezone: z.string(),
  headline: z.string(),
  intro: z.string(),
  accent: z.string().regex(/^#[0-9a-fA-F]{6}$/, "accent must be a hex colour like #1F5EDC"),
  availability: z.object({
    open: z.boolean(),
    label: z.string(),
    details: z.array(z.string()).default([]),
  }),
  links: z.object({
    email: z.string().email(),
    github: url,
    linkedin: url,
    /** Optional. International format without "+" or spaces, e.g. 6281234567890. */
    whatsapp: z.string().regex(/^\d{8,15}$/).optional(),
  }),
  cv: z.object({
    href: href,
    label: z.string().default("Download CV"),
    /** File name the browser saves the PDF as. */
    fileName: z.string().default("CV.pdf"),
  }),
  portrait: z.object({ src: path, alt: z.string() }),
  highlights: z.array(z.object({ value: z.string(), label: z.string() })).max(6),
  nav: z.array(z.object({ label: z.string(), href })),
  footer: z.object({ note: z.string() }),
  seo: z.object({
    title: z.string(),
    description: z.string().max(170),
    keywords: z.array(z.string()).default([]),
  }),
});

/* ------------------------------------------------------------------ home.yaml */

export const sectionIds = [
  "hero",
  "ask",
  "experience",
  "projects",
  "research",
  "education",
  "toolkit",
  "leadership",
  "contact",
] as const;
export type SectionId = (typeof sectionIds)[number];

export const homeSectionSchema = z.object({
  id: z.enum(sectionIds),
  /** Set to false to hide a section without deleting its settings. */
  enabled: z.boolean().default(true),
  /** The anchor used in the URL (#work). Defaults to the id. */
  anchor: z.string().optional(),
  eyebrow: z.string().optional(),
  title: z.string().optional(),
  description: z.string().optional(),
});
export const homeSchema = z.object({ sections: z.array(homeSectionSchema).min(1) });

/* ------------------------------------------------------------ list-style YAML */

export const experienceSchema = z.array(
  z.object({
    company: z.string(),
    url: url.optional(),
    role: z.string(),
    type: z.string().optional(), // Internship, Full-time, Part-time…
    start: text,
    end: text, // "Present" for current roles
    location: z.string().optional(),
    bullets: z.array(z.string()).min(1),
    tags: z.array(z.string()).default([]),
  }),
);

export const educationSchema = z.array(
  z.object({
    institution: z.string(),
    url: url.optional(),
    degree: z.string(),
    field: z.string(),
    start: text,
    end: text,
    location: z.string().optional(),
    gpa: text.optional(),
    honors: z.array(z.string()).default([]),
    coursework: z.array(z.string()).default([]),
    thesis: z.string().optional(),
  }),
);

export const awardsSchema = z.array(
  z.object({ title: z.string(), issuer: z.string().optional(), year: text, url: url.optional() }),
);

export const certificationsSchema = z.array(
  z.object({ name: z.string(), issuer: z.string(), year: text, url: url.optional() }),
);

export const languagesSchema = z.array(z.object({ name: z.string(), level: z.string() }));

export const skillsSchema = z.array(z.object({ group: z.string(), items: z.array(z.string()).min(1) }));

export const leadershipSchema = z.array(
  z.object({
    title: z.string(),
    organisation: z.string(),
    period: text,
    description: z.string(),
  }),
);

export const researchSchema = z.object({
  eyebrow: z.string(),
  title: z.string(),
  subtitle: z.string(),
  description: z.string(),
  tags: z.array(z.string()).default([]),
  /** Slug of the project MDX that holds the full write-up. */
  project: z.string().optional(),
});

export const suggestedQuestionsSchema = z.array(z.string().max(80)).max(6);

/* ---------------------------------------------------------- project frontmatter */

export const projectStatuses = ["live", "completed", "testing", "in-progress", "archived"] as const;
export const projectCategories = ["agentic", "llm", "cv", "ml", "research"] as const;

export const projectFrontmatterSchema = z.object({
  title: z.string(),
  slug: z.string().regex(/^[a-z0-9]+(?:-[a-z0-9]+)*$/, "slug must be kebab-case"),
  summary: z.string(),
  repo: url,
  demo: url.optional(),
  status: z.enum(projectStatuses),
  category: z.enum(projectCategories),
  tags: z.array(z.string()).default([]),
  stack: z.array(z.string()).default([]),
  timeline: text,
  role: z.string(),
  /** One line, outcome first. Shown in bold on the project card. */
  highlight: z.string(),
  cover: path.optional(),
  /** Pinned on the homepage "Selected work" grid. */
  featured: z.boolean().default(false),
  /** Sort order: lower numbers first. */
  order: z.number().default(100),
  /** Listed under "In the lab" on the homepage. */
  lab: z.boolean().default(false),
  series: z.string().optional(),
});

export type Site = z.infer<typeof siteSchema>;
export type Home = z.infer<typeof homeSchema>;
export type HomeSection = z.infer<typeof homeSectionSchema>;
export type Experience = z.infer<typeof experienceSchema>;
export type Education = z.infer<typeof educationSchema>;
export type Awards = z.infer<typeof awardsSchema>;
export type Certifications = z.infer<typeof certificationsSchema>;
export type Languages = z.infer<typeof languagesSchema>;
export type Skills = z.infer<typeof skillsSchema>;
export type Leadership = z.infer<typeof leadershipSchema>;
export type Research = z.infer<typeof researchSchema>;
export type ProjectFrontmatter = z.infer<typeof projectFrontmatterSchema>;
export type ProjectStatus = (typeof projectStatuses)[number];
