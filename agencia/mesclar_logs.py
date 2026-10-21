import json
from itertools import combinations
from pathlib import Path

from app.services.vector_clock import comparar

PASTA_DADOS = Path(__file__).resolve().parent / "data"


def carregar_eventos() -> list[dict]:
    eventos = []
    for arquivo in sorted(PASTA_DADOS.glob("*.jsonl")):
        linhas = arquivo.read_text(encoding="utf-8").strip().splitlines()
        eventos.extend(json.loads(linha) for linha in linhas if linha)
    return eventos


def resumo(evento: dict) -> str:
    return f"[{evento['agencia']}] {evento['tipo']} {evento['timestampVetorial']}"


def main():
    # Hora de parede só para exibir em ordem legível; a causalidade vem do vetor
    eventos = sorted(carregar_eventos(), key=lambda e: e["horaParede"])
    print("=== Linha do tempo (ordenada por hora de parede) ===")
    for evento in eventos:
        print(f"({evento['horaParede']}) {resumo(evento)} {json.dumps(evento['detalhes'], ensure_ascii=False)}")

    # ponytail: O(n²) sobre todos os pares, ok para logs de laboratório
    concorrentes, causais = [], []
    for e1, e2 in combinations(eventos, 2):
        if e1["agencia"] == e2["agencia"]:
            continue
        relacao = comparar(e1["timestampVetorial"], e2["timestampVetorial"])
        if relacao == "CONCORRENTES":
            concorrentes.append((e1, e2))
        elif relacao in ("ANTES", "DEPOIS"):
            causais.append((e1, e2) if relacao == "ANTES" else (e2, e1))

    print("\n=== Pares de eventos CONCORRENTES entre agências diferentes ===")
    for e1, e2 in concorrentes:
        print(f"{resumo(e1)}  x  {resumo(e2)}")
    if not concorrentes:
        print("(nenhum par concorrente encontrado - gere mais eventos em paralelo e rode de novo)")

    print("\n=== Pares CAUSALMENTE relacionados entre agências diferentes (antes -> depois) ===")
    for antes, depois in causais:
        print(f"{resumo(antes)}  ->  {resumo(depois)}")

    print(f"\n{len(concorrentes)} par(es) concorrente(s), {len(causais)} par(es) causal(is)")


if __name__ == "__main__":
    main()
