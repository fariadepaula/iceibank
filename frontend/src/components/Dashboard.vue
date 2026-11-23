<script setup>
import { ref, computed, onMounted } from "vue";
import { auth } from "../auth.js";
import { api } from "../api.js";

const saldo = ref(null);
const nomeAluno = ref("");
const carregando = ref(false);
const enviando = ref(false);
const aviso = ref(null); // { tipo: "ok" | "erro", texto }

const abas = [
  { id: "deposito", rotulo: "Depositar" },
  { id: "saque", rotulo: "Sacar" },
  { id: "transferencia", rotulo: "Transferir" },
];
const aba = ref("deposito");
const valor = ref("");
const idDestino = ref("");

const formatador = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
const saldoFormatado = computed(() => (saldo.value == null ? "..." : formatador.format(saldo.value)));
const rotuloBotao = computed(() => abas.find((a) => a.id === aba.value).rotulo);

function trocarAba(id) {
  aba.value = id;
  aviso.value = null;
}

async function carregarSaldo() {
  carregando.value = true;
  try {
    const conta = await api(`/contas/${auth.contaId}`);
    saldo.value = conta.saldo;
    nomeAluno.value = conta.nomeAluno;
  } catch (e) {
    aviso.value = { tipo: "erro", texto: e.message };
  } finally {
    carregando.value = false;
  }
}

async function enviar() {
  aviso.value = null;
  enviando.value = true;
  try {
    if (aba.value === "transferencia") {
      const resposta = await api("/transferencias", {
        method: "POST",
        body: {
          idOrigem: auth.contaId,
          idDestino: Number(idDestino.value),
          valor: Number(valor.value),
          // Idempotência (funcionalidade adicional do backend): cada envio do
          // formulário é uma operação nova, com chave própria.
          operacaoId: crypto.randomUUID(),
        },
      });
      aviso.value = { tipo: "ok", texto: resposta.mensagem };
      idDestino.value = "";
      await carregarSaldo();
    } else {
      const rota = aba.value === "deposito" ? "depositar" : "sacar";
      const conta = await api(`/contas/${auth.contaId}/${rota}`, {
        method: "POST",
        body: { valor: Number(valor.value) },
      });
      saldo.value = conta.saldo;
      const nome = aba.value === "deposito" ? "Depósito" : "Saque";
      aviso.value = { tipo: "ok", texto: `${nome} de ${formatador.format(Number(valor.value))} concluído.` };
    }
    valor.value = "";
  } catch (e) {
    aviso.value = { tipo: "erro", texto: e.message };
  } finally {
    enviando.value = false;
  }
}

onMounted(carregarSaldo);
</script>

<template>
  <section class="cartao saldo">
    <div>
      <p class="nome">{{ nomeAluno || "Saldo" }}</p>
      <p class="valor" :class="{ carregando }">{{ saldoFormatado }}</p>
    </div>
    <button class="botao-texto" :disabled="carregando" @click="carregarSaldo">Atualizar</button>
  </section>

  <section class="cartao operacoes">
    <div class="abas" role="tablist">
      <button
        v-for="a in abas"
        :key="a.id"
        role="tab"
        :aria-selected="aba === a.id"
        :class="{ ativa: aba === a.id }"
        @click="trocarAba(a.id)"
      >
        {{ a.rotulo }}
      </button>
    </div>

    <form @submit.prevent="enviar">
      <label v-if="aba === 'transferencia'">
        Conta de destino
        <input v-model="idDestino" type="number" min="0" inputmode="numeric" required />
      </label>
      <label>
        Valor (R$)
        <input v-model="valor" type="number" min="0.01" step="0.01" inputmode="decimal" required />
      </label>
      <p v-if="aba === 'transferencia'" class="dica">
        Para conta de outra agência, o crédito chega pela fila e pode levar alguns instantes.
      </p>
      <button type="submit" class="botao-primario" :disabled="enviando">
        {{ enviando ? "Enviando..." : rotuloBotao }}
      </button>
    </form>

    <p v-if="aviso" class="aviso" :class="aviso.tipo">{{ aviso.texto }}</p>
  </section>
</template>

<style scoped>
.saldo {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1rem;
}

.nome {
  margin: 0;
  color: var(--texto-suave);
}

.valor {
  margin: 0.25rem 0 0;
  font-size: 2.25rem;
  font-weight: 600;
  letter-spacing: -0.01em;
  transition: opacity 0.2s;
}

.valor.carregando {
  opacity: 0.5;
}

.operacoes {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.abas {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  border: 1px solid var(--borda);
  border-radius: 999px;
  overflow: hidden;
}

.abas button {
  border-radius: 0;
  background: transparent;
  color: var(--texto);
  padding: 0.55rem 0.5rem;
}

.abas button + button {
  border-left: 1px solid var(--borda);
}

.abas button.ativa {
  background: var(--primaria-suave);
  color: var(--primaria);
  font-weight: 600;
}

form {
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
}

.dica {
  margin: 0;
  font-size: 0.85rem;
  color: var(--texto-suave);
}
</style>
