import threading


class RelogioVetorial:
    """Um contador por agência; a posição id_agencia é a desta agência."""

    def __init__(self, id_agencia: int, numero_agencias: int):
        self.id_agencia = id_agencia
        self._vetor = [0] * numero_agencias
        # O consumidor RabbitMQ roda numa thread separada das requisições HTTP
        self._lock = threading.Lock()

    def evento_local(self) -> list[int]:
        with self._lock:
            self._vetor[self.id_agencia] += 1
            return list(self._vetor)

    def ao_enviar(self) -> list[int]:
        with self._lock:
            self._vetor[self.id_agencia] += 1
            return list(self._vetor)

    def ao_receber(self, vetor_recebido: list[int]) -> list[int]:
        with self._lock:
            self._vetor = [max(local, recebido) for local, recebido in zip(self._vetor, vetor_recebido)]
            self._vetor[self.id_agencia] += 1
            return list(self._vetor)


def comparar(v1: list[int], v2: list[int]) -> str:
    v1_menor_ou_igual = all(a <= b for a, b in zip(v1, v2))
    v2_menor_ou_igual = all(b <= a for a, b in zip(v1, v2))
    if v1_menor_ou_igual and v2_menor_ou_igual:
        return "IGUAIS"
    if v1_menor_ou_igual:
        return "ANTES"
    if v2_menor_ou_igual:
        return "DEPOIS"
    return "CONCORRENTES"


def _selfcheck():
    a0, a1 = RelogioVetorial(0, 3), RelogioVetorial(1, 3)
    assert a0.evento_local() == [1, 0, 0]
    enviado = a0.ao_enviar()
    assert enviado == [2, 0, 0]
    assert a1.evento_local() == [0, 1, 0]
    assert a1.ao_receber(enviado) == [2, 2, 0]  # max posição a posição, depois +1 na própria

    # Perguntas da Parte B
    assert comparar([3, 1, 0], [3, 2, 0]) == "ANTES"
    assert comparar([3, 1, 0], [1, 3, 0]) == "CONCORRENTES"
    assert comparar([1, 0, 0], [1, 0, 0]) == "IGUAIS"
    print("vector_clock: ok")


if __name__ == "__main__":
    _selfcheck()
