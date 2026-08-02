"""
Lloyd Stable Tokenizer
======================
Character IDs are PERMANENT and ordered.

Growing vocab_size later only unlocks higher ID slots — it never
remaps existing characters. Learned embeddings stay valid.

UNK (unknown) is always id 0.
Default vocab_size = 600 (room for letters, punct, Latin-1, reserved).
"""

from __future__ import annotations

from typing import Dict, List, Tuple

# ---------------------------------------------------------------------------
# MASTER order — FROZEN. Only append at the end. Never reorder.
# id 0 = UNK
# ids 1.. = characters in this order when vocab is large enough
# ---------------------------------------------------------------------------
_STABLE_ORDER = (
    " "
    + "abcdefghijklmnopqrstuvwxyz"
    + "0123456789"
    + ".',!?-\n"
    + ":;()[]{}""/#@_+=*"
    + "\t"
    + "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    + "…—–“”‘’•°±×÷€£¥©®™"
    + "áéíóúàèìòùäëïöüñçÁÉÍÓÚÑ"
    + "<>\\|^~`$%&"
)

_seen = set()
_ORDERED: List[str] = []
for ch in _STABLE_ORDER:
    if ch not in _seen:
        _seen.add(ch)
        _ORDERED.append(ch)

# Fill remaining registry slots with Latin-1 / byte-ish placeholders (stable)
for code in range(32, 256):
    ch = chr(code)
    if ch not in _seen:
        _seen.add(ch)
        _ORDERED.append(ch)
    if len(_ORDERED) >= 599:  # +1 for UNK → 600 ids total capacity in table
        break

while len(_ORDERED) < 599:
    ch = chr(0x100 + len(_ORDERED))
    if ch not in _seen:
        _seen.add(ch)
        _ORDERED.append(ch)

MAX_REGISTRY = 600  # id 0 UNK + up to 599 chars


class StableTokenizer:
    """
    encode/decode with stable IDs.
    vocab_size = embedding table rows (default 600).
    Char at order index i → token id (i + 1) when that id < vocab_size.
    id 0 = UNK.
    """

    def __init__(self, vocab_size: int = 600):
        self.set_vocab_size(vocab_size)

    def set_vocab_size(self, vocab_size: int):
        vocab_size = max(2, min(int(vocab_size), MAX_REGISTRY))
        self.vocab_size = vocab_size
        self.itos: Dict[int, str] = {0: "\ufffd"}
        self.stoi: Dict[str, int] = {}
        for i, ch in enumerate(_ORDERED):
            tid = i + 1
            if tid >= vocab_size:
                break
            self.itos[tid] = ch
            self.stoi[ch] = tid
        # if uppercase not unlocked yet, map to lowercase id
        for ch in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            if ch not in self.stoi:
                low = ch.lower()
                if low in self.stoi:
                    self.stoi[ch] = self.stoi[low]

    def encode(self, text: str) -> List[int]:
        ids = []
        for ch in text:
            tid = self.stoi.get(ch)
            if tid is None or tid >= self.vocab_size:
                ids.append(0)
            else:
                ids.append(tid)
        return ids

    def decode(self, ids: List[int]) -> str:
        out = []
        for i in ids:
            if i == 0:
                continue
            out.append(self.itos.get(i, ""))
        return "".join(out)

    def expand(self, new_size: int) -> Tuple[int, int]:
        old = self.vocab_size
        new_size = max(old, min(int(new_size), MAX_REGISTRY))
        self.set_vocab_size(new_size)
        return old, self.vocab_size

    def status(self) -> str:
        return (
            f"tokenizer stable_ids vocab={self.vocab_size} "
            f"registry={len(_ORDERED)} max={MAX_REGISTRY} unk=0"
        )
