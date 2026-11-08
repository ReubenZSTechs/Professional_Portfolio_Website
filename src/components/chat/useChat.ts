"use client";

import { useCallback, useRef, useState } from "react";
import {
  ApiError,
  explainChatFailure,
  streamChat,
  type ChatEvent,
  type ChatStage,
  type ChatTurn,
  type Source,
} from "@/lib/api";

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  error?: string;
  pending?: boolean;
  /** Server signature on a finished assistant answer; sent back with history. */
  sig?: string;
};

/** Must match MAX_HISTORY_TURNS in backend/src/core/config.py. */
const MAX_HISTORY_TURNS = 10;
/** Keep the request well under the API's 64 KB body limit by dropping the oldest turns. */
const MAX_HISTORY_CHARS = 30_000;
const SESSION_KEY = "chat-session";

let counter = 0;
const newId = () => `m${Date.now()}-${counter++}`;

function readSession(): string | null {
  try {
    return sessionStorage.getItem(SESSION_KEY);
  } catch {
    return null;
  }
}

function writeSession(token: string | null) {
  try {
    if (token) sessionStorage.setItem(SESSION_KEY, token);
    else sessionStorage.removeItem(SESSION_KEY);
  } catch {
    /* storage blocked: the token just lives for this page view */
  }
}

/** Session tokens look like `v1.<unix expiry>.<sig>`; treat ones about to expire as gone. */
function sessionStillValid(token: string | null): boolean {
  const expiry = Number(token?.split(".")[1]);
  return Number.isFinite(expiry) && expiry * 1000 > Date.now() + 30_000;
}

function buildHistory(messages: ChatMessage[]): ChatTurn[] {
  const turns: ChatTurn[] = messages
    .filter((m) => !m.error && m.content && !m.pending)
    // Unsigned assistant turns would be dropped by the server anyway.
    .filter((m) => m.role === "user" || m.sig)
    .slice(-MAX_HISTORY_TURNS * 2)
    .map(({ role, content, sig }) => (role === "assistant" ? { role, content, sig } : { role, content }));
  while (turns.length && JSON.stringify(turns).length > MAX_HISTORY_CHARS) turns.shift();
  return turns;
}

/**
 * Chat state + streaming. The server is stateless, so the recent history is sent with every
 * question; the prompt-rewriter agent uses it to resolve follow-ups like "what stack did it use?".
 *
 * Security (docs/security.md): the first question passes an invisible Turnstile check and gets
 * a signed 30-minute session; assistant answers carry server signatures so history can't be forged.
 */
export function useChat(getVerificationToken?: () => Promise<string | null>) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [stage, setStage] = useState<ChatStage | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const sessionRef = useRef<string | null>(null);
  const busy = stage !== null;

  const update = (id: string, patch: (m: ChatMessage) => Partial<ChatMessage>) =>
    setMessages((all) => all.map((m) => (m.id === id ? { ...m, ...patch(m) } : m)));

  const ask = useCallback(
    async (question: string) => {
      const text = question.trim();
      if (!text || busy) return;

      const history = buildHistory(messages);
      const userMsg: ChatMessage = { id: newId(), role: "user", content: text };
      const botId = newId();
      setMessages((all) => [...all, userMsg, { id: botId, role: "assistant", content: "", pending: true }]);
      setStage("rewriting");

      const controller = new AbortController();
      abortRef.current = controller;

      const handle = async (ev: ChatEvent) => {
        switch (ev.event) {
          case "session":
            sessionRef.current = ev.data.token;
            writeSession(ev.data.token);
            break;
          case "status":
            setStage(ev.data.stage);
            break;
          case "token":
            update(botId, (m) => ({ content: m.content + ev.data.text }));
            break;
          case "retract":
            // The output guard stopped this answer: replace whatever was shown.
            update(botId, () => ({ content: ev.data.text, sources: undefined }));
            break;
          case "sources":
            update(botId, () => ({ sources: ev.data.sources }));
            break;
          case "error": {
            // "busy" (every Gemini model overloaded) is already a clear, visitor-facing message.
            const message =
              ev.data.code === "busy" ? ev.data.message : await explainChatFailure(ev.data.message);
            update(botId, () => ({ error: message }));
            break;
          }
          case "done":
            if (ev.data.sig) update(botId, () => ({ sig: ev.data.sig }));
            break;
        }
      };

      const attempt = async (forceVerification: boolean) => {
        sessionRef.current ??= readSession();
        let session = forceVerification ? null : sessionRef.current;
        if (!sessionStillValid(session)) session = null;
        const turnstileToken = session ? null : ((await getVerificationToken?.()) ?? null);
        for await (const ev of streamChat(text, history, { sessionToken: session, turnstileToken }, controller.signal)) {
          await handle(ev);
        }
      };

      try {
        try {
          await attempt(false);
        } catch (err) {
          // The session expired or was rejected: verify again once, transparently.
          if (err instanceof ApiError && err.code === "verification" && getVerificationToken) {
            sessionRef.current = null;
            writeSession(null);
            await attempt(true);
          } else {
            throw err;
          }
        }
      } catch (err) {
        if (controller.signal.aborted) return;
        const generic = "The assistant is unavailable right now. Please try again later.";
        const message =
          err instanceof ApiError && err.status < 500 ? err.message : await explainChatFailure(generic);
        update(botId, () => ({ error: message }));
      } finally {
        update(botId, () => ({ pending: false }));
        setStage(null);
        abortRef.current = null;
      }
    },
    [busy, messages, getVerificationToken],
  );

  const stop = useCallback(() => abortRef.current?.abort(), []);
  const reset = useCallback(() => {
    abortRef.current?.abort();
    setMessages([]);
    setStage(null);
  }, []);

  return { messages, stage, busy, ask, stop, reset };
}
