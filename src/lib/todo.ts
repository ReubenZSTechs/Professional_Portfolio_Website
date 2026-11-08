/**
 * Placeholder convention: any content value that starts with "TODO" (YAML/frontmatter)
 * or any <Todo> block in MDX is a reminder for Reuben. They render highlighted
 * in `npm run dev` and disappear in production builds, so an unfinished detail
 * never shows up on the live site.
 *
 * Set SHOW_TODOS=true to show them in a production preview.
 */
export const showTodos =
  process.env.NODE_ENV !== "production" || process.env.SHOW_TODOS === "true";

export const isTodo = (value: string | undefined | null): boolean =>
  typeof value === "string" && /^\s*TODO\b/i.test(value);

/** Returns the value, or undefined when it is a placeholder that should be hidden. */
export const visible = (value: string | undefined): string | undefined =>
  value && (!isTodo(value) || showTodos) ? value : undefined;
