// Cloudflare Worker that forwards persona descriptions to Claude.
// The Anthropic API key lives here as a secret (ANTHROPIC_API_KEY), never in the web page.

const MODEL = "claude-sonnet-5-5";
const MAX_PROMPT_CHARS = 8000;

export default {
  async fetch(request, env) {
    const origin = request.headers.get("Origin") || "";
    const allowed = (env.ALLOWED_ORIGIN || "").split(",").map((s) => s.trim()).filter(Boolean);
    const cors = {
      "Access-Control-Allow-Origin": allowed.includes(origin) ? origin : allowed[0] || "",
      "Access-Control-Allow-Methods": "POST, OPTIONS",
      "Access-Control-Allow-Headers": "content-type",
      Vary: "Origin",
    };

    if (request.method === "OPTIONS") return new Response(null, { headers: cors });
    if (request.method !== "POST") return new Response("Method not allowed", { status: 405, headers: cors });
    if (!allowed.includes(origin)) return new Response("Origin not allowed", { status: 403, headers: cors });

    let body;
    try {
      body = await request.json();
    } catch {
      return new Response("Bad JSON", { status: 400, headers: cors });
    }
    const prompt = String(body?.prompt || "");
    if (!prompt || prompt.length > MAX_PROMPT_CHARS) {
      return new Response("Prompt missing or too long", { status: 400, headers: cors });
    }

    const upstream = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: {
        "content-type": "application/json",
        "x-api-key": env.ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
      },
      body: JSON.stringify({
        model: MODEL,
        max_tokens: 1200,
        messages: [{ role: "user", content: prompt }],
      }),
    });

    return new Response(upstream.body, {
      status: upstream.status,
      headers: { ...cors, "content-type": "application/json" },
    });
  },
};
