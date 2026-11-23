<script setup>
import { ref } from "vue";
import { auth } from "../auth.js";
import { api } from "../api.js";

const idConta = ref("");
const senha = ref("");
const erro = ref("");
const enviando = ref(false);

async function entrar() {
  erro.value = "";
  enviando.value = true;
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
  } finally {
    enviando.value = false;
  }
}
</script>

<template>
  <form class="cartao login" @submit.prevent="entrar">
    <h1>Entrar</h1>
    <label>
      Número da conta
      <input v-model="idConta" type="number" min="0" inputmode="numeric" required autofocus />
    </label>
    <label>
      Senha
      <input v-model="senha" type="password" required />
    </label>
    <label>
      Agência de entrada
      <select v-model.number="auth.agencia">
        <option :value="0">Agência 0</option>
        <option :value="1">Agência 1</option>
        <option :value="2">Agência 2</option>
      </select>
      <small>Qualquer uma serve. A agência repassa o pedido para a dona da conta.</small>
    </label>
    <button type="submit" class="botao-primario" :disabled="enviando">
      {{ enviando ? "Entrando..." : "Entrar" }}
    </button>
    <p v-if="erro" class="aviso erro">{{ erro }}</p>
  </form>
</template>

<style scoped>
.login {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-top: 2rem;
}

h1 {
  margin: 0;
  font-size: 1.4rem;
}

small {
  color: var(--texto-suave);
  font-size: 0.8rem;
}
</style>
