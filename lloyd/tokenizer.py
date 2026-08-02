"""
Lloyd Stable Tokenizer
======================
Character IDs are PERMANENT and ordered.

Growing vocab_size later only unlocks higher ID slots — it never
remaps existing characters. That way embeddings already learned for
'a'=1, 'b'=2, ... stay valid when you go 50 → 128 → 256.

UNK (unknown) is always id 0.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

# ---------------------------------------------------------------------------
# MASTER table — order is frozen forever. Only append at the end if needed.
# Active vocab_size = how many of these rows the model embedding table has.
# ---------------------------------------------------------------------------
MASTER_CHARS: List[str] = list(
    # 0 is reserved as UNK placeholder symbol in itos only; encoding uses id 0 for OOV
    " "  # will be id 1 when we shift — actually we use index in list as id, id 0 = UNK
)

# Build: id 0 = UNK (not a real char in stoi for normal letters)
# ids 1.. = stable characters in fixed order
_STABLE_ORDER = (
    " "
    + "abcdefghijklmnopqrstuvwxyz"
    + "0123456789"
    + ".',!?-\n"
    + ":;()[]{}""/#@_+=*"
    + "\t"
    + "ABCDEFGHIJKLMNOPQRSTUVWXYZ"  # own ids when vocab large enough
    + "…—–“”‘’•°±×÷€£¥"
)

# Deduplicate preserving order
_seen = set()
_ORDERED: List[str] = []
for ch in _STABLE_ORDER:
    if ch not in _seen:
        _seen.add(ch)
        _ORDERED.append(ch)

# Theoretical max registry size (can extend later by appending only)
MAX_REGISTRY = max(256, len(_ORDERED) + 1)


class StableTokenizer:
    """
    encode/decode with stable IDs.
    vocab_size = number of embedding rows (must be >= 2).
    Char at MASTER index i always maps to token id (i + 1) when (i+1) < vocab_size.
    id 0 = UNK / OOV.
    """

    def __init__(self, vocab_size: int = 50):
        self.set_vocab_size(vocab_size)

    def set_vocab_size(self, vocab_size: int):
        vocab_size = max(2, int(vocab_size))
        self.vocab_size = vocab_size
        # id 0 = UNK
        self.itos: Dict[int, str] = {0: "�"}
        self.stoi: Dict[str, int] = {}
        # assign stable ids 1..vocab_size-1 from frozen order
        for i, ch in enumerate(_ORDERED):
            tid = i + 1
            if tid >= vocab_size:
                break
            self.itos[tid] = ch
            self.stoi[ch] = tid
        # lowercase already in table; if uppercase not yet unlocked, map to lower
        for ch in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            if ch not in self.stoi:
                low = ch.lower()
                if low in self.stoi:
                    self.stoi[ch] = self.stoi[low]

    def encode(self, text: str) -> List[int]:
        ids = []
        for ch in text:
            tid = self.stoi.get(ch)
            if tid is None:
                # uppercase fallback already handled; true OOV → 0
                # if char exists in master but vocab too small, still UNK (not scramble)
                ids.append(0)
            else:
                ids.append(tid if tid < self.vocab_size else 0)
        return ids

    def decode(self, ids: List[int]) -> str:
        out = []
        for i in ids:
            if i == 0:
                continue  # drop UNK noise in output
            out.append(self.itos.get(i, ""))
        return "".join(out)

    def expand(self, new_size: int) -> Tuple[int, int]:
        """Grow active vocab. Returns (old_size, new_size). IDs unchanged."""
        old = self.vocab_size
        new_size = max(old, int(new_size))
        self.set_vocab_size(new_size)
        return old, self.vocab_size

    def status(self) -> str:
        return f"tokenizer stable_ids vocab={self.vocab_size} registry={len(_ORDERED)} unk=0"
