import json
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


class RegistroEventos:
    def __init__(self, nome_agencia: str):
        self.nome_agencia = nome_agencia
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.caminho_arquivo = DATA_DIR / f"eventos-{nome_agencia}.jsonl"

    def registrar(self, tipo: str, timestamp_vetorial: list[int], detalhes: dict) -> dict:
        evento = {
            "agencia": self.nome_agencia,
            "tipo": tipo,
            "timestampVetorial": timestamp_vetorial,
            "horaParede": datetime.now(timezone.utc).isoformat(),
            "detalhes": detalhes,
        }
        with open(self.caminho_arquivo, "a", encoding="utf-8") as arquivo:
            arquivo.write(json.dumps(evento, ensure_ascii=False) + "\n")
        print(f"[Vetor {timestamp_vetorial}] {tipo} {detalhes}")
        return evento
