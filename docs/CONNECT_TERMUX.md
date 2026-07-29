# Connect Lloyd APK to Termux (same phone)

## Why it failed before

1. **127.0.0.1 does not work** between the Lloyd APK and Termux.
   They are different apps. Each has its own localhost.
2. Android blocks plain **http://** from apps unless the APK allows cleartext.
   Rebuild the APK from Actions (new workflow enables this).

## Correct setup

### Termux (keep this running)

```bash
cd ~/lloydchrisisai
python server.py
```

You should see: `Lloyd is live on port 8080`

### Get your phone IP

```bash
ifconfig
```

Use the `wlan0` inet address, e.g. `10.11.205.156`

### In the Lloyd app

1. Tap **⚙**
2. Enter: `http://10.11.205.156:8080`  (your IP)
3. Tap **Test** — should say connected
4. Tap **Save**

Do **not** use `127.0.0.1` or `localhost`.

### Test in Chrome first

Open Chrome on the phone:

```
http://10.11.205.156:8080
```

If the Lloyd page loads, the server is fine and the APK only needed cleartext + the right IP.

### Rebuild APK

After this repo update, go to **Actions → Build Lloyd APK → Run workflow**,
download the new artifact, and install it (uninstall the old one first).
