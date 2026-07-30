# Lloyd Category Dictionary (importance math only)

**Only words in your categories have values.**  
Everything else has **no value** and is not listed.

## Math format

| Form | Meaning |
|------|---------|
| `∆word+10$∆` | Category word: coding, hacking, english-structure, slang, attitude, humor |
| `∆word+7$∆` | Pattern indicator / relational connector |
| *(not listed)* | No importance value |

`$` = **context amplifier** — importance spreads to nearby words.

## Ranking

```
+numbers  >  0  >  -numbers
```

## Category groups

### +10$ (high priority + context spread)
- coding / programming
- hacking / security
- English language structure
- slang / Gen-Z
- attitude / personality
- adult / dark humor / jokes

### +7$ (pattern indicators / relational connectors)
- **Sequence/Order:** first, then, next, after, before, sequence, step, pattern, cycle, …
- **Comparison:** same, similar, opposite, contrast, both, identical, matching, parallel, …
- **Causality/Logic:** because, therefore, cause, effect, if, then, since, hence, leads to, …
- **Frequency:** always, often, sometimes, never, usually, typically, tends to, habit, …
- **Quantity/Change:** more, less, increase, decrease, grow, higher, lower, change, shift, …
- **Relationship:** connects, relates, linked, associated, bond, involves, affects, determines, …

## Files

- `special_plus10s.txt` — the live math dictionary (only valued words)
- `build_full_dict.py` — rebuild helper (outputs only category words)

## Load into Lloyd

```python
from lloyd.importance import engine
engine.load_dictionary_file("lloyd/dictionary/special_plus10s.txt")
```
