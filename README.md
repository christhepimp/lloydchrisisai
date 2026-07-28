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
- Mobile interface coming  

## Current Status (v0.1)

- Pure NumPy Tiny Transformer (decoder-only) from scratch  
- Training loop skeleton  
- Hard-coded English dictionary + basic rule engine  
- Gen-Z personality & identity  
- Simple vector memory  
- Autonomous agent loop with goals  
- Terminal chat working  

## How to run right now

```bash
python main.py
```

## Project Structure

```
lloydchrisisai/
├── main.py
├── lloyd/
│   ├── agent.py
│   ├── english_engine.py
│   ├── memory.py
│   └── personality.py
└── model/
    └── tiny_transformer.py
```

## Next steps

1. Real backpropagation for the Transformer  
2. Expand the English dictionary heavily  
3. Mobile-friendly web interface  
4. Image generation module  
5. Scale the architecture toward 3B  

Built by Chris + Lloyd.
