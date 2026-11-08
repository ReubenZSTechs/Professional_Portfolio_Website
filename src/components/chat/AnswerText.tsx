/**
 * Renders an assistant answer: paragraphs, "- " bullet lists, **bold**, `code`,
 * citation markers ([1] or grouped [2, 4]) linked to the sources panel, and
 * /projects/<slug> paths turned into case-study links.
 *
 * Deliberately tiny instead of a full Markdown library: the system prompt only allows
 * these few constructs, and rendering text (never HTML) keeps model output safe.
 */
import Link from "next/link";
import { Fragment, type ReactNode } from "react";
import clsx from "clsx";

const INLINE = /(\*\*[^*]+\*\*|`[^`]+`|\[\d+(?:\s*,\s*\d+)*\]|\/projects\/[a-z0-9]+(?:-[a-z0-9]+)*)/g;
const BULLET = /^\s*(?:[-*•]|\d+\.)\s+/;

function Inline({ text, citeIds, msgId }: { text: string; citeIds: Set<number>; msgId: string }) {
  const parts = text.split(INLINE);
  return (
    <>
      {parts.map((part, i) => {
        if (!part) return null;
        if (part.startsWith("**") && part.endsWith("**")) {
          return (
            <strong key={i} className="font-semibold text-ink">
              {part.slice(2, -2)}
            </strong>
          );
        }
        if (part.startsWith("`") && part.endsWith("`")) {
          const inner = part.slice(1, -1);
          return /^\/projects\/[a-z0-9-]+$/.test(inner) ? (
            <Link key={i} href={inner}>
              {inner}
            </Link>
          ) : (
            <code key={i} className="rounded bg-chip px-1 text-[0.9em]">
              {inner}
            </code>
          );
        }
        if (/^\[\d/.test(part)) {
          const nums = part.slice(1, -1).split(",").map((n) => Number(n.trim()));
          return (
            <span key={i} className="whitespace-nowrap text-[13px] font-semibold">
              {nums.map((n) => (
                <Fragment key={n}>
                  {citeIds.has(n) ? (
                    <a href={`#${msgId}-src-${n}`} className="no-underline">
                      [{n}]
                    </a>
                  ) : (
                    <span className="text-muted">[{n}]</span>
                  )}
                </Fragment>
              ))}
            </span>
          );
        }
        if (part.startsWith("/projects/")) {
          return (
            <Link key={i} href={part}>
              {part}
            </Link>
          );
        }
        return <Fragment key={i}>{part}</Fragment>;
      })}
    </>
  );
}

type Block = { kind: "p"; lines: string[] } | { kind: "ul"; items: string[] };

function toBlocks(text: string): Block[] {
  const blocks: Block[] = [];
  // A blank line ends a paragraph; consecutive bullet lines (even across blank lines) form one list.
  for (const chunk of text.split(/\n{2,}/)) {
    let para: string[] | null = null;
    for (const line of chunk.split("\n")) {
      if (!line.trim()) continue;
      if (BULLET.test(line)) {
        para = null;
        const last = blocks[blocks.length - 1];
        const item = line.replace(BULLET, "");
        if (last?.kind === "ul") last.items.push(item);
        else blocks.push({ kind: "ul", items: [item] });
      } else {
        if (!para) {
          para = [];
          blocks.push({ kind: "p", lines: para });
        }
        para.push(line);
      }
    }
  }
  return blocks;
}

export function AnswerText({
  text,
  citeIds,
  msgId,
  pending,
}: {
  text: string;
  citeIds: Set<number>;
  msgId: string;
  pending?: boolean;
}): ReactNode {
  const blocks = toBlocks(text);
  if (blocks.length === 0) return pending ? <p className="caret m-0 text-muted" /> : null;
  return blocks.map((block, i) => {
    const isLast = i === blocks.length - 1;
    if (block.kind === "ul") {
      return (
        <ul key={i} className={clsx("m-0 flex flex-col gap-1.5 pl-5", pending && isLast && "caret")}>
          {block.items.map((item, j) => (
            <li key={j} className="list-disc marker:text-muted">
              <Inline text={item} citeIds={citeIds} msgId={msgId} />
            </li>
          ))}
        </ul>
      );
    }
    return (
      <p key={i} className={clsx("m-0", pending && isLast && "caret")}>
        {block.lines.map((line, j) => (
          <Fragment key={j}>
            {j > 0 && <br />}
            <Inline text={line} citeIds={citeIds} msgId={msgId} />
          </Fragment>
        ))}
      </p>
    );
  });
}
