"use client";

import { useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import clsx from "clsx";
import type { ChatStage, Source } from "@/lib/api";
import { ArrowIcon } from "@/components/ui";
import { AnswerText } from "./AnswerText";
import { useTurnstile } from "@/components/security/useTurnstile";
import { useChat, type ChatMessage } from "./useChat";

const MAX_CHARS = 500; // matches MAX_QUESTION_CHARS on the backend

const stageLabels: Record<ChatStage, string> = {
  rewriting: "Understanding your question…",
  retrieving: "Searching my CV and projects…",
  answering: "Writing an answer…",
};

const sourceTypeLabels: Record<Source["type"], string> = {
  project: "Project",
  experience: "Experience",
  research: "Research",
  education: "Education",
  profile: "Profile",
  knowledge: "Background",
};

function Message({ message }: { message: ChatMessage }) {
  if (message.role === "user") {
    return (
      <div className="max-w-[85%] self-end rounded-[16px_16px_4px_16px] bg-ink px-4 py-3 text-bg">{message.content}</div>
    );
  }
  const citeIds = new Set(message.sources?.map((s) => s.id));
  return (
    <div className="flex max-w-[94%] gap-3 self-start">
      <span aria-hidden className="inline-flex size-8 flex-none items-center justify-center rounded-full bg-accent font-display text-sm font-bold text-white">
        R
      </span>
      <div className="flex min-w-0 flex-col gap-3 pt-1 text-body">
        <AnswerText text={message.content} citeIds={citeIds} msgId={message.id} pending={message.pending} />
        {message.error && (
          <p role="alert" className="m-0 rounded-lg bg-warning-bg px-3 py-2 text-sm text-warning-ink">
            {message.error}
          </p>
        )}
      </div>
    </div>
  );
}

function SourcesPanel({ message }: { message?: ChatMessage }) {
  const sources = message?.sources ?? [];
  return (
    <aside
      aria-label="Sources used in this answer"
      className="flex min-w-0 flex-[2_1_320px] flex-col gap-4 border-t border-line bg-surface-raised/60 p-6 sm:p-7 lg:border-t-0 lg:border-l"
    >
      <h3 className="m-0 text-sm font-semibold tracking-[0.06em] text-muted uppercase">Sources for this answer</h3>
      {sources.length === 0 ? (
        <p className="m-0 text-sm text-muted">
          Every answer cites where it came from: my CV, project case studies or repositories. Sources appear here.
        </p>
      ) : (
        <ol className="m-0 flex list-none flex-col p-0">
          {sources.map((s) => (
            <li
              key={s.id}
              id={`${message!.id}-src-${s.id}`}
              className="flex scroll-mt-28 flex-col gap-1.5 border-b border-line py-4 first:pt-0 last:border-b-0"
            >
              <span className="text-xs font-semibold text-muted">
                [{s.id}] {sourceTypeLabels[s.type] ?? "Source"}
                {s.section ? ` · ${s.section}` : ""}
              </span>
              <strong className="text-ink">{s.title}</strong>
              <span className="line-clamp-3 text-sm text-muted">{s.snippet}</span>
              {s.url && (
                <a href={s.url} className="text-sm font-semibold">
                  {s.url.startsWith("/projects/") ? "Open case study" : "Open source"}
                </a>
              )}
            </li>
          ))}
        </ol>
      )}
    </aside>
  );
}

export function ChatPanel({ suggestions }: { suggestions: string[] }) {
  const turnstile = useTurnstile("chat");
  const { messages, stage, busy, ask, stop, reset } = useChat(turnstile.getToken);
  const [input, setInput] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);
  const lastAssistant = [...messages].reverse().find((m) => m.role === "assistant");

  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
  }, [messages]);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;
    void ask(input);
    setInput("");
  };

  return (
    <div className="glass flex flex-wrap overflow-hidden rounded-[20px] shadow-card">
      <div className="flex min-w-0 flex-[3_1_560px] flex-col">
        <div
          ref={scrollRef}
          className="flex max-h-[560px] min-h-[380px] flex-auto flex-col gap-4 overflow-y-auto p-5 sm:p-7"
          aria-live="polite"
          aria-busy={busy}
        >
          {messages.length === 0 ? (
            <div className="m-auto flex max-w-md flex-col items-center gap-2 text-center">
              <span aria-hidden className="inline-flex size-11 items-center justify-center rounded-full bg-accent-soft font-display text-lg font-bold text-accent">
                R
              </span>
              <p className="m-0 font-semibold text-ink">Hi! I&apos;m an assistant trained on Reuben&apos;s work.</p>
              <p className="m-0 text-sm text-muted">
                Ask about his projects, experience or stack. I only answer from his CV and case studies, and I&apos;ll tell
                you when I don&apos;t know.
              </p>
            </div>
          ) : (
            messages.map((m) => <Message key={m.id} message={m} />)
          )}
          {stage && <p className="m-0 text-sm text-muted">{stageLabels[stage]}</p>}
        </div>

        {suggestions.length > 0 && (
          <div className="flex flex-wrap gap-2 px-5 pb-4 sm:px-7">
            {suggestions.map((q) => (
              <button
                key={q}
                type="button"
                disabled={busy}
                onClick={() => void ask(q)}
                className="min-h-11 rounded-full border border-line-strong bg-bg px-4 text-sm text-ink transition hover:border-ink disabled:opacity-50"
              >
                {q}
              </button>
            ))}
          </div>
        )}

        {/* Shown only if Cloudflare needs a one-click check; invisible otherwise. */}
        <div className="px-5 sm:px-7">{turnstile.slot}</div>
        <form onSubmit={submit} className="flex gap-2.5 border-t border-line px-5 pt-4 pb-5 sm:px-7">
          <label htmlFor="ask-input" className="sr-only">
            Ask a question about Reuben
          </label>
          <input
            id="ask-input"
            type="text"
            value={input}
            maxLength={MAX_CHARS}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about my projects, stack or experience"
            autoComplete="off"
            className="min-h-13 min-w-0 flex-auto rounded-xl border border-line-strong bg-bg px-4 text-ink placeholder:text-muted"
          />
          {busy ? (
            <button type="button" onClick={stop} className="min-h-13 rounded-xl border border-line-strong px-5 font-semibold text-ink">
              Stop
            </button>
          ) : (
            <button
              type="submit"
              disabled={!input.trim()}
              className="inline-flex min-h-13 items-center gap-2 rounded-xl bg-accent px-5 font-semibold text-white transition hover:bg-accent-strong disabled:opacity-60"
            >
              Ask <ArrowIcon />
            </button>
          )}
        </form>
        {messages.length > 0 && !busy && (
          <button type="button" onClick={reset} className="mb-4 self-center text-sm text-muted underline-offset-4 hover:underline">
            Start a new conversation
          </button>
        )}
      </div>

      <SourcesPanel message={lastAssistant} />
    </div>
  );
}
