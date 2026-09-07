import { auth, logout } from "./auth.js";

// Espelha o config.js do backend - cada agência é a "porta de entrada"
// escolhida no login (seção 12.1: o frontend precisa apontar pra qualquer uma).
const BASES = {
  0: "http://localhost:4000",
  1: "http://localhost:4001",
  2: "http://localhost:4002",
};

export async function api(caminho, { method = "GET", body, auth: exigeAuth = true } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (exigeAuth && auth.token) headers.Authorization = `Bearer ${auth.token}`;

  const resposta = await fetch(`${BASES[auth.agencia]}${caminho}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  const dados = await resposta.json().catch(() => ({}));

  if (resposta.status === 401) {
    logout();
    throw new Error(dados.detail || "Sessão expirada, faça login novamente.");
  }
  if (!resposta.ok) {
    throw new Error(dados.detail || `Erro ${resposta.status}.`);
  }
  return dados;
}
