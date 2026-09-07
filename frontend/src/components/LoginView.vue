<script setup>
import { ref } from "vue";
import { auth } from "../auth.js";
import { api } from "../api.js";

const idConta = ref("");
const senha = ref("");
const erro = ref("");

async function entrar() {
  erro.value = "";
  try {
    const resposta = await api("/auth/login", {
      method: "POST",
      body: { idConta: Number(idConta.value), senha: senha.value },
      auth: false,
    });
    auth.contaId = Number(idConta.value);
    auth.token = resposta.access_token;
  } catch (e) {
    erro.value = e.message;
  }
}
</script>

<template>
  <form @submit.prevent="entrar">
    <label>
      Agência (porta de entrada)
      <select v-model.number="auth.agencia">
        <option :value="0">Agência 0</option>
        <option :value="1">Agência 1</option>
        <option :value="2">Agência 2</option>
      </select>
    </label>
    <label>
      Número da conta
      <input v-model="idConta" type="number" required />
    </label>
    <label>
      Senha
      <input v-model="senha" type="password" required />
    </label>
    <button type="submit">Entrar</button>
    <p v-if="erro" class="erro">{{ erro }}</p>
  </form>
</template>
