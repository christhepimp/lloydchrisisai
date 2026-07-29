# Deploying Lloyd (same brain, any host)

Lloyd’s brain lives only in `lloyd/` + `model/`.  
Every deployment method below runs that exact same code.

## Option A – Render / Railway / Fly / any container host

`Procfile` already exists:

```
web: python server.py
```

Just connect the GitHub repo and set the start command if needed.  
The host will inject `PORT`; `server.py` already reads it.

## Option B – PythonAnywhere (WSGI)

Use `flask_app.py`:

```python
# in your WSGI file
from flask_app import app as application
```

## Option C – Hugging Face Spaces

`app.py` is a ready Gradio interface that imports the same `Lloyd` + `LloydTrainer`.

## Option D – Local + reverse proxy / Cloudflare Tunnel

```bash
python server.py
# then expose with cloudflared / ngrok / caddy
```

## After you have a public URL

1. Update the APK’s `API` constant (see `mobile/README.md`)
2. Rebuild the APK
3. Users get the full version on their phone while the brain grows on the server

When Lloyd is big enough you can later ship a quantized on-device version — the architecture already separates brain from UI.
