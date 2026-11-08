"use client";

/**
 * Cloudflare Turnstile: an invisible "are you human?" check (docs/security.md).
 *
 * Most visitors never see anything. If Cloudflare is unsure, a small checkbox appears in the
 * returned `slot` element. `getToken()` resolves to a fresh single-use token, or null when no
 * site key is configured (local development without Turnstile).
 */
import { useCallback, useEffect, useRef, type ReactNode } from "react";

type TurnstileOptions = {
  sitekey: string;
  action?: string;
  appearance?: "always" | "execute" | "interaction-only";
  execution?: "render" | "execute";
  theme?: "auto" | "light" | "dark";
  callback?: (token: string) => void;
  "error-callback"?: () => void;
  "expired-callback"?: () => void;
};

type TurnstileApi = {
  render: (el: HTMLElement, options: TurnstileOptions) => string;
  execute: (widgetId: string) => void;
  reset: (widgetId: string) => void;
  remove: (widgetId: string) => void;
};

declare global {
  interface Window {
    turnstile?: TurnstileApi;
  }
}

const SITE_KEY = process.env.NEXT_PUBLIC_TURNSTILE_SITE_KEY;
const SCRIPT_URL = "https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit";
const TOKEN_TIMEOUT_MS = 30_000;

let scriptPromise: Promise<TurnstileApi> | null = null;

function loadTurnstile(): Promise<TurnstileApi> {
  if (window.turnstile) return Promise.resolve(window.turnstile);
  scriptPromise ??= new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = SCRIPT_URL;
    script.async = true;
    script.defer = true;
    script.onload = () => (window.turnstile ? resolve(window.turnstile) : reject(new Error("Turnstile missing")));
    script.onerror = () => {
      scriptPromise = null;
      reject(new Error("Could not load the verification script"));
    };
    document.head.appendChild(script);
  });
  return scriptPromise;
}

export function useTurnstile(action: "chat" | "contact"): {
  getToken: () => Promise<string | null>;
  slot: ReactNode;
  enabled: boolean;
} {
  const containerRef = useRef<HTMLDivElement>(null);
  const widgetRef = useRef<string | null>(null);
  const pendingRef = useRef<((token: string | null) => void) | null>(null);

  const settle = (token: string | null) => {
    pendingRef.current?.(token);
    pendingRef.current = null;
  };

  useEffect(() => {
    if (!SITE_KEY) return;
    let cancelled = false;
    loadTurnstile()
      .then((api) => {
        if (cancelled || !containerRef.current || widgetRef.current) return;
        widgetRef.current = api.render(containerRef.current, {
          sitekey: SITE_KEY,
          action,
          appearance: "interaction-only",
          execution: "execute",
          theme: "auto",
          callback: (token) => settle(token),
          "error-callback": () => settle(null),
          "expired-callback": () => settle(null),
        });
      })
      .catch(() => {
        /* getToken() resolves null; the server then explains that verification is needed */
      });
    return () => {
      cancelled = true;
      if (widgetRef.current && window.turnstile) window.turnstile.remove(widgetRef.current);
      widgetRef.current = null;
    };
  }, [action]);

  const getToken = useCallback(async (): Promise<string | null> => {
    if (!SITE_KEY) return null;
    try {
      const api = await loadTurnstile();
      // Wait briefly for the widget to finish rendering after the script loads.
      for (let i = 0; i < 20 && !widgetRef.current; i++) await new Promise((r) => setTimeout(r, 100));
      const widgetId = widgetRef.current;
      if (!widgetId) return null;
      settle(null); // cancel any earlier pending request
      return await new Promise<string | null>((resolve) => {
        const timer = setTimeout(() => settle(null), TOKEN_TIMEOUT_MS);
        pendingRef.current = (token) => {
          clearTimeout(timer);
          resolve(token);
        };
        api.reset(widgetId); // tokens are single-use
        api.execute(widgetId);
      });
    } catch {
      return null;
    }
  }, []);

  return {
    getToken,
    enabled: Boolean(SITE_KEY),
    slot: <div ref={containerRef} className="empty:hidden [&>div]:mx-auto" aria-live="polite" />,
  };
}
