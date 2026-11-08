"""Limite de taxa simples: garante um intervalo mínimo entre requisições."""

import time
from collections.abc import Callable


class MinIntervalLimiter:
    """Espera o necessário para manter `min_interval` segundos entre chamadas."""

    def __init__(
        self,
        min_interval: float,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.min_interval = min_interval
        self._clock = clock
        self._sleep = sleep
        self._last: float | None = None

    def wait(self) -> None:
        """Bloqueia até poder fazer a próxima requisição."""
        now = self._clock()
        if self._last is not None:
            remaining = self.min_interval - (now - self._last)
            if remaining > 0:
                self._sleep(remaining)
                now = self._clock()
        self._last = now
