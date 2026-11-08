/**
 * Maps the section ids used in content/home.yaml to their components.
 * The homepage renders whatever home.yaml lists, in that order, so
 * reordering or hiding sections never needs a code change.
 *
 * To add a new section type: build the component, add its id to `sectionIds`
 * in lib/schemas.ts, and register it here.
 */
import type { ComponentType } from "react";
import type { HomeSection, SectionId } from "@/lib/schemas";
import { AskSection } from "./AskSection";
import { ContactSection } from "./ContactSection";
import { EducationSection } from "./EducationSection";
import { ExperienceSection } from "./ExperienceSection";
import { Hero } from "./Hero";
import { LeadershipSection } from "./LeadershipSection";
import { ProjectsSection } from "./ProjectsSection";
import { ResearchSection } from "./ResearchSection";
import { ToolkitSection } from "./ToolkitSection";

export type SectionProps = { section: HomeSection; anchor: string };

export const sectionRegistry: Record<SectionId, ComponentType<SectionProps>> = {
  hero: Hero,
  ask: AskSection,
  experience: ExperienceSection,
  projects: ProjectsSection,
  research: ResearchSection,
  education: EducationSection,
  toolkit: ToolkitSection,
  leadership: LeadershipSection,
  contact: ContactSection,
};
