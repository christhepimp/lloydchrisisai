# Get the Lloyd APK — no Android Studio

The APK is built automatically in the cloud by GitHub Actions.

## Steps

1. Go to the repo: https://github.com/christhepimp/lloydchrisisai
2. Click the **Actions** tab
3. Select **Build Lloyd APK** on the left
4. Click **Run workflow** (button on the right)
   - Optional: paste your hosted Lloyd URL (e.g. `https://lloyd-xxxx.onrender.com`) so it’s baked into the app
   - Or leave blank and set the URL later inside the app (⚙ button)
5. Wait ~5–10 minutes for the green checkmark
6. Open that run → **Artifacts** → download **lloyd-apk**
7. Unzip it → you get `app-debug.apk`
8. On your Android phone:
   - Enable **Install from unknown sources** / **Install unknown apps** for your file manager or browser
   - Open the `.apk` and install

## Point the app at Lloyd’s brain

The APK is the UI shell. The brain (chat + train + export) runs where you host it.

### Quick free host (Render)

1. Go to https://render.com → New → Web Service
2. Connect the `lloydchrisisai` GitHub repo
3. Runtime: Python
4. Build: `pip install -r requirements.txt`
5. Start: `python server.py`
6. After deploy, copy the URL (e.g. `https://lloyd-xxxx.onrender.com`)
7. In the Lloyd app tap **⚙** → paste that URL → Save

Now Upload / Train / Export / Import all work from your phone.  
After training, hit **Export** to download `lloyd_brain.lloyd` and move him anywhere later.

### Same machine (testing)

```bash
python server.py
# then expose with cloudflared / ngrok if you want the phone to reach it
```

## Re-building

Any push that touches the mobile UI or the workflow file triggers a new build.  
You can also always hit **Run workflow** manually.

## Note on “full brain inside the APK”

This APK runs the full UI and talks to the real Lloyd brain over the network.  
Training happens on the server (or your PC), not inside the phone’s CPU — that’s why we don’t need Android Studio or a huge Python runtime in the APK.

When you want true offline on-device training later, the same portable `.lloyd` brain file and the Chaquopy path in `docs/ON_DEVICE_APK.md` are ready.
