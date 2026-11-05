import os
import time
import uuid


def uuid7() -> uuid.UUID:
    """UUID versión 7 (RFC 9562): 48 bits de tiempo en ms + bits aleatorios."""
    ms = time.time_ns() // 1_000_000
    aleatorio = int.from_bytes(os.urandom(10), "big")  # 80 bits
    rand_a = (aleatorio >> 68) & 0xFFF                 # 12 bits
    rand_b = aleatorio & ((1 << 62) - 1)               # 62 bits
    valor = (ms & ((1 << 48) - 1)) << 80
    valor |= 0x7 << 76      # versión 7
    valor |= rand_a << 64
    valor |= 0b10 << 62     # variante RFC
    valor |= rand_b
    return uuid.UUID(int=valor)