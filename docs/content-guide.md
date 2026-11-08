# Content guide: editing the site

Everything visitors read lives in **`content/`**. You never need to touch components to change text, reorder sections, or pin projects.

## The editing loop
1. Edit a file in `content/` (locally in your editor, or directly on github.com with the ✏️ button).
2. Preview locally with `npm run dev` (http://localhost:3000). Pages reload when you save.
3. Commit and push to `main`. Vercel rebuilds and publishes in about a minute. GitHub Actions re-indexes the chatbot's knowledge at the same time.
4. Want a review link first? Push to another branch: Vercel gives every branch its own preview URL.

If a file has a mistake (missing field, wrong type), `npm run build` and the Vercel build **fail with a message naming the file and field**, so a broken page never goes live.

## Quick reference
| Change | File | Field |
|---|---|---|
| Headline, intro, role, location | `content/site.yaml` | `headline`, `intro`, `role`, `location` |
| Hero numbers (3.90 GPA, 1st…) | `content/site.yaml` | `highlights` (max 6) |
| "Open to roles" banner | `content/site.yaml` | `availability` (set `open: false` to hide) |
| Brand colour | `content/site.yaml` | `accent` |
| Email, LinkedIn, GitHub, WhatsApp | `content/site.yaml` | `links` |
| CV download | put the PDF at `public/cv.pdf` | `cv.href` |
| Portrait | `public/images/portrait.jpg` | `portrait` |
| Reorder / hide homepage sections | `content/home.yaml` | order of `sections`, `enabled: false` |
| Section titles and intros | `content/home.yaml` | `eyebrow`, `title`, `description` |
| Pin / unpin a project on the homepage | `content/projects/<slug>.mdx` | `featured`, `order` |
| "In the lab" list | `content/projects/<slug>.mdx` | `lab: true` |
| Add a project | copy `content/projects/_template.mdx` | see below |
| Jobs | `content/experience.yaml` | |
| Degree, GPA, honours | `content/education.yaml` | |
| Certificates | `content/certifications.yaml` | section hides itself while empty |
| Languages | `content/languages.yaml` | |
| Awards | `content/awards.yaml` | |
| Skills | `content/skills.yaml` | |
| Leadership & teaching | `content/leadership.yaml` | |
| Thesis block | `content/research.yaml` | |
| Chat suggestion chips | `content/suggested-questions.yaml` | max 6 |
| Facts only the chatbot should know | `knowledge/*.md` | free text |

## `site.yaml`
```yaml
accent: "#1F5EDC"          # hex only; mockup options: #1F5EDC #0F766E #7C3AED #C2410C
availability:
  open: true
  label: Open to AI Engineer roles
  details: [Internships now · full-time from Aug 2027, Jakarta (WIB, UTC+7) · remote or relocation]
links:
  whatsapp: "6281234567890"  # optional; international format, digits only. Adds a WhatsApp link.
```

## `home.yaml`
Section ids: `hero`, `ask`, `experience`, `projects`, `research`, `education`, `toolkit`, `leadership`, `contact`.
```yaml
sections:
  - id: hero
  - id: projects            # move this line up to show projects before the chat
    anchor: work            # URL anchor (#work); defaults to the id
    eyebrow: Selected work
    title: Projects
  - id: leadership
    enabled: false          # hidden, settings kept
```
If you change an `anchor`, update the matching `nav` link in `site.yaml`.

## Project frontmatter
The file name must equal the `slug`, e.g. `content/projects/plantatio.mdx` → `slug: plantatio` → `/projects/plantatio`.

| Field | Required | Notes |
|---|---|---|
| `title` | ✓ | |
| `slug` | ✓ | kebab-case, equals the file name |
| `summary` | ✓ | one sentence; shown on cards and in search results |
| `repo` | ✓ | full GitHub URL |
| `demo` | | live demo URL |
| `status` | ✓ | `live` (deployed, link a `demo`) · `completed` (finished and working) · `testing` · `in-progress` · `archived` |
| `category` | ✓ | `agentic` · `llm` · `cv` · `ml` · `research` (filters on /projects) |
| `tags` | | first 4 shown on cards |
| `stack` | | first 4 shown in the case-study header |
| `timeline` | ✓ | free text, e.g. `Apr 2026 – present` |
| `role` | ✓ | e.g. `Solo` or `Team of 3 · I owned the agent logic` |
| `highlight` | ✓ | the one result to remember; bold on cards |
| `cover` | | `/images/projects/<slug>.webp`, 2:1 (e.g. 1400×700); shown on cards and at the top of the case study. Without it, generated cover art is used |
| `featured` | | `true` = pinned in "Selected work" |
| `order` | | lower = earlier (homepage, /projects, "Next project") |
| `lab` | | `true` = listed under "In the lab" (if not featured) |
| `series` | | grouping label, e.g. `athena` |

## MDX components
Use these inside project files; they render the case-study blocks from the mockup.
```mdx
<Pipeline steps={["Upload PDF", "Chunk", "Retrieve", "LLM", "Report"]} highlight={4} />

<Decisions>
  <Decision title="LoRA + quantisation">Why, and the trade-off you accepted.</Decision>
</Decisions>

<Metrics>
  <Metric value="~40%" label="Less literature-review time" />
</Metrics>

<Callout>A note, disclaimer or warning.</Callout>

<Figure src="/images/projects/my-demo.webp" alt="What the screenshot shows" caption="Optional caption" width={1200} height={800} />

<Todo>Something to fill in later (dev only).</Todo>
```
Normal Markdown works too: headings (`##`), lists, links, **bold**, tables, and code. Internal links like `[Arthur](/projects/arthur-research-paper-summarizer)` navigate without a page reload.

**MDX gotchas**: a literal `{` or `<` in prose must be escaped (`\{`, `&lt;`), and component props with arrays need `{[...]}`.

## Adding images
Put files in `public/images/projects/` and reference them as `/images/projects/name.webp`: in `cover:` (2:1 crop) or with `<Figure … width height />` inside the MDX (`width`/`height` are the file's pixel size, which prevents layout shift). Keep each file under ~150 KB; WebP works best. To make one from a screenshot:
```bash
cwebp -q 78 screenshot.png -o public/images/projects/my-project.webp
```
Next.js serves resized versions automatically.

## Animations
Sections fade in as they scroll into view (`src/components/ui/Reveal.tsx`). Content you add inside existing sections is animated automatically. Visitors with "reduce motion" turned on see everything immediately.
