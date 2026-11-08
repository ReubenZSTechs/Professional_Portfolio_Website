/**
 * Content loaders. Server-only: read /content at build time and validate it.
 *
 * Pages call these functions; they never read files themselves. To add a new
 * editable file, add a schema in schemas.ts and a loader here.
 */
import "server-only";
import fs from "node:fs";
import nodePath from "node:path";
import { cache } from "react";
import matter from "gray-matter";
import YAML from "yaml";
import type { z } from "zod";
import {
  awardsSchema,
  certificationsSchema,
  educationSchema,
  experienceSchema,
  homeSchema,
  languagesSchema,
  leadershipSchema,
  projectFrontmatterSchema,
  researchSchema,
  siteSchema,
  skillsSchema,
  suggestedQuestionsSchema,
  type ProjectFrontmatter,
} from "./schemas";

const CONTENT_DIR = nodePath.join(process.cwd(), "content");
const PROJECTS_DIR = nodePath.join(CONTENT_DIR, "projects");

function formatIssues(file: string, error: z.ZodError): string {
  const lines = error.issues.map((i) => `  • ${i.path.join(".") || "(root)"}: ${i.message}`);
  return `Invalid content in content/${file}:\n${lines.join("\n")}`;
}

function parseWith<S extends z.ZodTypeAny>(schema: S, data: unknown, file: string): z.output<S> {
  const result = schema.safeParse(data);
  if (!result.success) throw new Error(formatIssues(file, result.error));
  return result.data;
}

function readYaml<S extends z.ZodTypeAny>(file: string, schema: S, fallback?: unknown): z.output<S> {
  const full = nodePath.join(CONTENT_DIR, file);
  if (!fs.existsSync(full)) {
    if (fallback !== undefined) return parseWith(schema, fallback, file);
    throw new Error(`Missing content file: content/${file}`);
  }
  return parseWith(schema, YAML.parse(fs.readFileSync(full, "utf8")), file);
}

export const getSite = cache(() => readYaml("site.yaml", siteSchema));
export const getHome = cache(() => readYaml("home.yaml", homeSchema));
export const getExperience = cache(() => readYaml("experience.yaml", experienceSchema, []));
export const getEducation = cache(() => readYaml("education.yaml", educationSchema, []));
export const getAwards = cache(() => readYaml("awards.yaml", awardsSchema, []));
export const getCertifications = cache(() => readYaml("certifications.yaml", certificationsSchema, []));
export const getLanguages = cache(() => readYaml("languages.yaml", languagesSchema, []));
export const getSkills = cache(() => readYaml("skills.yaml", skillsSchema, []));
export const getLeadership = cache(() => readYaml("leadership.yaml", leadershipSchema, []));
export const getResearch = cache(() => readYaml("research.yaml", researchSchema));
export const getSuggestedQuestions = cache(() =>
  readYaml("suggested-questions.yaml", suggestedQuestionsSchema, []),
);

/* ------------------------------------------------------------------ projects */

export type Project = ProjectFrontmatter & { body: string };

export const getProjects = cache((): Project[] => {
  if (!fs.existsSync(PROJECTS_DIR)) return [];
  const projects = fs
    .readdirSync(PROJECTS_DIR)
    .filter((f) => f.endsWith(".mdx") && !f.startsWith("_"))
    .map((file) => {
      const { data, content } = matter(fs.readFileSync(nodePath.join(PROJECTS_DIR, file), "utf8"));
      const fm = parseWith(projectFrontmatterSchema, data, `projects/${file}`);
      if (`${fm.slug}.mdx` !== file) {
        throw new Error(`content/projects/${file}: slug "${fm.slug}" must match the file name.`);
      }
      return { ...fm, body: content };
    });
  return projects.sort((a, b) => a.order - b.order || a.title.localeCompare(b.title));
});

export const getProject = (slug: string) => getProjects().find((p) => p.slug === slug);
export const getFeaturedProjects = () => getProjects().filter((p) => p.featured);
export const getLabProjects = () => getProjects().filter((p) => p.lab && !p.featured);

/** The project shown as "Next:" at the bottom of a case study (wraps around). */
export function getNextProject(slug: string): Project | undefined {
  const list = getProjects();
  const i = list.findIndex((p) => p.slug === slug);
  return i === -1 || list.length < 2 ? undefined : list[(i + 1) % list.length];
}
