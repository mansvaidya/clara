# CLARA: Cognitive Persona Profiles

An interactive explorer of cognitive persona profiles for testing AI assistants with older adults. Every persona takes one level (Typical, Low or Lowest) on six dimensions: processing speed, working memory, executive function, episodic recall, language and attention. Of the 486 possible profiles, 207 pass the plausibility rules.

Visitors can also describe a person in one line, and Claude suggests plausible profiles to test. An optional button then draws an AI-generated portrait of that person with OpenAI's image API.

A **Try it** section plays the same automated prescription refill call for two simulated callers side by side: a typical Clara (T1) and Clara with a chosen profile (T2, T3 or T4). Each run samples real synthetic personas, and a bar compares outcomes across 2,000 simulated calls per profile. The simulation runs entirely in the browser and needs no API keys.

The site is password-protected. The page is encrypted, so its content cannot be read without the password, even from the page source.

## Files

| File | Purpose |
| --- | --- |
| `index.html` | The published site: a password prompt plus the encrypted page |
| `tools/encrypt.py` | Encrypts the page source into `index.html` |
| `src/site.html` | The unencrypted page source. Kept out of the repository by `.gitignore` and stored separately |
| `worker/worker.js` | A small Cloudflare Worker that holds the Anthropic and OpenAI API keys and forwards requests to Claude and to the image API |
| `worker/wrangler.toml` | Worker settings, including which site may call it |
| `.github/workflows/deploy-worker.yml` | Deploys the Worker from GitHub, reading the key from the repository's secrets |

## 1. Publishing the page with GitHub Pages

1. Push this folder to a GitHub repository.
2. In the repository, open **Settings → Pages**, set the source to **Deploy from a branch**, branch `main`, folder `/ (root)`.
3. The site is published at `https://USERNAME.github.io/REPO-NAME/`.

The page works on its own at this point. Without the Worker, the describe box falls back to a simple keyword match.

## 2. Password protection

The password is set when `index.html` is built. To change the page or the password:

1. Place the unencrypted source at `src/site.html` and make the edits there.
2. Run `pip install cryptography`, then `python tools/encrypt.py NEW-PASSWORD`.
3. Commit and push the new `index.html`.

`src/site.html` must never be uploaded to the repository: anyone could read the site from it without the password. `.gitignore` excludes it from git pushes, but files dragged into the GitHub web uploader are not filtered, so upload only `index.html` that way.

A short password such as a single word can be guessed by someone who downloads the page and tries many passwords. The page holds no personal data, so this level of protection keeps casual visitors out, but a longer password is stronger.

After the correct password is entered, the browser tab remembers it until the tab is closed.

## 3. Connecting Claude and portraits (optional)

GitHub Pages serves only static files, so it cannot keep a secret. An API key written into `index.html` would be readable by anyone viewing the page source. The Worker keeps the keys on the server side instead, and GitHub Actions deploys it using the repository's secrets.

1. Create a free Cloudflare account. Note the **Account ID** (on the Workers & Pages overview page), and create an **API token** from the "Edit Cloudflare Workers" template.
2. In the GitHub repository, open **Settings → Secrets and variables → Actions** and add four secrets:
   - `ANTHROPIC_API_KEY`: the Anthropic API key
   - `OPENAI_API_KEY`: the OpenAI API key, for portraits (leave it out to turn portraits off)
   - `CLOUDFLARE_API_TOKEN`: the token from step 1
   - `CLOUDFLARE_ACCOUNT_ID`: the account ID from step 1
3. In `worker/wrangler.toml`, set `ALLOWED_ORIGIN` to the site's address, for example `https://USERNAME.github.io`. Only that site can use the Worker.
4. Push the changes. The **Deploy API proxy** action runs and prints the Worker's address, for example `https://clara-persona-proxy.SUBDOMAIN.workers.dev`.
5. In `src/site.html`, set `const PROXY_URL = "https://clara-persona-proxy.SUBDOMAIN.workers.dev";`, rebuild `index.html` with `tools/encrypt.py` (section 2), and push again.

Every description submitted through the page uses credits from the linked Anthropic account, and every portrait uses credits from the OpenAI account. The Worker accepts requests only from the site's address and caps the prompt length, but anyone with the site password can still use it. Spending limits in the Anthropic Console and the OpenAI dashboard are recommended.

## Portraits

Portraits are made only when a visitor clicks **Show a portrait**, never automatically. Each one takes 10 to 40 seconds.

- **What the image shows.** Claude describes the person's appearance (age, gender, background, setting, hair, glasses, clothing). The cognitive levels are never sent to the image API, so portraits don't depict impairment.
- **Fixed prompt.** The Worker writes the image prompt itself from those few fields, in one fixed editorial-photo style. It cannot be used to make other kinds of images.
- **Balance.** When a description doesn't give a gender or background, the page picks one at random from a balanced list, rather than leaving it to the image model's defaults.
- **Labelling.** Every portrait is labelled "AI-generated image. Not a real person."

## Changing the models

The Worker uses `claude-sonnet-5-5` for Claude and `gpt-image-2` at `medium` quality for portraits. To change them, edit `CLAUDE_MODEL`, `IMAGE_MODEL` and `IMAGE_QUALITY` at the top of `worker/worker.js`. `low` quality is cheaper and faster; `high` is sharper and slower.
