import 'dart:async';

import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:flutter/foundation.dart';

import 'api_client.dart';
import 'armazenamento.dart';

/// Saldo, depósito e saque em modo offline-first para a conta logada.
///
/// - Lê da agência quando dá e guarda a cópia local (saldo + vetorAtual).
/// - Sem conexão, depósito/saque entram numa fila local com o vetor conhecido
///   e o saldo exibido já reflete o efeito (provisório, marcado como pendente).
/// - Quando a conectividade volta (ou a cada poucos segundos, enquanto houver
///   fila), sincroniza sozinho via POST /contas/{id}/sincronizar.
/// - 409: a operação fica marcada como conflito e a fila pausa até a pessoa
///   decidir (descartar ou reaplicar sobre o saldo real).
class ContaOffline extends ChangeNotifier {
  ContaOffline({required this.contaId, required this.api, required this.armazenamento, Connectivity? conectividade})
      : _conectividade = conectividade ?? Connectivity() {
    cache = armazenamento.conta(contaId);
    pendentes = armazenamento.pendentes(contaId);
    _assinatura = _conectividade.onConnectivityChanged.listen((estado) {
      if (!estado.contains(ConnectivityResult.none)) sincronizar();
    });
    // A conectividade do aparelho pode voltar sem a agência ter voltado (ou o
    // contrário), então enquanto houver fila o app tenta de tempos em tempos.
    _retentativa = Timer.periodic(const Duration(seconds: 5), (_) {
      if (pendentes.any((op) => !op.conflito)) sincronizar();
    });
  }

  final int contaId;
  final ApiClient api;
  final Armazenamento armazenamento;
  final Connectivity _conectividade;
  late final StreamSubscription<List<ConnectivityResult>> _assinatura;
  late final Timer _retentativa;

  ContaEmCache? cache;
  List<OperacaoPendente> pendentes = [];
  bool online = true;
  bool sincronizando = false;

  /// Mensagem do último conflito, para a tela avisar de forma visível.
  String? avisoConflito;

  bool get temConflito => pendentes.any((op) => op.conflito);

  /// Saldo confirmado pela agência + efeito das operações ainda não sincronizadas.
  double? get saldoProvisorio =>
      cache == null ? null : pendentes.where((op) => !op.conflito).fold<double>(cache!.saldo, (s, op) => s + op.efeito);

  Future<void> _guardar(Map<String, dynamic> conta) async {
    cache = ContaEmCache.daApi(conta);
    await armazenamento.salvarConta(contaId, cache!);
  }

  /// Lê o saldo da agência. Sem conexão, mantém o último dado conhecido.
  Future<void> atualizar() async {
    try {
      await _guardar(await api.get('/contas/$contaId'));
      online = true;
    } on ApiException catch (e) {
      if (!e.semConexao) rethrow;
      online = false;
    } finally {
      notifyListeners();
    }
    if (online) await sincronizar();
  }

  /// Retorna true se aplicou na hora, false se ficou pendente.
  Future<bool> registrar(String tipo, double valor) async {
    if (tipo == 'SAQUE' && (saldoProvisorio ?? 0) < valor) {
      throw ApiException('Saldo insuficiente (considerando operações pendentes).');
    }
    // Com fila pendente, a operação nova vai para o fim dela: aplicar direto
    // furaria a ordem em que a pessoa fez as operações.
    if (online && pendentes.isEmpty) {
      try {
        await _guardar(await api.post('/contas/$contaId/${tipo == 'DEPOSITO' ? 'depositar' : 'sacar'}', {'valor': valor}));
        notifyListeners();
        return true;
      } on ApiException catch (e) {
        if (!e.semConexao) rethrow;
        online = false;
      }
    }
    if (cache == null) throw ApiException('Sem conexão e sem saldo conhecido: consulte o saldo online ao menos uma vez.');

    final op = OperacaoPendente(
      operacaoId: novoOperacaoId(),
      contaId: contaId,
      tipo: tipo,
      valor: valor,
      vetorConhecido: List.of(cache!.vetorAtual),
      criadaEm: DateTime.now(),
    );
    await armazenamento.salvarPendente(op);
    pendentes = [...pendentes, op];
    notifyListeners();
    return false;
  }

  Future<void> sincronizar() async {
    if (sincronizando || pendentes.isEmpty || temConflito) return;
    sincronizando = true;
    notifyListeners();
    try {
      for (final op in List.of(pendentes)) {
        final Map<String, dynamic> conta;
        try {
          conta = await api.post('/contas/$contaId/sincronizar', {
            'tipo': op.tipo,
            'valor': op.valor,
            'vetorConhecido': op.vetorConhecido,
            'operacaoId': op.operacaoId,
          });
        } on ApiException catch (e) {
          if (e.semConexao) {
            online = false;
            return;
          }
          online = true;
          if (e.status == 409) {
            await _marcarConflito(op, e);
          } else {
            // Recusa definitiva (ex.: saldo insuficiente): não adianta repetir
            await _marcarConflito(op, e, mensagem: 'Operação recusada pela agência: ${e.mensagem}');
          }
          return;
        }
        online = true;
        final vetorAnterior = List.of(op.vetorConhecido);
        await _guardar(conta);
        await armazenamento.removerPendente(op.operacaoId);
        pendentes = pendentes.where((p) => p.operacaoId != op.operacaoId).toList();
        // As próximas operações foram feitas sobre a mesma leitura; a mudança no
        // vetor agora é a nossa própria operação, não de outra pessoa.
        for (final proxima in pendentes) {
          if (listEquals(proxima.vetorConhecido, vetorAnterior)) {
            proxima.vetorConhecido = List.of(cache!.vetorAtual);
            await armazenamento.salvarPendente(proxima);
          }
        }
        notifyListeners();
      }
    } finally {
      sincronizando = false;
      notifyListeners();
    }
  }

  Future<void> _marcarConflito(OperacaoPendente op, ApiException erro, {String? mensagem}) async {
    final contaAtual = erro.corpo['contaAtual'];
    if (contaAtual is Map<String, dynamic>) await _guardar(contaAtual);
    op.conflito = true;
    await armazenamento.salvarPendente(op);
    avisoConflito = mensagem ??
        'A conta mudou na agência enquanto você estava offline. '
            'O ${op.tipo == 'DEPOSITO' ? 'depósito' : 'saque'} de R\$ ${op.valor.toStringAsFixed(2).replaceAll('.', ',')} '
            'não foi aplicado automaticamente.';
  }

  /// A pessoa viu o saldo real e decidiu aplicar mesmo assim.
  Future<void> reaplicar(OperacaoPendente op) async {
    op
      ..conflito = false
      ..vetorConhecido = List.of(cache!.vetorAtual);
    await armazenamento.salvarPendente(op);
    if (!temConflito) avisoConflito = null;
    notifyListeners();
    await sincronizar();
  }

  Future<void> descartar(OperacaoPendente op) async {
    await armazenamento.removerPendente(op.operacaoId);
    pendentes = pendentes.where((p) => p.operacaoId != op.operacaoId).toList();
    if (!temConflito) avisoConflito = null;
    notifyListeners();
    await sincronizar();
  }

  @override
  void dispose() {
    _assinatura.cancel();
    _retentativa.cancel();
    super.dispose();
  }
}
