/**
 * DTR-N Proxy — forwards /api/dtrn/* → Python FastAPI server on port 10000
 * Also rewrites HTML responses so their JS uses /api/dtrn as the API prefix.
 * Uses native Node 24 fetch (no extra deps needed).
 */
import { Router } from "express";
import type { Request, Response } from "express";

const router = Router();
const DTRN_BASE = "http://localhost:8000";

/**
 * Fetch a page/endpoint from the DTR-N Python server and forward the response.
 * For HTML responses we inject a tiny script that overrides API_BASE so the
 * page's fetch calls are re-routed through this proxy.
 */
async function proxyRequest(req: Request, res: Response, targetPath: string) {
  const qs = req.url.includes("?") ? req.url.slice(req.url.indexOf("?")) : "";
  const url = `${DTRN_BASE}${targetPath}${qs}`;

  try {
    const headers: Record<string, string> = {};
    if (req.headers["content-type"])
      headers["content-type"] = req.headers["content-type"] as string;
    if (req.headers["authorization"])
      headers["authorization"] = req.headers["authorization"] as string;
    if (req.headers["x-session-id"])
      headers["x-session-id"] = req.headers["x-session-id"] as string;

    const init: RequestInit = { method: req.method, headers };
    if (!["GET", "HEAD"].includes(req.method)) {
      headers["content-type"] = "application/json";
      init.body = JSON.stringify(req.body);
    }

    const upstream = await fetch(url, init);
    const ct = upstream.headers.get("content-type") ?? "application/json";
    res.status(upstream.status);
    res.setHeader("content-type", ct);

    if (ct.includes("text/html")) {
      let html = await upstream.text();
      // Rewrite empty API_BASE so JS fetches go through this proxy
      html = html
        .replace(
          /const\s+API_BASE\s*=\s*['"]['"]/g,
          `const API_BASE = '/api/dtrn'`
        )
        .replace(
          /const\s+API_BASE\s*=\s*['"]['"];/g,
          `const API_BASE = '/api/dtrn';`
        )
        .replace(
          /const API_BASE = '';/g,
          `const API_BASE = '/api/dtrn';`
        )
        .replace(
          /const API_BASE = "";/g,
          `const API_BASE = '/api/dtrn';`
        );
      res.send(html);
    } else if (ct.includes("application/json") || ct.includes("text/plain")) {
      const text = await upstream.text();
      res.send(text);
    } else {
      const buf = Buffer.from(await upstream.arrayBuffer());
      res.send(buf);
    }
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err);
    res
      .status(502)
      .json({ error: "DTR-N upstream unavailable", detail: msg });
  }
}

// ── HTML pages ───────────────────────────────────────────────────────────────
const HTML_PAGES: Record<string, string> = {
  "":                   "/",
  "dashboard":          "/dashboard",
  "login":              "/login",
  "parallel-build":     "/parallel-build",
  "thank-you-egypt":    "/thank-you-egypt",
  "app":                "/app",
  "session-dashboard":  "/session-dashboard",
};

for (const [slug, upstreamPath] of Object.entries(HTML_PAGES)) {
  router.get(`/dtrn${slug ? `/${slug}` : ""}`, (req, res) => {
    proxyRequest(req, res, upstreamPath);
  });
}

// ── All /api/* endpoints ──────────────────────────────────────────────────────
// Express 5 / path-to-regexp v8 returns wildcard captures as string[] joined by commas.
// We derive the sub-path directly from req.path (relative to the router mount point)
// to avoid any encoding/join ambiguity.
router.all("/dtrn/api/*path", (req, res) => {
  // req.path inside a sub-router mounted at /api is the path AFTER the mount prefix.
  // e.g. router mounted at /api, request at /api/dtrn/api/status → req.path = /dtrn/api/status
  const sub = req.path.replace(/^\/dtrn\/api\/?/, ""); // "status" or "workspace/files"
  proxyRequest(req, res, `/api/${sub}`);
});

// Convenience shortcut
router.get("/dtrn/status", (req, res) =>
  proxyRequest(req, res, "/api/parallel/status")
);

export default router;
