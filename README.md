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
- Mobile interface with **file upload + real neural training**  

## Current Status (v0.4)

- Pure NumPy Tiny Transformer with real learning  
- **Upload .txt files in the UI → hit Train → the neural net actually updates its weights**  
- Expanded English dictionary + Gen-Z slang  
- Autonomous agent with goals  
- Image generation placeholder  
- Vector memory  
- Local server connecting UI ↔ real agent ↔ trainer  

## How to run

```bash
python server.py
```

Then open **http://localhost:8080**

1. Chat with Lloyd  
2. Tap **Upload** and select a `.txt` file (any English text)  
3. Tap **Train** — Lloyd’s Transformer runs real training steps on your file  

You will see the loss going down in the response.

## Project Structure

```
lloydchrisisai/
├── server.py
├── main.py
├── lloyd/
│   ├── agent.py
│   ├── trainer.py          ← real neural training from uploads
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

Built by Chris + Lloyd.
