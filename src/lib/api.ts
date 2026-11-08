/**
 * Typed client for the Python backend (FastAPI under /api/py).
 * The wire format is documented in docs/api.md; keep both in sync.
 */

export type ChatRole = "user" | "assistant";
/** `sig` is the server's signature on an assistant answer; unsigned assistant turns are dropped
 * server-side, so forged history can't steer the bot (docs/security.md). */
export type ChatTurn = { role: ChatRole; content: string; sig?: string };

export type Source = {
  /** Citation number used in the answer text, e.g. [1]. */
  id: number;
  type: "project" | "experience" | "research" | "education" | "profile" | "knowledge";
  title: string;
  section?: string | null;
  snippet: string;
  url?: string | null;
};

export type ChatStage = "rewriting" | "retrieving" | "answering";

export type ChatEvent =
  | { event: "status"; data: { stage: ChatStage } }
  | { event: "token"; data: { text: string } }
  | { event: "sources"; data: { sources: Source[] } }
  | { event: "retract"; data: { text: string } }
  | { event: "session"; data: { token: string } }
  | { event: "error"; data: { message: string; code?: string } }
  | { event: "done"; data: { sig?: string } };

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    /** Machine-readable reason from the X-Error-Code header, e.g. "verification", "quota". */
    public code?: string,
  ) {
    super(message);
  }
}

const API_BASE = "/api/py";

async function errorMessage(res: Response): Promise<string> {
  try {
    const body = (await res.json()) as { detail?: unknown };
    if (typeof body.detail === "string") return body.detail;
  } catch {
    /* not JSON */
  }
  if (res.status === 429) return "Too many questions in a short time. Please wait a minute and try again.";
  return "Something went wrong. Please try again.";
}

/** Parses a text/event-stream body into typed events. */
async function* readEvents(body: ReadableStream<Uint8Array>): AsyncGenerator<ChatEvent> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, "\n");
    let sep: number;
    while ((sep = buffer.indexOf("\n\n")) !== -1) {
      const raw = buffer.slice(0, sep);
      buffer = buffer.slice(sep + 2);
      let event = "message";
      const data: string[] = [];
      for (const line of raw.split("\n")) {
        if (line.startsWith("event:")) event = line.slice(6).trim();
        else if (line.startsWith("data:")) data.push(line.slice(5).trimStart());
      }
      if (data.length === 0) continue;
      try {
        yield { event, data: JSON.parse(data.join("\n")) } as ChatEvent;
      } catch {
        /* ignore malformed frames */
      }
    }
  }
}

async function apiError(res: Response): Promise<ApiError> {
  return new ApiError(await errorMessage(res), res.status, res.headers.get("X-Error-Code") ?? undefined);
}

export type ChatAuth = {
  /** Fresh Cloudflare Turnstile token (only needed when there's no valid session). */
  turnstileToken?: string | null;
  /** Signed chat-session token from an earlier `session` event. */
  sessionToken?: string | null;
};

export async function* streamChat(
  message: string,
  history: ChatTurn[],
  auth: ChatAuth = {},
  signal?: AbortSignal,
): AsyncGenerator<ChatEvent> {
  const headers: Record<string, string> = { "Content-Type": "application/json", Accept: "text/event-stream" };
  if (auth.sessionToken) headers["X-Chat-Session"] = auth.sessionToken;
  const res = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers,
    body: JSON.stringify({ message, history, turnstile_token: auth.turnstileToken ?? null }),
    signal,
  });
  if (!res.ok || !res.body) throw await apiError(res);
  yield* readEvents(res.body);
}

export type ContactPayload = {
  name: string;
  email: string;
  message: string;
  company?: string;
  turnstileToken?: string | null;
};

export async function sendContact({ turnstileToken, ...payload }: ContactPayload): Promise<void> {
  const res = await fetch(`${API_BASE}/contact`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...payload, turnstile_token: turnstileToken ?? null }),
  });
  if (!res.ok) throw await apiError(res);
}

type Health = { configured: Record<string, boolean> };

/**
 * Turns a chat failure into an actionable message. In development it checks /api/py/health
 * to say exactly what's missing; visitors in production get a polite generic message.
 * See docs/troubleshooting.md → "Chat doesn't work locally".
 */
export async function explainChatFailure(fallback: string): Promise<string> {
  if (process.env.NODE_ENV !== "development") return fallback;
  let res: Response;
  try {
    res = await fetch(`${API_BASE}/health`, { cache: "no-store" });
  } catch {
    return "Dev: the Python API isn't reachable. Start both servers with `npm run dev:all`.";
  }
  if (!res.ok) {
    return "Dev: the Python API isn't running (the /api/py proxy failed). Start both servers with `npm run dev:all`.";
  }
  const health = (await res.json()) as Health;
  const missing = Object.entries(health.configured)
    // Only these are required for the chat locally; Resend and Turnstile are optional in dev.
    .filter(([name, ok]) => !ok && (name === "gemini" || name === "supabase"))
    .map(([name]) => name);
  if (missing.length) {
    return `Dev: ${missing.join(" and ")} ${missing.length > 1 ? "aren't" : "isn't"} configured. Fill in .env (see .env.example) and restart \`npm run dev:all\`.`;
  }
  return `${fallback} (Dev: the API is up and configured. Check the API terminal for the traceback; see docs/troubleshooting.md.)`;
}
