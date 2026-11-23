import json

from mesclar_logs import carregar_eventos

TIPOS_BULLY = {"ELEICAO_INICIADA", "ELEICAO_RECEBIDA", "TORNOU_LIDER", "LIDER_ANUNCIADO", "LIDER_NAO_RESPONDEU"}


def main():
    eventos = [e for e in carregar_eventos() if e["tipo"] in TIPOS_BULLY]
    eventos.sort(key=lambda e: e["horaParede"])

    print("=== Histórico de eventos de eleição ===")
    for evento in eventos:
        print(f"({evento['horaParede']}) [{evento['agencia']}] {evento['tipo']} {json.dumps(evento['detalhes'], ensure_ascii=False)}")

    print("\n=== Linha do tempo de líderes ===")
    for evento in eventos:
        if evento["tipo"] == "TORNOU_LIDER":
            print(f"A partir de {evento['horaParede']}: Agência {evento['detalhes']['idAgencia']} é a líder")


if __name__ == "__main__":
    main()
