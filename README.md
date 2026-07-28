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
- Mobile interface started  

## Current Status (v0.2)

- Pure NumPy Tiny Transformer (decoder-only) from scratch  
- Training loop skeleton (real backprop coming next)  
- Expanded English dictionary + Gen-Z slang  
- Gen-Z personality & identity  
- Simple vector memory  
- Autonomous agent loop with goals  
- Image generation placeholder (Lloyd can trigger it himself)  
- Mobile-friendly web interface  
- Terminal chat working  

## How to run

### Terminal
```bash
python main.py
```

### Mobile Web Interface
Open `interface/mobile_web/index.html` in a browser (or serve it).

## Project Structure

```
lloydchrisisai/
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

1. Real backpropagation for the Transformer so it can actually learn  
2. Connect the mobile interface to the real Python agent  
3. More advanced English rules  
4. Scale architecture toward 3B  

Built by Chris + Lloyd.
