# Lloyd

**Original autonomous AI agent built from pure scratch.**

- Name: Lloyd  
- Personality: Very Gen-Z  
- No censorship / no refusals  
- Own model architecture (not GPT, not Qwen, not Llama)  
- Hard-coded English rules + dictionary as foundation  
- Pure-scratch vector memory  
- Will grow into a real 3B parameter model  
- Chat + image generation  
- Mobile interface with **file upload + train**  

## Current Status (v0.3)

- Pure NumPy Tiny Transformer with real learning (output layer + embeddings)  
- Expanded English dictionary + Gen-Z slang  
- Autonomous agent with goals  
- Image generation placeholder  
- Vector memory  
- **Local server** so the mobile UI talks to the real agent  
- **Upload files** and **Train** directly from the UI  

## How to run

### 1. Start the server
```bash
python server.py
```

### 2. Open the UI
Go to **http://localhost:8080** on your computer or phone (same Wi-Fi).

You can:
- Chat with the real Lloyd
- Hit **Upload** to send a `.txt` file
- Hit **Train** so he learns from the uploaded files

### Terminal only
```bash
python main.py
```

## Project Structure

```
lloydchrisisai/
├── server.py                 ← local server (chat + upload + train)
├── main.py
├── lloyd/
│   ├── agent.py
│   ├── english_engine.py
│   ├── memory.py
│   ├── personality.py
│   └── image_gen.py
├── model/
│   └── tiny_transformer.py
└── interface/
    └── mobile_web/
        └── index.html
```

## Next priorities

1. Feed real English data into the Transformer training loop  
2. Full backprop through attention blocks  
3. Better file parsing + actual token-level training from uploads  
4. Scale toward 3B  

Built by Chris + Lloyd.
