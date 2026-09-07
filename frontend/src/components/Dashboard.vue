<script setup>
import { ref, onMounted } from "vue";
import { auth, logout } from "../auth.js";
import { api } from "../api.js";

const saldo = ref(null);
const nomeAluno = ref("");
const mensagem = ref("");
const erro = ref("");

const valorDeposito = ref("");
const valorSaque = ref("");
const transferencia = ref({ idDestino: "", valor: "" });

async function carregarSaldo() {
  erro.value = "";
  try {
    const conta = await api(`/contas/${auth.contaId}`);
    saldo.value = conta.saldo;
    nomeAluno.value = conta.nomeAluno;
  } catch (e) {
    erro.value = e.message;
  }
}

async function depositar() {
  erro.value = "";
  mensagem.value = "";
  try {
    const conta = await api(`/contas/${auth.contaId}/depositar`, {
      method: "POST",
      body: { valor: Number(valorDeposito.value) },
    });
    saldo.value = conta.saldo;
    mensagem.value = "Depósito concluído.";
    valorDeposito.value = "";
  } catch (e) {
    erro.value = e.message;
  }
}

async function sacar() {
  erro.value = "";
  mensagem.value = "";
  try {
    const conta = await api(`/contas/${auth.contaId}/sacar`, {
      method: "POST",
      body: { valor: Number(valorSaque.value) },
    });
    saldo.value = conta.saldo;
    mensagem.value = "Saque concluído.";
    valorSaque.value = "";
  } catch (e) {
    erro.value = e.message;
  }
}

async function transferir() {
  erro.value = "";
  mensagem.value = "";
  try {
    const resposta = await api("/transferencias", {
      method: "POST",
      body: {
        idOrigem: auth.contaId,
        idDestino: Number(transferencia.value.idDestino),
        valor: Number(transferencia.value.valor),
        // Idempotência (funcionalidade adicional do backend): cada envio gera
        // uma chave nova; um reenvio acidental do mesmo clique reusaria esta,
        // mas aqui cada submit do formulário é uma operação nova de fato.
        operacaoId: crypto.randomUUID(),
      },
    });
    mensagem.value = resposta.mensagem;
    transferencia.value = { idDestino: "", valor: "" };
    await carregarSaldo();
  } catch (e) {
    erro.value = e.message;
  }
}

onMounted(carregarSaldo);
</script>

<template>
  <div>
    <p>
      Conta {{ auth.contaId }} — Agência {{ auth.agencia }}
      <button @click="logout">Sair</button>
    </p>
    <h2>{{ nomeAluno }} — saldo: {{ saldo }}</h2>

    <form @submit.prevent="depositar">
      <strong>Depositar</strong>
      <input v-model="valorDeposito" type="number" step="0.01" placeholder="Valor" required />
      <button type="submit">Depositar</button>
    </form>

    <form @submit.prevent="sacar">
      <strong>Sacar</strong>
      <input v-model="valorSaque" type="number" step="0.01" placeholder="Valor" required />
      <button type="submit">Sacar</button>
    </form>

    <form @submit.prevent="transferir">
      <strong>Transferir (local ou entre agências — o backend decide)</strong>
      <input v-model="transferencia.idDestino" type="number" placeholder="Conta destino" required />
      <input v-model="transferencia.valor" type="number" step="0.01" placeholder="Valor" required />
      <button type="submit">Transferir</button>
    </form>

    <p v-if="mensagem" class="ok">{{ mensagem }}</p>
    <p v-if="erro" class="erro">{{ erro }}</p>
  </div>
</template>
