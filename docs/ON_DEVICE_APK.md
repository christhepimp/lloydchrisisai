# Full Lloyd inside the APK (train on the phone)

You want the **complete** brain running on the device so training actually happens on the phone, and you can still export him later.

## Recommended path: Chaquopy (Python inside Android)

Chaquopy embeds CPython + NumPy inside an Android app. The existing `lloyd/` + `model/` packages run unchanged.

### High-level architecture

```
Android APK
├── WebView  →  existing mobile_web UI
└── Local Python (Chaquopy)
      ├── starts a tiny HTTP server on 127.0.0.1
      ├── runs the exact same server.py / flask logic
      └── full TinyTransformer + trainer + memory
```

Training, chat, export, import all work offline on the phone.

### Steps (on a machine with Android Studio)

1. Create a new Android project (Empty Activity) or use Capacitor + Chaquopy plugin.
2. Add Chaquopy to `build.gradle` (see https://chaquo.com/chaquopy/).
3. Put the whole Lloyd repo under `src/main/python/` (or symlink `lloyd/`, `model/`, etc.).
4. In Python startup code, launch the same handler that `server.py` uses, bound to `127.0.0.1:8765`.
5. Point the WebView at `http://127.0.0.1:8765`.
6. Request storage permissions so the user can pick `.txt` training files and save the exported `.lloyd`.

Because the brain is pure NumPy, no extra native libs beyond what Chaquopy already ships for NumPy are required.

### Alternative: BeeWare / Briefcase

```bash
pip install briefcase
# then follow BeeWare Android tutorial, pointing at this repo as the Python app
```

You get a pure-Python APK. You would replace the HTML UI with a Toga (or other) native UI that calls `Lloyd` and `LloydTrainer` directly. Same brain code.

### Why this works for transfer later

- After training on the phone, hit **Export** → you get a `.lloyd` file.
- That file contains the exact neural weights + memory.
- Copy it to a server / laptop / another phone and **Import**.
- The same `lloyd/` + `model/` code loads it. No conversion needed.

## Current status in this repo

- Brain is fully serializable (`save` / `load` / `.lloyd` export).
- UI already has Export + Import buttons.
- Servers auto-save after every train.
- The on-device packaging step (Chaquopy / BeeWare) still needs to be run once on a machine with the Android SDK — the Python side is ready.

Once you have the APK built with Chaquopy (or BeeWare), training happens on-device and the brain can leave the phone whenever you want.
