import threading
from contextlib import contextmanager

import pika

from app import config
from app.services.auth import hash_senha, verificar_senha
from app.services.event_log import RegistroEventos
from app.services.mensageria import publicar
from app.services.vector_clock import RelogioVetorial, comparar


class ErroNegocio(Exception):
    status = 400

    def __init__(self, detalhe: str):
        super().__init__(detalhe)
        self.detalhe = detalhe


class ContaNaoEncontrada(ErroNegocio):
    status = 404


class ContaJaExiste(ErroNegocio):
    status = 409


class SaldoInsuficiente(ErroNegocio):
    status = 400


class BrokerIndisponivel(ErroNegocio):
    status = 503


class ConflitoSincronizacao(ErroNegocio):
    status = 409

    def __init__(self, detalhe: str, **extra):
        super().__init__(detalhe)
        self.extra = extra


def _publica(conta: dict, vetor_atual: list[int]) -> dict:
    """Cópia sem a senha: nada fora deste módulo recebe referência ao estado interno."""
    return {"id": conta["id"], "nomeAluno": conta["nomeAluno"], "saldo": conta["saldo"], "vetorAtual": vetor_atual}


class Agencia:
    """Dona de uma partição de contas (id % 3). Única porta de acesso ao estado da
    agência: as rotas HTTP e o consumidor RabbitMQ chamam estes métodos, e toda
    leitura-e-escrita de saldo acontece sob o mesmo lock."""

    def __init__(self, id_agencia: int):
        self.id = id_agencia
        self.relogio = RelogioVetorial(id_agencia, config.NUMERO_AGENCIAS)
        self.registro = RegistroEventos(f"agencia-{id_agencia}")
        self._contas: dict[int, dict] = {}
        self._operacoes_vistas: dict[str, dict] = {}
        # Rotas síncronas rodam num pool de threads e o consumidor da fila em outra
        # thread: sem isso, "verifica saldo, depois debita" deixa dois saques
        # simultâneos passarem pela verificação e o saldo fica negativo.
        self._lock = threading.Lock()

    def e_dona(self, id_conta: int) -> bool:
        return config.agencia_responsavel(id_conta) == self.id

    @contextmanager
    def _conta(self, id_conta: int):
        with self._lock:
            conta = self._contas.get(id_conta)
            if not conta:
                raise ContaNaoEncontrada("Conta não encontrada nesta agência.")
            yield conta

    # --- contas ---

    def criar_conta(self, id_conta: int, nome_aluno: str, senha: str, saldo_inicial: float) -> dict:
        if not self.e_dona(id_conta):
            raise ErroNegocio(f"Conta {id_conta} não pertence a esta agência.")
        with self._lock:
            if id_conta in self._contas:
                raise ContaJaExiste("Conta já existe.")
            ts = self.relogio.evento_local()
            self._contas[id_conta] = {
                "id": id_conta,
                "nomeAluno": nome_aluno,
                "saldo": saldo_inicial,
                "senha_hash": hash_senha(senha),
            }
            self.registro.registrar("CRIAR_CONTA", ts, {"id": id_conta, "nomeAluno": nome_aluno, "saldoInicial": saldo_inicial})
            return _publica(self._contas[id_conta], self.relogio.obter_vetor_atual())

    def autenticar(self, id_conta: int, senha: str) -> bool:
        with self._lock:
            conta = self._contas.get(id_conta)
            senha_hash = conta["senha_hash"] if conta else None
        # PBKDF2 é lento de propósito, então a verificação fica fora do lock para não travar a agência
        return senha_hash is not None and verificar_senha(senha, senha_hash)

    def consultar(self, id_conta: int) -> dict:
        with self._conta(id_conta) as conta:
            return _publica(conta, self.relogio.obter_vetor_atual())

    def depositar(self, id_conta: int, valor: float) -> dict:
        with self._conta(id_conta) as conta:
            ts = self.relogio.evento_local()
            conta["saldo"] += valor
            self.registro.registrar("DEPOSITO", ts, {"id": id_conta, "valor": valor, "novoSaldo": conta["saldo"]})
            return _publica(conta, self.relogio.obter_vetor_atual())

    def sacar(self, id_conta: int, valor: float) -> dict:
        with self._conta(id_conta) as conta:
            if conta["saldo"] < valor:
                raise SaldoInsuficiente("Saldo insuficiente.")
            ts = self.relogio.evento_local()
            conta["saldo"] -= valor
            self.registro.registrar("SAQUE", ts, {"id": id_conta, "valor": valor, "novoSaldo": conta["saldo"]})
            return _publica(conta, self.relogio.obter_vetor_atual())

    # --- sincronização offline-first (Sprint 3, Parte E) ---

    def sincronizar(self, id_conta: int, tipo: str, valor: float, vetor_conhecido: list[int], operacao_id: str | None) -> dict:
        with self._conta(id_conta) as conta:
            if operacao_id and operacao_id in self._operacoes_vistas:
                return {**self._operacoes_vistas[operacao_id], "vetorAtual": self.relogio.obter_vetor_atual()}

            vetor_atual = self.relogio.obter_vetor_atual()
            relacao = comparar(vetor_conhecido, vetor_atual)
            if relacao != "IGUAIS":
                # Algo aconteceu nesta agência desde a última leitura do app. Em vez de
                # aplicar às cegas, devolve o estado real para o app decidir.
                # A recusa não avança o relógio. Se avançasse, o vetorAtual devolvido
                # já nasceria velho e o app nunca conseguiria sincronizar.
                print(f"[sincronizar] conflito na conta {id_conta}: app={vetor_conhecido} agência={vetor_atual} ({relacao})")
                raise ConflitoSincronizacao(
                    "Conflito detectado: o estado da conta mudou desde a última sincronização do app.",
                    vetorConhecido=vetor_conhecido,
                    vetorAtual=vetor_atual,
                    contaAtual=_publica(conta, vetor_atual),
                )

            if tipo == "SAQUE" and conta["saldo"] < valor:
                raise SaldoInsuficiente("Saldo insuficiente.")
            ts = self.relogio.evento_local()
            conta["saldo"] += valor if tipo == "DEPOSITO" else -valor
            self.registro.registrar("SINCRONIZACAO_OFFLINE", ts, {"id": id_conta, "tipo": tipo, "valor": valor, "novoSaldo": conta["saldo"]})
            resultado = _publica(conta, list(ts))
            self._lembrar(operacao_id, resultado)
            return resultado

    # --- transferências ---

    def transferir(self, id_origem: int, id_destino: int, valor: float, operacao_id: str | None) -> dict:
        detalhes = {"idOrigem": id_origem, "idDestino": id_destino, "valor": valor}
        agencia_destino = config.agencia_responsavel(id_destino)

        with self._lock:
            # Idempotência (funcionalidade adicional do Sprint 1): repetir o mesmo
            # operacaoId devolve o resultado anterior sem debitar de novo.
            if operacao_id and operacao_id in self._operacoes_vistas:
                return self._operacoes_vistas[operacao_id]

            origem = self._contas.get(id_origem)
            if not origem:
                raise ContaNaoEncontrada("Conta de origem não encontrada nesta agência.")
            if origem["saldo"] < valor:
                raise SaldoInsuficiente("Saldo insuficiente.")

            if agencia_destino == self.id:
                destino = self._contas.get(id_destino)
                if not destino:
                    raise ContaNaoEncontrada("Conta de destino não encontrada.")
                # Débito e crédito acontecem sob o mesmo lock, então são atômicos
                self.registro.registrar("TRANSFERENCIA_DEBITO", self.relogio.evento_local(), detalhes)
                origem["saldo"] -= valor
                destino["saldo"] += valor
                self.registro.registrar("TRANSFERENCIA_CREDITO", self.relogio.evento_local(), detalhes)
                return self._lembrar(operacao_id, {"mensagem": "Transferência concluída (mesma agência)."})

            # Entre agências: o débito é reservado aqui, sob o lock...
            origem["saldo"] -= valor
            self.registro.registrar("TRANSFERENCIA_DEBITO", self.relogio.evento_local(), detalhes)
            ts_envio = self.relogio.ao_enviar()

        # ...e a publicação (rede) acontece fora dele, para não travar a agência
        # inteira enquanto o broker responde.
        try:
            publicar(
                f"agencia.{agencia_destino}.creditar",
                {
                    "idConta": id_destino,
                    "valor": valor,
                    "vetorEnvio": ts_envio,
                    "origemAgencia": self.id,
                    "idOrigem": id_origem,
                    "operacaoId": operacao_id,
                },
            )
        except pika.exceptions.AMQPError as erro:
            # Nada saiu deste processo, então desfazer o débito aqui é seguro
            with self._lock:
                origem["saldo"] += valor
                self.registro.registrar("TRANSFERENCIA_FALHOU", self.relogio.evento_local(), {**detalhes, "erro": repr(erro)})
            raise BrokerIndisponivel("Broker de mensagens indisponível. Débito desfeito, tente novamente.")

        # 200 aqui significa "publicada", não "creditada": o crédito é assíncrono
        with self._lock:
            return self._lembrar(operacao_id, {"mensagem": "Transferência publicada para a agência de destino (entrega assíncrona)."})

    def aplicar_credito_remoto(self, mensagem: dict) -> bool:
        """Consumidor da fila desta agência. Devolve False se o crédito não puder
        ser aplicado; a mensagem vai então para a fila dead-letter."""
        operacao_id = mensagem.get("operacaoId")
        detalhes = {"idConta": mensagem["idConta"], "valor": mensagem["valor"], "origemAgencia": mensagem["origemAgencia"]}
        with self._lock:
            # Entrega é "pelo menos uma vez": uma mensagem repetida não credita duas vezes
            if operacao_id and operacao_id in self._operacoes_vistas:
                return True
            # Ao RECEBER de outra agência, mescla o vetor (regra 3)
            ts = self.relogio.ao_receber(mensagem["vetorEnvio"])
            conta = self._contas.get(mensagem["idConta"])
            if not conta:
                self.registro.registrar("CREDITO_REMOTO_FALHOU", ts, {**detalhes, "motivo": "conta não encontrada"})
                return False
            conta["saldo"] += mensagem["valor"]
            self.registro.registrar("TRANSFERENCIA_CREDITO_REMOTO", ts, detalhes)
            self._lembrar(operacao_id, {"mensagem": "Crédito remoto aplicado."})
            return True

    def _lembrar(self, operacao_id: str | None, resultado: dict) -> dict:
        # Chamado sempre com self._lock já adquirido
        if operacao_id:
            self._operacoes_vistas[operacao_id] = resultado
        return resultado
