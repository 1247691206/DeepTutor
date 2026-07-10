import { tenantIdFromPathname } from "@/context/app-shell-storage";

const OXCA_LEGACY_BASE = "/__OXCA_BASE_PATH__";

/**
 * Build a public asset URL that works in both:
 * - path-mode multi-tenant routes: /u/<tenant>/...
 * - plain/root routes: /...
 */
export function publicAssetPath(
  path: string,
  pathname?: string | null,
): string {
  const normalized = path.startsWith("/") ? path : `/${path}`;
  const currentPathname =
    pathname ??
    (typeof window !== "undefined" ? window.location.pathname : null);
  const tenantId = tenantIdFromPathname(currentPathname);
  // In path-mode deployments, static assets are reliably served via the
  // build-time Next basePath proxy lane.
  return tenantId ? `${OXCA_LEGACY_BASE}${normalized}` : normalized;
}
