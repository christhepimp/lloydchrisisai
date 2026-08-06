# armsx2-lloyd

Bridge notes for **Lloyd** ↔ **[ARMSX2](https://github.com/ARMSX2/ARMSX2)**.

- Core: `lloyd/emu_bridge.py`
- HTTP: `server.py` → `/emu/*`
- Docs: `docs/ARMSX2.md`, **`docs/ARMSX2_APK.md`** (APK + API settings)
- Stub: `host_stub.py`

## Do not vendor ARMSX2 here

```bash
git clone --depth 1 https://github.com/ARMSX2/ARMSX2.git
```

Build per upstream. Lloyd only needs the HTTP bridge.

## APK

The **Lloyd Capacitor APK** embeds the PS2 API settings UI (session, game, goal, play, learn).  
Install stock ARMSX2 separately. See `docs/ARMSX2_APK.md`.

## Host stub

```bash
python armsx2-lloyd/host_stub.py
# or with a caption:
python armsx2-lloyd/host_stub.py menu arcade mode highlighted
```
