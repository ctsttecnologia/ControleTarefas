
# automovel/throttling.py
"""
Rate-limiter in-memory leve, sem dependência de cache externo.

Implementa sliding window por chave. Thread-safe.
Adequado para single-process ou poucos workers.
Para multi-worker em produção pesada, migrar para Redis no futuro.
"""

import threading
import time
from collections import defaultdict, deque
from typing import Deque, DefaultDict


class InMemoryRateLimiter:
    """
    Rate-limiter sliding window em memória.

    Args:
        rate: Máximo de requests permitidos na janela.
        window_seconds: Tamanho da janela em segundos.

    Exemplo:
        limiter = InMemoryRateLimiter(rate=60, window_seconds=60)
        if not limiter.is_allowed("token-abc"):
            return JsonResponse({"error": "rate-limited"}, status=429)
    """

    def __init__(self, rate: int, window_seconds: int):
        if rate < 1 or window_seconds < 1:
            raise ValueError("rate e window_seconds devem ser >= 1")
        self.rate = rate
        self.window = window_seconds
        self._buckets: DefaultDict[str, Deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()
        self._request_count = 0  # para cleanup periódico

    def is_allowed(self, key: str) -> bool:
        """Retorna True se o request está dentro do limite, False caso contrário."""
        now = time.monotonic()
        cutoff = now - self.window

        with self._lock:
            bucket = self._buckets[key]

            # Remove timestamps fora da janela
            while bucket and bucket[0] < cutoff:
                bucket.popleft()

            if len(bucket) >= self.rate:
                return False

            bucket.append(now)

            # Cleanup oportunístico a cada 1000 requests
            self._request_count += 1
            if self._request_count >= 1000:
                self._request_count = 0
                self._cleanup_locked(cutoff)

            return True

    def _cleanup_locked(self, cutoff: float) -> None:
        """Remove buckets vazios ou totalmente expirados. Lock já adquirido."""
        stale = [
            k for k, b in self._buckets.items()
            if not b or b[-1] < cutoff
        ]
        for k in stale:
            del self._buckets[k]

    def reset(self, key: str) -> None:
        """Limpa o bucket de uma chave específica (uso administrativo)."""
        with self._lock:
            self._buckets.pop(key, None)


# ── Singletons configurados ──────────────────────────────────────
# 60 req/min por token → 1 req/s, suficiente para hardware GPS típico
tracking_limiter = InMemoryRateLimiter(rate=60, window_seconds=60)
