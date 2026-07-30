# Lloyd Annotated Dictionary (SCOWL complete copy)

This is a **complete rewritten copy** of SCOWL 2020.12.07 English word lists
(levels 10–70, american + english), with Lloyd importance math on **every word**.

## Math format

| Form | Meaning |
|------|---------|
| `∆word+N∆` | Word has importance **N** |
| `∆word+N$∆` | Word has importance **N** **and** context-spread (`$`) to nearby words |

## Ranking (hard-coded in Lloyd)

```
+numbers  >  0 (no number)  >  -numbers
```

## Category boosts → `∆word+10$∆`

These categories get **+10** importance **and** context amplifier `$`:

- coding / programming
- hacking / security
- English language structure (grammar, function words)
- slang / Gen-Z
- attitude / personality
- adult humor, dark humor, jokes

All other SCOWL words → `∆word+1∆`

## Files

- `lloyd_annotated_dictionary.txt` — full single file (~2MB, 111k+ words)
- `full/part_XX.txt` — same content split for easier handling
- `special_plus10s.txt` — only the +10$ category words

## Source

SCOWL 2020.12.07 — free to use/modify/distribute (Kevin Atkinson et al.).

## Load into Lloyd

Lloyd’s importance engine parses every `∆...∆` marker.
The `$` flag enables context spreading before attention.
