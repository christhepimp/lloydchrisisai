# Moving Lloyd’s Brain

Lloyd’s entire state is portable. You can train him on your phone, then move the exact same brain to a server, laptop, or another phone later.

## What gets saved

A `.lloyd` file is a zip that contains:

| File            | Contents                          |
|-----------------|-----------------------------------|
| `brain.npz`     | All neural weights (TinyTransformer) |
| `memory.json`   | Vector memory of conversations    |
| `meta.json`     | Version + goals                   |

## From the UI

1. **Export** button → downloads `lloyd_brain.lloyd`
2. Copy that file anywhere (Google Drive, USB, another device, server)
3. On the new place: **Import** button → pick the `.lloyd` file

Same weights. Same memories. Same personality.

## From code / CLI

```python
from lloyd.agent import Lloyd
from lloyd.trainer import LloydTrainer

lloyd = Lloyd()
trainer = LloydTrainer()

# after some training…
lloyd.export_brain("my_lloyd.lloyd", trainer=trainer)

# later, on another machine:
lloyd2 = Lloyd()
trainer2 = LloydTrainer()
lloyd2.import_brain("my_lloyd.lloyd", trainer=trainer2)
```

Or just the neural net:

```python
trainer.save_brain("weights.npz")
trainer.load_brain("weights.npz")
```

## Automatic saves

Both `server.py` and `flask_app.py` automatically write:

- `brains/latest_brain.npz`
- `brains/latest_memory.json`

after every Train. On next start they restore automatically.

## APK → Server (or the other way)

1. Train on the phone APK
2. Hit Export → get the `.lloyd` file
3. Upload that file to your hosted Lloyd (Import)
4. Or copy it into the `brains/` folder on the server and load it

The brain is just files. No lock-in.
