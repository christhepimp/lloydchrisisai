# Lloyd Category Dictionary (attention header guide)

**Only words in your categories have values.**  
Everything else has **no value** and is not listed.

The dictionary is a **guide for the attention header while it is still learning**.  
The header runs on its own; `$` is only a **boost** (context amplifier), not a replacement.

## Math format

| Form | Meaning |
|------|---------|
| `∆word+10∆` | Word is important (no context spread) |
| `∆word+10$∆` | Important **+ context amplifier** — nearby words get a boost |
| `∆word+7$∆` | Pattern connector + context amplifier |
| clamp | **never over +10 or under −10** |

Ranking: `+numbers > 0 > -numbers`

## Who gets `$` vs plain `+`

| Categories | Marker |
|------------|--------|
| **STRUCTURE**, **HUMOR**, **PATTERN** | `+$` (context amplifier) |
| **CODING**, **HACKING**, **SLANG**, **ATTITUDE** | plain `+` only |

- STRUCTURE / HUMOR → `∆word+10$∆`
- PATTERN → `∆word+7$∆` (or +10$ if also in a +10 category)
- CODING / HACKING / SLANG / ATTITUDE → `∆word+10∆`

## Files

- `build_full_dict.py` — category sets + rebuild rules (source of truth)
- `special_plus10s.txt` — optional on-disk dump (`python build_full_dict.py`)
- Engine loads categories at runtime via `lloyd.importance`

## Load

```python
from lloyd.importance import engine
engine.load_dictionary_file("lloyd/dictionary/special_plus10s.txt")
print(engine.status())
print(engine.highlight("the code was funny because the pattern repeated"))
```
