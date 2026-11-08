"use client";

import { useCallback, useRef, useState } from "react";
import {
  ApiError,
  explainChatFailure,
  streamChat,
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
};

/** Must match MAX_HISTORY_TURNS in backend/src/core/config.py. */
const MAX_HISTORY_TURNS = 10;

let counter = 0;
const newId = () => `m${Date.now()}-${counter++}`;

/**
 * Chat state + streaming. The server is stateless, so the recent history is
 * sent with every question; the prompt-rewriter agent uses it to resolve
 * follow-ups like "what stack did it use?".
 */
export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [stage, setStage] = useState<ChatStage | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const busy = stage !== null;

  const update = (id: string, patch: (m: ChatMessage) => Partial<ChatMessage>) =>
    setMessages((all) => all.map((m) => (m.id === id ? { ...m, ...patch(m) } : m)));

  const ask = useCallback(
    async (question: string) => {
      const text = question.trim();
      if (!text || busy) return;

      const history: ChatTurn[] = messages
        .filter((m) => !m.error && m.content)
        .slice(-MAX_HISTORY_TURNS * 2)
        .map(({ role, content }) => ({ role, content }));

      const userMsg: ChatMessage = { id: newId(), role: "user", content: text };
      const botId = newId();
      setMessages((all) => [...all, userMsg, { id: botId, role: "assistant", content: "", pending: true }]);
      setStage("rewriting");

      const controller = new AbortController();
      abortRef.current = controller;
      try {
        for await (const ev of streamChat(text, history, controller.signal)) {
          switch (ev.event) {
            case "status":
              setStage(ev.data.stage);
              break;
            case "token":
              update(botId, (m) => ({ content: m.content + ev.data.text }));
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
              break;
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
    [busy, messages],
  );

  const stop = useCallback(() => abortRef.current?.abort(), []);
  const reset = useCallback(() => {
    abortRef.current?.abort();
    setMessages([]);
    setStage(null);
  }, []);

  return { messages, stage, busy, ask, stop, reset };
}
