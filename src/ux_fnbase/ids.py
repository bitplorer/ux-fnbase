"""26-char deterministic-ish ids: 10-char time prefix + 16-char entropy.

Time prefix is milliseconds since epoch encoded in base32 (50 bits).
Entropy is 80 bits of secrets.token_hex truncated via base32 alphabet.
"""

from __future__ import annotations

import secrets
import time

_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def _b32(n: int, width: int) -> str:
    if n < 0:
        n = 0
    out = []
    for _ in range(width):
        out.append(_ALPHABET[n & 31])
        n >>= 5
    return "".join(reversed(out))


def new_id(now_ms: int | None = None) -> str:
    ms = int(now_ms if now_ms is not None else time.time() * 1000)
    time_part = _b32(ms & ((1 << 50) - 1), 10)
    entropy = int.from_bytes(secrets.token_bytes(10), "big")
    ent_part = _b32(entropy, 16)
    return time_part + ent_part
