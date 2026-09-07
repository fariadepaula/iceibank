import { reactive, watch } from "vue";

// Estado global simples (Model): não usamos Pinia por um único token/agência
// não justificar uma lib de state management - localStorage é a persistência,
// este objeto reativo é só o espelho em memória que os componentes observam.
export const auth = reactive({
  token: localStorage.getItem("iceibank_token") || null,
  contaId: localStorage.getItem("iceibank_conta_id")
    ? Number(localStorage.getItem("iceibank_conta_id"))
    : null,
  agencia: Number(localStorage.getItem("iceibank_agencia") || 0),
});

watch(
  () => auth.token,
  (valor) => {
    if (valor) localStorage.setItem("iceibank_token", valor);
    else localStorage.removeItem("iceibank_token");
  },
);
watch(
  () => auth.contaId,
  (valor) => {
    if (valor != null) localStorage.setItem("iceibank_conta_id", String(valor));
  },
);
watch(
  () => auth.agencia,
  (valor) => localStorage.setItem("iceibank_agencia", String(valor)),
);

export function logout() {
  auth.token = null;
  auth.contaId = null;
}
