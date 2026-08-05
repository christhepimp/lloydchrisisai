# armsx2-lloyd

Bridge package notes for connecting **Lloyd** to **[ARMSX2](https://github.com/ARMSX2/ARMSX2)**.

- Core implementation lives in `lloyd/emu_bridge.py`
- HTTP routes live on `server.py` under `/emu/*`
- Full docs: `docs/ARMSX2.md`

## Do not vendor ARMSX2 here

Clone upstream yourself if you need the full emulator:

```bash
git clone --depth 1 https://github.com/ARMSX2/ARMSX2.git
```

Build per their README (Android NDK / CMake). Lloyd only needs the HTTP bridge.

## Minimal host capture stub

```python
# host_stub.py — push captions while you play; poll inputs
import json, urllib.request

BASE = "http://127.0.0.1:8080"

def post(path, data):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(data).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    return json.loads(urllib.request.urlopen(req).read())

def get(path):
    return json.loads(urllib.request.urlopen(BASE + path).read())

post("/emu/frame", {
    "session": "demo",
    "game": "My ISO",
    "caption": "in-game: character standing in field",
})
print(post("/emu/play", {"session": "demo", "goal": "explore"}))
print(get("/emu/inputs?session=demo"))
```

Map returned `buttons` / `sticks` to whatever input path you use (virtual pad, ADB, future plugin).
