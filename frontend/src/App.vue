<script setup>
import { auth, logout } from "./auth.js";
import LoginView from "./components/LoginView.vue";
import Dashboard from "./components/Dashboard.vue";
</script>

<template>
  <header class="topo">
    <div class="marca">
      <svg class="logo" viewBox="0 0 24 24" width="24" height="24" aria-hidden="true">
        <path fill="currentColor" d="M12 2 2 7v2h20V7L12 2Zm-7 9v7h2v-7H5Zm4 0v7h2v-7H9Zm4 0v7h2v-7h-2Zm4 0v7h2v-7h-2ZM2 20v2h20v-2H2Z" />
      </svg>
      <span>ICEIBank</span>
    </div>
    <div v-if="auth.token" class="sessao">
      <span>Conta {{ auth.contaId }} · Agência {{ auth.agencia }}</span>
      <button class="botao-texto" @click="logout">Sair</button>
    </div>
  </header>
  <main class="conteudo">
    <LoginView v-if="!auth.token" />
    <Dashboard v-else />
  </main>
</template>

<style scoped>
.topo {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 0.5rem 1rem;
  padding: 0.75rem 1rem;
  background: var(--superficie);
  border-bottom: 1px solid var(--borda);
}

.marca {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 1.15rem;
  font-weight: 700;
  color: var(--primaria);
}

.sessao {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  font-size: 0.9rem;
  color: var(--texto-suave);
}

.conteudo {
  max-width: 520px;
  margin: 0 auto;
  padding: 1.5rem 1rem 3rem;
}
</style>
