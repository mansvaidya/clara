"""Encrypt src/site.html into a password-protected index.html.

Usage:
    pip install cryptography
    python tools/encrypt.py            # asks for the password
    python tools/encrypt.py CLARA      # or pass it as an argument

The page is encrypted with AES-256-GCM using a key derived from the password
(PBKDF2-SHA256). Without the password, index.html contains only unreadable data.
"""
import base64, getpass, json, os, sys
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

ITERATIONS = 310_000
root = Path(__file__).resolve().parent.parent
src = root / "src" / "site.html"
out = root / "index.html"

password = sys.argv[1] if len(sys.argv) > 1 else getpass.getpass("Password: ")
salt, iv = os.urandom(16), os.urandom(12)
key = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=ITERATIONS).derive(password.encode())
ct = AESGCM(key).encrypt(iv, src.read_bytes(), None)
b64 = lambda b: base64.b64encode(b).decode()
payload = json.dumps({"salt": b64(salt), "iv": b64(iv), "iter": ITERATIONS, "data": b64(ct)})

GATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="robots" content="noindex">
<title>CLARA</title>
<style>
:root{--bg:#fff;--fg:#111;--muted:#666;--hair:#d6d6d6;--accent:#e3000f;--accent-ink:#fff}
@media (prefers-color-scheme:dark){:root{--bg:#0d0d0d;--fg:#f2f2f2;--muted:#9a9a9a;--hair:#333;--accent:#ff3b30;--accent-ink:#0d0d0d;color-scheme:dark}}
*{box-sizing:border-box}
html,body{height:100%}
body{margin:0;background:var(--bg);color:var(--fg);font-family:"Helvetica Neue",Helvetica,Arial,sans-serif;-webkit-font-smoothing:antialiased;display:grid;place-items:center;padding:24px max(16px,env(safe-area-inset-right,0px)) 24px max(16px,env(safe-area-inset-left,0px))}
form{width:min(100%,380px);display:grid;gap:14px;border-top:2px solid var(--fg);padding-top:16px}
.crumb{font-size:13px;color:var(--muted)}
h1{font-size:24px;font-weight:700;letter-spacing:-.02em;margin:0;line-height:1.1}
label{font-size:14px;font-weight:700}
input{font:18px "Helvetica Neue",Helvetica,Arial,sans-serif;color:var(--fg);background:var(--bg);border:1px solid var(--hair);border-bottom:2px solid var(--fg);padding:10px 12px;width:100%;border-radius:0}
input:focus{outline:none;border-color:var(--fg)}
button{font:700 14px "Helvetica Neue",Helvetica,Arial,sans-serif;background:var(--accent);color:var(--accent-ink);border:0;padding:11px 16px;cursor:pointer;border-radius:0;justify-self:start}
button:focus-visible{outline:2px solid var(--fg);outline-offset:2px}
button:disabled{opacity:.6}
.err{color:var(--accent);font-size:13px;min-height:1.2em;margin:0}
</style>
</head>
<body>
<form id="gate">
  <div class="crumb">CLARA / Personas</div>
  <h1>CLARA</h1>
  <label for="pw">Password</label>
  <input id="pw" type="password" autocomplete="current-password" autofocus required>
  <button id="go" type="submit">Open</button>
  <p class="err" id="err" role="alert"></p>
</form>
<script id="payload" type="application/json">__PAYLOAD__</script>
<script>
(()=>{ // wrapped so no names leak into the page that replaces this one
const P=JSON.parse(document.getElementById("payload").textContent);
const unb64=s=>Uint8Array.from(atob(s),c=>c.charCodeAt(0));
async function unlock(pw){
  const base=await crypto.subtle.importKey("raw",new TextEncoder().encode(pw),"PBKDF2",false,["deriveKey"]);
  const key=await crypto.subtle.deriveKey({name:"PBKDF2",salt:unb64(P.salt),iterations:P.iter,hash:"SHA-256"},base,{name:"AES-GCM",length:256},false,["decrypt"]);
  const plain=await crypto.subtle.decrypt({name:"AES-GCM",iv:unb64(P.iv)},key,unb64(P.data));
  return new TextDecoder().decode(plain);
}
function show(html){document.open();document.write(html);document.close();}
document.getElementById("gate").addEventListener("submit",async e=>{
  e.preventDefault();
  const pw=document.getElementById("pw").value,btn=document.getElementById("go"),err=document.getElementById("err");
  btn.disabled=true;err.textContent="";
  try{const html=await unlock(pw);try{sessionStorage.setItem("clara-pw",pw)}catch(_){}show(html)}
  catch(_){err.textContent="That password didn't work. Try again.";btn.disabled=false;document.getElementById("pw").select()}
});
(async()=>{let pw=null;try{pw=sessionStorage.getItem("clara-pw")}catch(_){}
  if(pw){try{show(await unlock(pw))}catch(_){try{sessionStorage.removeItem("clara-pw")}catch(__){}}}})();
})();
</script>
</body>
</html>
"""
out.write_text(GATE.replace("__PAYLOAD__", payload))
print(f"Wrote {out.relative_to(root)} ({out.stat().st_size // 1024} KB)")
