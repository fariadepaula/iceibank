OFFSET = 71  # dois últimos dígitos da matrícula/RA

NUMERO_AGENCIAS = 3
PORTA_BASE = 4000 + OFFSET

AGENCIAS = [
    {"id": i, "url": f"http://localhost:{PORTA_BASE + i}"}
    for i in range(NUMERO_AGENCIAS)
]


def agencia_responsavel(id_conta: int) -> int:
    return id_conta % NUMERO_AGENCIAS
