# Run Lloyd on Termux (Android)

**Important:** On Termux do **not** run `pip install -r requirements.txt`.
That pulls **Gradio → orjson → Rust/maturin** and breaks (especially on Python 3.12+).

Use the minimal Termux deps instead.

## 0. Install Termux

F-Droid: https://f-droid.org/en/packages/com.termux/

## 1. Packages

```bash
pkg update -y && pkg upgrade -y
pkg install -y python git
pip install --upgrade pip
```

## 2. Clone + minimal install

```bash
cd ~
git clone https://github.com/christhepimp/lloydchrisisai.git
cd lloydchrisisai
pip install -r requirements-termux.txt
```

If clone already exists and `pip install -r requirements.txt` failed:

```bash
cd ~/lloydchrisisai
pip install numpy
```

That is enough for `server.py`.

## 3. API key (optional)

```bash
cd ~/lloydchrisisai
cp secrets.example.json secrets.json
nano secrets.json
```

```json
{
  "moltbook": "moltbook_sk_YOUR_KEY_HERE"
}
```

## 4. Run

```bash
cd ~/lloydchrisisai
python server.py
```

Browser on phone: **http://127.0.0.1:8080**

## 5. If you already broke the venv

```bash
cd ~/lloydchrisisai
pip uninstall -y orjson gradio maturin 2>/dev/null
pip install numpy
python server.py
```

## 6. Update

```bash
cd ~/lloydchrisisai && git pull && pip install -r requirements-termux.txt
```

## Why the error happened

`orjson` needs a Rust build (`maturin`) and `ANDROID_API_LEVEL`.
Lloyd’s Termux server is pure Python + NumPy — **no Gradio required**.
Gradio is only for Colab / desktop `app.py`.
