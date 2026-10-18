// Cloudflare Worker for the CLARA persona site. Three routes:
//   POST /        -> Claude reads a persona description (ANTHROPIC_API_KEY)
//   POST /image   -> OpenAI draws a portrait for that persona (OPENAI_API_KEY, optional)
//   POST /tts     -> ElevenLabs speaks one line of a simulated call (ELEVENLABS_API_KEY, optional)
// The keys live here as secrets, never in the web page.

const CLAUDE_MODEL = "claude-sonnet-5-5";
const IMAGE_MODEL = "gpt-image-2";
const IMAGE_QUALITY = "medium"; // "low" is cheaper and faster, "high" is sharper and slower
const MAX_PROMPT_CHARS = 8000;

// ElevenLabs voices. The page only ever sends one of these names, never a voice ID, so the
// endpoint can only speak call lines in these voices. Override any ID in wrangler.toml [vars].
// "fallback" IDs are ElevenLabs default voices, used if a Voice Library voice isn't available
// on your plan (Voice Library voices need a paid plan for API use).
const VOICES = {
  line:        { env: "VOICE_LINE",        id: "EXAVITQu4vr4xnSDxMaL", speed: 1.0,  note: "pharmacy line: calm, clear American female (default voice)" },
  staff:       { env: "VOICE_STAFF",       id: "iP95p4xoKVk53GoZ742B", speed: 1.0,  note: "pharmacy staff member: warm American male (default voice)" },
  younger:     { env: "VOICE_YOUNGER",     id: "cgSgspJ2msm6clMCkdW9", speed: 1.05, note: "the 35-year-old caller: natural young American female (default voice)" },
  older_woman: { env: "VOICE_OLDER_WOMAN", id: "wGcFBfKz5yUQqhqr0mVy", fallback: "ThT5KcBeYPX3keUQqHPh", speed: 0.9, note: "older woman (Maria Moody)" },
  older_man:   { env: "VOICE_OLDER_MAN",   id: "0lp4RIz96WD1RUtvEu3Q", fallback: "pqHfZKP75CvOlQylNhV4", speed: 0.9, note: "older man (Grandfather Joe)" },
};
const TTS_MODEL_DEFAULT = "eleven_flash_v2_5"; // fast and cheaper per character; set TTS_MODEL to "eleven_v4_turbo" for richer voices
const MAX_TTS_CHARS = 800;

async function sha256(text) {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

async function speak(env, voiceName, text) {
  const v = VOICES[voiceName];
  const model = env.TTS_MODEL || TTS_MODEL_DEFAULT;
  const wanted = (env[v.env] || v.id).trim();
  const ids = [wanted, v.fallback].filter(Boolean);
  const cache = caches.default;
  // The key names the voice actually wanted; audio from a fallback voice is never stored under it,
  // so once the wanted voice works it is used straight away.
  const key = new Request("https://tts-cache.clara/v2/" + (await sha256([voiceName, wanted, model, v.speed, text].join("|"))));
  const hit = await cache.match(key);
  if (hit) return hit;
  let last, used, note = "";
  for (const id of ids) {
    used = id;
    last = await fetch(`https://api.elevenlabs.io/v1/text-to-speech/${id}?output_format=mp3_44100_64`, {
      method: "POST",
      headers: { "content-type": "application/json", "xi-api-key": env.ELEVENLABS_API_KEY, accept: "audio/mpeg" },
      body: JSON.stringify({ text, model_id: model, voice_settings: { stability: 0.5, similarity_boost: 0.75, speed: v.speed } }),
    });
    if (last.ok) break;
    if (id === wanted) {
      // Keep ElevenLabs' reason so the page can show why the wanted voice wasn't used.
      let detail = "";
      try { const j = await last.clone().json(); detail = j?.detail?.status || j?.detail?.message || j?.detail || ""; } catch {}
      note = `${wanted} refused (${last.status}${detail ? ": " + String(detail).slice(0, 120) : ""})`;
    }
  }
  if (!last.ok) { const r = new Response(null, { status: last.status }); r.note = note; return r; }
  const audio = new Response(await last.arrayBuffer(), {
    headers: { "content-type": "audio/mpeg", "cache-control": "public, max-age=2592000", "x-voice-id": used, "x-voice-note": note.replace(/[^\x20-\x7E]/g, " ") },
  });
  if (used === wanted) await cache.put(key, audio.clone()); // the same line in the same voice is only paid for once
  return audio;
}

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

    if (path === "/tts") {
      if (!env.ELEVENLABS_API_KEY) return reply("Voices are not set up", 501, "text/plain");
      const voice = String(body?.voice || "");
      const text = String(body?.text || "").trim();
      if (!VOICES[voice]) return reply("Unknown voice", 400, "text/plain");
      if (!text || text.length > MAX_TTS_CHARS) return reply("Text missing or too long", 400, "text/plain");
      const audio = await speak(env, voice, text);
      if (!audio.ok) return reply(JSON.stringify({ error: audio.status }), audio.status === 429 ? 429 : 502);
      return new Response(audio.body, { headers: { ...cors, "content-type": "audio/mpeg", "x-voice-id": audio.headers.get("x-voice-id") || "", "x-voice-note": audio.headers.get("x-voice-note") || "", "Access-Control-Expose-Headers": "x-voice-id, x-voice-note" } });
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
