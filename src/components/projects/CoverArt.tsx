/**
 * Generated cover art for projects without a screenshot yet (no `cover:` in frontmatter).
 * Each category gets its own tint and line icon so the grid doesn't look repetitive.
 * Add a real screenshot as `cover:` and this disappears for that project.
 */
import type { ProjectFrontmatter } from "@/lib/schemas";

type Category = ProjectFrontmatter["category"];

const tints: Record<Category, string> = {
  agentic: "#1F5EDC",
  llm: "#7C3AED",
  research: "#0F766E",
  cv: "#C2410C",
  ml: "#0369A1",
};

const icons: Record<Category, React.ReactNode> = {
  // a small agent graph
  agentic: (
    <>
      <circle cx="100" cy="100" r="26" />
      <circle cx="40" cy="45" r="13" />
      <circle cx="162" cy="48" r="13" />
      <circle cx="158" cy="156" r="13" />
      <circle cx="38" cy="150" r="13" />
      <path d="M50 54l30 28M151 57l-31 25M148 147l-29-26M48 141l32-24" />
    </>
  ),
  // a document turning into a chat bubble
  llm: (
    <>
      <rect x="38" y="30" width="80" height="104" rx="10" />
      <path d="M56 58h44M56 78h44M56 98h28" />
      <path d="M104 112h56a12 12 0 0 1 12 12v30a12 12 0 0 1-12 12h-30l-18 16v-16h-8a12 12 0 0 1-12-12v-30a12 12 0 0 1 12-12z" />
    </>
  ),
  // graph-of-thoughts
  research: (
    <>
      <circle cx="100" cy="40" r="12" />
      <circle cx="56" cy="100" r="12" />
      <circle cx="144" cy="100" r="12" />
      <circle cx="100" cy="160" r="16" />
      <path d="M93 50l-30 40M107 50l30 40M63 110l28 38M137 110l-28 38M68 100h64" />
    </>
  ),
  // a lens with a detection box
  cv: (
    <>
      <rect x="40" y="48" width="120" height="104" rx="12" />
      <circle cx="100" cy="100" r="28" />
      <path d="M60 64h20M60 64v20M140 136h-20M140 136v-20" />
    </>
  ),
  // a rising chart
  ml: (
    <>
      <path d="M36 164h128M36 164V36" />
      <path d="M48 140l32-34 26 20 46-58" />
      <circle cx="152" cy="68" r="6" />
    </>
  ),
};

export function CoverArt({ project }: { project: Pick<ProjectFrontmatter, "category" | "title"> }) {
  const tint = tints[project.category];
  return (
    <div
      aria-hidden
      className="relative h-full overflow-hidden"
      style={{
        background: `radial-gradient(120% 120% at 100% 0%, color-mix(in oklab, ${tint} 28%, transparent), transparent 60%),
          radial-gradient(90% 90% at 0% 100%, color-mix(in oklab, ${tint} 14%, transparent), transparent 70%),
          var(--chip)`,
      }}
    >
      <svg
        viewBox="0 0 200 200"
        fill="none"
        strokeWidth="3"
        strokeLinecap="round"
        strokeLinejoin="round"
        className="absolute top-1/2 right-[8%] h-[78%] -translate-y-1/2 opacity-60"
        style={{ stroke: tint }}
      >
        {icons[project.category]}
      </svg>
      {/* faint dot grid for texture */}
      <div
        className="absolute inset-0 opacity-[0.35]"
        style={{
          backgroundImage: "radial-gradient(color-mix(in oklab, var(--ink) 18%, transparent) 1px, transparent 1px)",
          backgroundSize: "18px 18px",
          maskImage: "linear-gradient(90deg, black, transparent 70%)",
        }}
      />
    </div>
  );
}
