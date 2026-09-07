import json
from pathlib import Path

PASTA_DADOS = Path(__file__).resolve().parent / "data"


def carregar_eventos() -> list[dict]:
    eventos = []
    for arquivo in sorted(PASTA_DADOS.glob("*.jsonl")):
        linhas = arquivo.read_text(encoding="utf-8").strip().splitlines()
        eventos.extend(json.loads(linha) for linha in linhas if linha)
    return eventos


def main():
    eventos = sorted(carregar_eventos(), key=lambda e: e["timestampLamport"])
    print("=== Linha do tempo unificada (ordenada por relogio de Lamport) ===")
    for evento in eventos:
        detalhes = json.dumps(evento["detalhes"], ensure_ascii=False)
        print(f"[Lamport {evento['timestampLamport']}] ({evento['horaParede']}) {evento['agencia']} - {evento['tipo']} {detalhes}")


if __name__ == "__main__":
    main()
