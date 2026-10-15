# CLARA Persona Space

An interactive explorer of cognitive persona profiles for testing AI assistants with older adults. Every persona takes one level (Typical, Low or Lowest) on six dimensions: processing speed, working memory, executive function, episodic recall, language and attention. Of the 486 possible profiles, 207 pass the plausibility rules.

You can also describe a person in one line, and Claude suggests plausible profiles to test.

## Files

| File | What it is |
| --- | --- |
| `index.html` | The whole site, one self-contained page |
| `worker/worker.js` | A small Cloudflare Worker that holds your Anthropic API key and forwards requests to Claude |
| `worker/wrangler.toml` | Worker settings, including which site may call it |
| `.github/workflows/deploy-worker.yml` | Deploys the Worker from GitHub, reading the key from your GitHub secrets |

## 1. Publish the page with GitHub Pages

1. Push this folder to a GitHub repository.
2. In the repository, open **Settings → Pages**, set the source to **Deploy from a branch**, branch `main`, folder `/ (root)`.
3. The site appears at `https://YOUR-USERNAME.github.io/REPO-NAME/`.

The page works on its own at this point. Without the Worker, the describe box uses a simple keyword match.

## 2. Connect Claude (optional)

GitHub Pages only serves static files, so it can't keep a secret. If the API key were written into `index.html`, anyone could read it from the page source. The Worker keeps the key on the server side instead, and GitHub Actions deploys it using your GitHub secrets.

1. Create a free Cloudflare account. Note your **Account ID** (on the Workers & Pages overview page), and create an **API token** with the "Edit Cloudflare Workers" template.
2. In the GitHub repository, open **Settings → Secrets and variables → Actions** and add three secrets:
   - `ANTHROPIC_API_KEY`: your Anthropic API key
   - `CLOUDFLARE_API_TOKEN`: the token from step 1
   - `CLOUDFLARE_ACCOUNT_ID`: the account ID from step 1
3. In `worker/wrangler.toml`, set `ALLOWED_ORIGIN` to `https://YOUR-USERNAME.github.io`. Only this site will be able to use the Worker.
4. Push. The **Deploy Claude proxy** action runs and prints the Worker's address, for example `https://clara-persona-proxy.YOUR-SUBDOMAIN.workers.dev`.
5. In `index.html`, set `const CLAUDE_PROXY_URL = "https://clara-persona-proxy.YOUR-SUBDOMAIN.workers.dev";` and push again.

Every description sent through the page uses your Anthropic API credits. The Worker only accepts requests from your site's address and caps the prompt length, but anyone who can open your site can still use it. Set a spending limit in the Anthropic Console.

## Changing the model

The Worker uses `claude-sonnet-5-5`. Change `MODEL` in `worker/worker.js` to use another one.
