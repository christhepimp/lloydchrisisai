# Download Lloyd as a ZIP

All project files stay as they are on `main`. GitHub builds a full source zip automatically.

## Full project ZIP (recommended)

**Download everything (current `main` branch):**

→ **[lloydchrisisai-main.zip](https://github.com/christhepimp/lloydchrisisai/archive/refs/heads/main.zip)**

Same archive via API zipball:

→ [api.github.com zipball/main](https://api.github.com/repos/christhepimp/lloydchrisisai/zipball/main)

## From the GitHub website

1. Open [christhepimp/lloydchrisisai](https://github.com/christhepimp/lloydchrisisai)
2. Click the green **Code** button
3. Choose **Download ZIP**

## After download

```bash
unzip lloydchrisisai-main.zip
cd lloydchrisisai-main
pip install -r requirements.txt
python server.py
```

Or on Termux:

```bash
cd ~
curl -L -o lloyd.zip https://github.com/christhepimp/lloydchrisisai/archive/refs/heads/main.zip
unzip lloyd.zip
cd lloydchrisisai-main
python server.py
```

No source files were removed or rewritten for this — the zip is a snapshot of the whole repo.
