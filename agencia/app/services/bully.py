import threading

import requests

from app import config

TIMEOUT_S = 1  # mesmo valor do roteiro (TIMEOUT_MS = 1000)


class ServicoBully:
    """Eleição de líder pelo algoritmo de Bully: vence a agência ativa de maior ID."""

    def __init__(self, id_agencia: int, relogio, registro):
        self.id_agencia = id_agencia
        self.relogio = relogio
        self.registro = registro
        self._lider_atual = None
        self._eleicao_em_andamento = False
        # Rotas HTTP (pool de threads do FastAPI) e o heartbeat mexem no mesmo estado
        self._lock = threading.Lock()

    def _agencias_com_id_maior(self):
        return [a for a in config.AGENCIAS if a["id"] > self.id_agencia]

    def iniciar_eleicao(self) -> None:
        with self._lock:
            if self._eleicao_em_andamento:
                return
            self._eleicao_em_andamento = True
        try:
            vetor = self.relogio.evento_local()
            self.registro.registrar("ELEICAO_INICIADA", vetor, {"idAgencia": self.id_agencia})

            alguem_respondeu = False
            for agencia in self._agencias_com_id_maior():
                try:
                    vetor_envio = self.relogio.ao_enviar()
                    resposta = requests.post(
                        f"{agencia['url']}/bully/eleicao",
                        json={"origemId": self.id_agencia, "vetorEnvio": vetor_envio},
                        timeout=TIMEOUT_S,
                    )
                    resposta.raise_for_status()
                    alguem_respondeu = True
                except requests.exceptions.RequestException:
                    pass  # agência fora do ar ou não respondeu a tempo
        finally:
            with self._lock:
                self._eleicao_em_andamento = False

        if not alguem_respondeu:
            self._tornar_me_lider()
        # Se alguém maior respondeu, é ela quem conduz a própria eleição e
        # anuncia o resultado via /bully/coordenador.

    def _tornar_me_lider(self) -> None:
        with self._lock:
            self._lider_atual = self.id_agencia
        vetor = self.relogio.evento_local()
        self.registro.registrar("TORNOU_LIDER", vetor, {"idAgencia": self.id_agencia})

        for agencia in config.AGENCIAS:
            if agencia["id"] == self.id_agencia:
                continue
            try:
                vetor_envio = self.relogio.ao_enviar()
                requests.post(
                    f"{agencia['url']}/bully/coordenador",
                    json={"liderId": self.id_agencia, "vetorEnvio": vetor_envio},
                    timeout=TIMEOUT_S,
                )
            except requests.exceptions.RequestException:
                pass  # fora do ar: descobre a líder quando voltar e fizer a própria eleição

    def receber_eleicao(self, origem_id: int, vetor_recebido: list[int]) -> None:
        vetor = self.relogio.ao_receber(vetor_recebido)
        self.registro.registrar("ELEICAO_RECEBIDA", vetor, {"de": origem_id, "minhaId": self.id_agencia})
        # O 200 da rota é o "OK" implícito. A eleição própria roda em outra thread
        # para a resposta sair antes do timeout de 1s de quem perguntou.
        threading.Thread(target=self.iniciar_eleicao, daemon=True).start()

    def receber_coordenador(self, lider_id: int, vetor_recebido: list[int]) -> None:
        with self._lock:
            self._lider_atual = lider_id
        vetor = self.relogio.ao_receber(vetor_recebido)
        self.registro.registrar("LIDER_ANUNCIADO", vetor, {"liderId": lider_id, "agencia": self.id_agencia})

    def obter_lider_atual(self):
        with self._lock:
            return self._lider_atual
