import threading


class RelogioLamport:
    """Contador lógico de Lamport - não é um relógio de parede."""

    def __init__(self):
        self._contador = 0
        self._lock = threading.Lock()

    @property
    def contador(self) -> int:
        with self._lock:
            return self._contador

    def evento_local(self) -> int:
        with self._lock:
            self._contador += 1
            return self._contador

    def ao_enviar(self) -> int:
        with self._lock:
            self._contador += 1
            return self._contador

    def ao_receber(self, timestamp_recebido: int) -> int:
        with self._lock:
            self._contador = max(self._contador, timestamp_recebido) + 1
            return self._contador


def _selfcheck():
    r = RelogioLamport()
    assert r.evento_local() == 1
    assert r.evento_local() == 2
    assert r.ao_enviar() == 3
    assert r.ao_receber(10) == 11  # recebido adiantado -> salta pra frente
    assert r.ao_receber(1) == 12   # recebido atrasado -> local prevalece
    print("lamport_clock: ok")


if __name__ == "__main__":
    _selfcheck()
