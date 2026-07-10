"use client";

export type AppLanguage = "en" | "zh";

export const ACTIVE_SESSION_STORAGE_KEY = "deeptutor.activeSessionId.tab";
export const LANGUAGE_STORAGE_KEY = "deeptutor-language";
export const SIDEBAR_COLLAPSED_STORAGE_KEY = "deeptutor.sidebarCollapsed";
export const CHAT_RESPONSE_TIMEOUT_STORAGE_KEY =
  "deeptutor.chatResponseTimeout";

/** Tenant id from `/u/<tenant>/...` public path (path-mode multi-tenant). */
export function tenantIdFromPathname(
  pathname: string | null | undefined,
): string | null {
  if (!pathname) return null;
  const m = pathname.match(/^\/u\/([^/]+)/);
  return m?.[1] || null;
}

/** Scope sessionStorage keys so admin switching tenants cannot reuse session ids. */
export function activeSessionStorageKey(
  pathname?: string | null,
): string {
  const path =
    pathname ??
    (typeof window !== "undefined" ? window.location.pathname : "");
  const tenant = tenantIdFromPathname(path);
  return tenant
    ? `${ACTIVE_SESSION_STORAGE_KEY}.${tenant}`
    : ACTIVE_SESSION_STORAGE_KEY;
}

// Mirror of the per-user ``chat_response_timeout`` UI preference. Cached in
// localStorage so the chat watchdog (a separate provider from Settings) can
// read it synchronously without its own fetch. Kept in sync on settings load.
export const DEFAULT_CHAT_RESPONSE_TIMEOUT_SECONDS = 180;
export const MIN_CHAT_RESPONSE_TIMEOUT_SECONDS = 30;
export const MAX_CHAT_RESPONSE_TIMEOUT_SECONDS = 1800;

export function clampChatResponseTimeout(seconds: number): number {
  if (!Number.isFinite(seconds)) return DEFAULT_CHAT_RESPONSE_TIMEOUT_SECONDS;
  return Math.min(
    MAX_CHAT_RESPONSE_TIMEOUT_SECONDS,
    Math.max(MIN_CHAT_RESPONSE_TIMEOUT_SECONDS, Math.round(seconds)),
  );
}

export function readStoredChatResponseTimeout(): number {
  if (typeof window === "undefined")
    return DEFAULT_CHAT_RESPONSE_TIMEOUT_SECONDS;
  try {
    const raw = window.localStorage.getItem(CHAT_RESPONSE_TIMEOUT_STORAGE_KEY);
    const parsed = raw ? Number.parseInt(raw, 10) : NaN;
    return Number.isFinite(parsed) && parsed > 0
      ? clampChatResponseTimeout(parsed)
      : DEFAULT_CHAT_RESPONSE_TIMEOUT_SECONDS;
  } catch {
    return DEFAULT_CHAT_RESPONSE_TIMEOUT_SECONDS;
  }
}

export function writeStoredChatResponseTimeout(seconds: number): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(
      CHAT_RESPONSE_TIMEOUT_STORAGE_KEY,
      String(clampChatResponseTimeout(seconds)),
    );
  } catch {
    // localStorage may be unavailable
  }
}

export const ACTIVE_SESSION_EVENT = "deeptutor:active-session";
export const LANGUAGE_EVENT = "deeptutor:language";
export const SIDEBAR_COLLAPSED_EVENT = "deeptutor:sidebar-collapsed";

export function normalizeLanguage(
  value: string | null | undefined,
): AppLanguage {
  return value === "zh" ? "zh" : "en";
}

export function readStoredLanguage(): AppLanguage {
  if (typeof window === "undefined") return "en";
  try {
    return normalizeLanguage(window.localStorage.getItem(LANGUAGE_STORAGE_KEY));
  } catch {
    return "en";
  }
}

export function writeStoredLanguage(language: AppLanguage): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(LANGUAGE_STORAGE_KEY, language);
    window.dispatchEvent(
      new CustomEvent(LANGUAGE_EVENT, {
        detail: { language },
      }),
    );
  } catch {
    // localStorage may be unavailable
  }
}

export function readStoredActiveSessionId(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.sessionStorage.getItem(activeSessionStorageKey());
  } catch {
    return null;
  }
}

export function writeStoredActiveSessionId(sessionId: string | null): void {
  if (typeof window === "undefined") return;
  try {
    const key = activeSessionStorageKey();
    if (sessionId) {
      window.sessionStorage.setItem(key, sessionId);
    } else {
      window.sessionStorage.removeItem(key);
    }
    window.dispatchEvent(
      new CustomEvent(ACTIVE_SESSION_EVENT, {
        detail: { sessionId },
      }),
    );
  } catch {
    // sessionStorage may be unavailable
  }
}

export function readStoredSidebarCollapsed(): boolean {
  if (typeof window === "undefined") return false;
  try {
    return window.localStorage.getItem(SIDEBAR_COLLAPSED_STORAGE_KEY) === "1";
  } catch {
    return false;
  }
}

export function writeStoredSidebarCollapsed(collapsed: boolean): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(
      SIDEBAR_COLLAPSED_STORAGE_KEY,
      collapsed ? "1" : "0",
    );
    window.dispatchEvent(
      new CustomEvent(SIDEBAR_COLLAPSED_EVENT, {
        detail: { collapsed },
      }),
    );
  } catch {
    // localStorage may be unavailable
  }
}
