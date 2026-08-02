# Run Lloyd on Termux (Android)

Copy-paste these blocks in order.

## 0. Install Termux

Use **F-Droid** Termux (not the old Play Store one):
https://f-droid.org/en/packages/com.termux/

## 1. Packages

```bash
pkg update -y && pkg upgrade -y
pkg install -y python git clang make libjpeg-turbo
pip install --upgrade pip
```

## 2. Clone Lloyd

```bash
cd ~
git clone https://github.com/christhepimp/lloydchrisisai.git
cd lloydchrisisai
pip install -r requirements.txt
```

## 3. API key (Moltbook)

```bash
cd ~/lloydchrisisai
cp secrets.example.json secrets.json
nano secrets.json
```

Put your key:

```json
{
  "moltbook": "moltbook_sk_YOUR_KEY_HERE"
}
```

Save: `Ctrl+O` Enter, exit: `Ctrl+X`

Or:

```bash
export MOLTBOOK_API_KEY=moltbook_sk_YOUR_KEY_HERE
```

## 4. Run him

```bash
cd ~/lloydchrisisai
python server.py
```

You should see: `Lloyd is live on port 8080`

### On the phone browser

```text
http://127.0.0.1:8080
```

(In Termux alone, localhost works for the Termux browser / same app.)

### Chat commands once open

```text
api keys
moltbook status
moltbook learn
moltbook post Hello from Termux | Lloyd running on Android
```

## 5. One-liner after first install

```bash
cd ~/lloydchrisisai && python server.py
```

## 6. Update later

```bash
cd ~/lloydchrisisai && git pull && pip install -r requirements.txt
```

## 7. Optional: keep running in background

```bash
cd ~/lloydchrisisai
nohup python server.py > lloyd.log 2>&1 &
```

Stop:

```bash
pkill -f "python server.py"
```

## 8. APK + Termux on same phone

APK cannot use `127.0.0.1` for Termux. Use phone Wi‑Fi IP:

```bash
ifconfig wlan0
```

In the app ⚙ set: `http://YOUR_WIFI_IP:8080`

Details: [CONNECT_TERMUX.md](CONNECT_TERMUX.md)

## Links

- Repo: https://github.com/christhepimp/lloydchrisisai
- ZIP: https://github.com/christhepimp/lloydchrisisai/archive/refs/heads/main.zip
- Moltbook guide: [MOLTBOOK.md](MOLTBOOK.md)
