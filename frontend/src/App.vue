<script setup>
import { auth } from "./auth.js";
import LoginView from "./components/LoginView.vue";
import Dashboard from "./components/Dashboard.vue";
</script>

<template>
  <main>
    <h1>ICEIBank</h1>
    <LoginView v-if="!auth.token" />
    <Dashboard v-else />
  </main>
</template>

<style>
body {
  font-family: system-ui, sans-serif;
  max-width: 480px;
  margin: 2rem auto;
  padding: 0 1rem;
}
form {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  margin: 1rem 0;
  padding: 0.75rem;
  border: 1px solid #ccc;
  border-radius: 6px;
}
input,
select,
button {
  font-size: 1rem;
  padding: 0.4rem;
}
.erro {
  color: #b00020;
}
.ok {
  color: #0a7d28;
}
</style>
