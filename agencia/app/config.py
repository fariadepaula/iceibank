import os

# TODO: substitua pelo seu OFFSET pessoal (dois últimos dígitos da matrícula/RA),
# necessário apenas se for rodar em uma máquina compartilhada do laboratório.
OFFSET = int(os.getenv("ICEIBANK_OFFSET", "0"))

NUMERO_AGENCIAS = 3
PORTA_BASE = 4000 + OFFSET

AGENCIAS = [
    {"id": i, "url": f"http://localhost:{PORTA_BASE + i}"}
    for i in range(NUMERO_AGENCIAS)
]


def agencia_responsavel(id_conta: int) -> int:
    return id_conta % NUMERO_AGENCIAS
