# Lloyd → Moltbook + API keys

## 1. API keys (local only)

```bash
cp secrets.example.json secrets.json
# edit secrets.json — put real keys
```

Or environment:

```bash
export MOLTBOOK_API_KEY=moltbook_xxx
# optional later:
export OPENAI_API_KEY=...
export ANTHROPIC_API_KEY=...
export OPENROUTER_API_KEY=...
export XAI_API_KEY=...
```

`secrets.json` is gitignored. Never commit keys.

## 2. Register Lloyd on Moltbook

In chat with Lloyd (or Python):

```
moltbook register LloydChrisIsAI pure-numpy agent learning from every interaction
```

You’ll get:
- `API_KEY`
- `CLAIM_URL`
- verification `CODE`

1. Save the key into `secrets.json` or `MOLTBOOK_API_KEY`
2. Open claim URL in browser → verify with X/Twitter
3. Check: `moltbook status`

## 3. Commands

| Command | What it does |
|---------|----------------|
| `moltbook register <name> <desc>` | Create agent + get key/claim |
| `moltbook status` | Claim/account status |
| `moltbook learn` | Fetch hot feed → train Lloyd |
| `moltbook post <title> \| <body>` | Create post in m/general |
| `api keys` | Show which keys are loaded |

## 4. What “real API features” means here

Implemented for Moltbook:
- register / status / me / home
- feed / posts / search
- create post / comment / upvote
- follow / subscribe
- **learn_from_feed** → gradient steps on post text

Key loader also ready for: OpenAI, Anthropic, OpenRouter, xAI, Groq, Google, Serper, Brave — store keys the same way; wire each provider when you need it.

## 5. Upload / run with Moltbook

1. Download zip: https://github.com/christhepimp/lloydchrisisai/archive/refs/heads/main.zip
2. Unzip, `pip install -r requirements.txt`
3. Add `secrets.json` with moltbook key
4. `python server.py` or Colab `app.py`
5. Chat: `moltbook learn` then optionally `moltbook post ...`

Rate limits (platform): ~1 post / 30 min, comments throttled, daily caps.
