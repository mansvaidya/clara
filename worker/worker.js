// Cloudflare Worker for the CLARA persona site. Two routes:
//   POST /        -> Claude reads a persona description (ANTHROPIC_API_KEY)
//   POST /image   -> OpenAI draws a portrait for that persona (OPENAI_API_KEY)
// Both keys live here as secrets, never in the web page.

const CLAUDE_MODEL = "claude-sonnet-5-5";
const IMAGE_MODEL = "gpt-image-2";
const IMAGE_QUALITY = "medium"; // "low" is cheaper and faster, "high" is sharper and slower
const MAX_PROMPT_CHARS = 8000;

const SETTINGS = {
  kitchen: "at a kitchen table at home",
  living: "in a living room at home",
  porch: "on a front porch",
  garden: "in a backyard garden",
  center: "in a community center",
  library: "in a public library",
};
const GENDERS = { woman: "woman", man: "man", person: "person" };

// Keep free-text fields short and plain so the endpoint can only make portraits.
const clean = (v, max) =>
  String(v || "")
    .replace(/[^\p{L}\p{N} ,.'\-]/gu, " ")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, max);

function portraitPrompt(f) {
  const age = Math.min(100, Math.max(60, parseInt(f.age, 10) || 75));
  const gender = GENDERS[f.gender] || "person";
  const background = clean(f.background, 60);
  const details = clean(f.details, 120);
  const setting = SETTINGS[f.setting] || SETTINGS.living;
  return [
    `Editorial portrait photograph of a ${age}-year-old ${background ? background + " " : ""}${gender}${details ? ", " + details : ""}, ${setting}.`,
    "Head and shoulders, looking toward the camera with a calm, warm, dignified expression.",
    "Soft natural window light, shallow depth of field, softly blurred background, muted natural colors, realistic skin texture.",
    "Show an ordinary, capable older adult in everyday clothes. No signs of illness, distress, confusion or frailty, no medical equipment.",
    "No text, no logos, no watermark.",
  ].join(" ");
}

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
    const reply = (body, status = 200, type = "application/json") =>
      new Response(body, { status, headers: { ...cors, "content-type": type } });

    if (request.method === "OPTIONS") return new Response(null, { headers: cors });
    if (request.method !== "POST") return reply("Method not allowed", 405, "text/plain");
    if (!allowed.includes(origin)) return reply("Origin not allowed", 403, "text/plain");

    let body;
    try {
      body = await request.json();
    } catch {
      return reply("Bad JSON", 400, "text/plain");
    }

    const path = new URL(request.url).pathname.replace(/\/+$/, "");

    if (path === "/image") {
      if (!env.OPENAI_API_KEY) return reply("Image generation is not set up", 501, "text/plain");
      const upstream = await fetch("https://api.openai.com/v1/images/generations", {
        method: "POST",
        headers: { "content-type": "application/json", authorization: `Bearer ${env.OPENAI_API_KEY}` },
        body: JSON.stringify({
          model: IMAGE_MODEL,
          prompt: portraitPrompt(body || {}),
          size: "1024x1024",
          quality: IMAGE_QUALITY,
          output_format: "webp",
          output_compression: 80,
          n: 1,
        }),
      });
      if (!upstream.ok) return reply(JSON.stringify({ error: upstream.status }), upstream.status === 429 ? 429 : 502);
      const data = await upstream.json();
      const b64 = data?.data?.[0]?.b64_json;
      if (!b64) return reply(JSON.stringify({ error: "no_image" }), 502);
      return reply(JSON.stringify({ image: `data:image/webp;base64,${b64}` }));
    }

    if (path === "" || path === "/claude") {
      const prompt = String(body?.prompt || "");
      if (!prompt || prompt.length > MAX_PROMPT_CHARS) return reply("Prompt missing or too long", 400, "text/plain");
      const upstream = await fetch("https://api.anthropic.com/v1/messages", {
        method: "POST",
        headers: {
          "content-type": "application/json",
          "x-api-key": env.ANTHROPIC_API_KEY,
          "anthropic-version": "2023-06-01",
        },
        body: JSON.stringify({ model: CLAUDE_MODEL, max_tokens: 1400, messages: [{ role: "user", content: prompt }] }),
      });
      return new Response(upstream.body, { status: upstream.status, headers: { ...cors, "content-type": "application/json" } });
    }

    return reply("Not found", 404, "text/plain");
  },
};
