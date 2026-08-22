export interface Env {
  ORIGIN_URL: string;
}

const HOP_BY_HOP_HEADERS = new Set([
  "connection",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailer",
  "transfer-encoding",
  "upgrade",
]);

function buildOriginUrl(request: Request, origin: string): URL {
  const incoming = new URL(request.url);
  const base = new URL(origin.endsWith("/") ? origin : `${origin}/`);
  base.pathname = incoming.pathname;
  base.search = incoming.search;
  return base;
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const originUrl = buildOriginUrl(request, env.ORIGIN_URL);

    // Preserve the original method, headers and body so Stripe webhooks and
    // other POST endpoints continue to receive the exact request payload.
    const upstreamRequest = new Request(originUrl.toString(), request);
    upstreamRequest.headers.set("X-Forwarded-Host", new URL(request.url).host);
    upstreamRequest.headers.set("X-Praetor-Edge", "cloudflare-worker");

    try {
      const upstream = await fetch(upstreamRequest, {
        redirect: "manual",
      });

      const headers = new Headers(upstream.headers);
      for (const header of HOP_BY_HOP_HEADERS) {
        headers.delete(header);
      }

      headers.set("X-Content-Type-Options", "nosniff");
      headers.set("Referrer-Policy", "strict-origin-when-cross-origin");
      headers.set("X-Frame-Options", "DENY");
      headers.set("Permissions-Policy", "camera=(), microphone=(), geolocation=()");

      return new Response(upstream.body, {
        status: upstream.status,
        statusText: upstream.statusText,
        headers,
      });
    } catch (error) {
      console.error("PRAETOR origin request failed", {
        error: error instanceof Error ? error.message : String(error),
        path: new URL(request.url).pathname,
      });

      return Response.json(
        {
          error: "PRAETOR origin unavailable",
          status: "bad_gateway",
        },
        { status: 502 },
      );
    }
  },
};
