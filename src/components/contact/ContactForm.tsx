"use client";

import { useState, type FormEvent } from "react";
import { useTurnstile } from "@/components/security/useTurnstile";
import { ApiError, sendContact } from "@/lib/api";

type Status = { kind: "idle" } | { kind: "sending" } | { kind: "sent" } | { kind: "error"; message: string };

const fieldClass =
  "min-h-11 rounded-[10px] border border-inverse-line bg-inverse-surface px-3.5 text-inverse-ink placeholder:text-inverse-muted/60";

export function ContactForm() {
  const turnstile = useTurnstile("contact");
  const [status, setStatus] = useState<Status>({ kind: "idle" });

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const data = new FormData(form);
    setStatus({ kind: "sending" });
    try {
      await sendContact({
        name: String(data.get("name") ?? ""),
        email: String(data.get("email") ?? ""),
        message: String(data.get("message") ?? ""),
        company: String(data.get("company") ?? ""), // honeypot: real people leave it empty
        turnstileToken: await turnstile.getToken(),
      });
      form.reset();
      setStatus({ kind: "sent" });
    } catch (err) {
      setStatus({
        kind: "error",
        message: err instanceof ApiError ? err.message : "Could not send your message. Please email me directly.",
      });
    }
  }

  if (status.kind === "sent") {
    return (
      <div role="status" className="flex min-w-0 flex-[1_1_400px] flex-col gap-2 rounded-2xl border border-inverse-line p-6">
        <p className="m-0 text-lg font-semibold">Thanks, your message is on its way.</p>
        <p className="m-0 text-inverse-muted">I&apos;ll get back to you by email.</p>
      </div>
    );
  }

  return (
    <form onSubmit={onSubmit} className="flex min-w-0 flex-[1_1_400px] flex-col gap-3.5" noValidate={false}>
      <label htmlFor="c-name" className="text-sm text-inverse-muted">
        Name
      </label>
      <input id="c-name" name="name" type="text" required maxLength={120} autoComplete="name" className={fieldClass} />
      <label htmlFor="c-email" className="text-sm text-inverse-muted">
        Email
      </label>
      <input id="c-email" name="email" type="email" required maxLength={200} autoComplete="email" className={fieldClass} />
      <label htmlFor="c-msg" className="text-sm text-inverse-muted">
        Message
      </label>
      <textarea id="c-msg" name="message" rows={4} required minLength={10} maxLength={4000} className={`${fieldClass} resize-y py-3`} />
      {/* Honeypot field, hidden from people and screen readers. Bots tend to fill it. */}
      <div aria-hidden className="absolute -left-[9999px]">
        <label htmlFor="c-company">Company</label>
        <input id="c-company" name="company" type="text" tabIndex={-1} autoComplete="off" />
      </div>
      {status.kind === "error" && (
        <p role="alert" className="m-0 rounded-lg bg-warning-bg px-3 py-2 text-sm text-warning-ink">
          {status.message}
        </p>
      )}
      {turnstile.slot}
      <button
        type="submit"
        disabled={status.kind === "sending"}
        className="min-h-12 self-start rounded-[10px] bg-inverse-ink px-6 font-semibold text-inverse-bg transition hover:opacity-90 disabled:opacity-60"
      >
        {status.kind === "sending" ? "Sending…" : "Send message"}
      </button>
    </form>
  );
}
