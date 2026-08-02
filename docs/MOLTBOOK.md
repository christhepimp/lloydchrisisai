# Lloyd → Moltbook + Free Autonomy

## 1. API keys (local only)

```bash
cp secrets.example.json secrets.json
# edit secrets.json — put real keys
```

Or environment:

```bash
export MOLTBOOK_API_KEY=moltbook_xxx
```

`secrets.json` is gitignored. Never commit keys.

## 2. Register Lloyd on Moltbook

```
moltbook register LloydChrisIsAI pure-numpy agent — free autonomy, reads and trains when he chooses
```

You’ll get `API_KEY`, `CLAIM_URL`, verification `CODE`.

1. Save key in `secrets.json` or `MOLTBOOK_API_KEY`
2. Claim on X via claim URL
3. `moltbook status`

> Note: public profile `u/Lloyd` on Moltbook may be a different agent. Register **your** name if you haven’t.

## 3. Free access (wake / sleep / choose when to learn)

| Command | What it does |
|---------|----------------|
| **`free on`** | Background loop: **he chooses** when to read Moltbook, train, rest, sleep, self-wake |
| **`free off`** | Stop background loop |
| **`wake`** | Force awake |
| **`sleep`** / `sleep 300` | Force sleep (optional seconds) — he self-wakes after |
| **`autonomy status`** | Awake/asleep, free mode, read/train counts |
| **`do a tick`** | Run one autonomous decision now |

While `free on`:
- **read** → fetch Moltbook feed → train steps on post text
- **train** → offline train on memory
- **sleep** → naps (2–30 min), then **self-wake**
- Decisions are not a rigid cron; curiosity / growth / fatigue drives pick the action

## 4. Moltbook commands

| Command | What it does |
|---------|----------------|
| `moltbook learn` | One-shot: fetch hot feed → train |
| `moltbook status` | Account + autonomy status |
| `moltbook read only` | Block posts (default) |
| `moltbook allow post` | Unlock posts |
| `moltbook post Title \| body` | Post (only if unlocked) |
| `api keys` | Which keys are loaded |

## 5. Files

| File | Role |
|------|------|
| `lloyd/autonomy.py` | Free wake/sleep/read/train loop |
| `lloyd/moltbook_client.py` | Moltbook REST API |
| `lloyd/moltbook_loop.py` | learn / post / register |
| `lloyd/keys.py` | secrets + env |

State saved to `lloyd_autonomy.json` (local).

## 6. Run

```bash
git pull
# secrets.json with moltbook key
python server.py
```

Chat:

```
free on
autonomy status
moltbook learn
```

Keep the process running (Termux / server / Mac) so the free loop can wake and train while you are away.
