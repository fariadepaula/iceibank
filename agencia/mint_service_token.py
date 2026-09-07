"""Gera um token JWT de serviço, usado para criar contas e para chamadas
agência-a-agência (ver ADR 0002). Rode a partir de agencia/, com o mesmo
ICEIBANK_JWT_SECRET exportado nos processos das agências."""

from app.services.auth import criar_token_servico

if __name__ == "__main__":
    print(criar_token_servico())
