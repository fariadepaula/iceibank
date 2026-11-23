import 'package:hive_ce_flutter/hive_ce_flutter.dart';

/// Operação de escrita feita sem conexão, esperando para ser sincronizada.
class OperacaoPendente {
  OperacaoPendente({
    required this.operacaoId,
    required this.contaId,
    required this.tipo,
    required this.valor,
    required this.vetorConhecido,
    required this.criadaEm,
    this.conflito = false,
  });

  final String operacaoId;
  final int contaId;
  final String tipo; // DEPOSITO | SAQUE
  final double valor;

  /// Vetor da agência que o app conhecia quando a operação foi feita.
  List<int> vetorConhecido;
  final DateTime criadaEm;

  /// A agência recusou (409): espera a decisão da pessoa usuária.
  bool conflito;

  /// Efeito esperado no saldo (UI otimista).
  double get efeito => tipo == 'DEPOSITO' ? valor : -valor;

  Map<String, dynamic> paraMapa() => {
        'operacaoId': operacaoId,
        'contaId': contaId,
        'tipo': tipo,
        'valor': valor,
        'vetorConhecido': vetorConhecido,
        'criadaEm': criadaEm.toIso8601String(),
        'conflito': conflito,
      };

  factory OperacaoPendente.deMapa(Map mapa) => OperacaoPendente(
        operacaoId: mapa['operacaoId'] as String,
        contaId: mapa['contaId'] as int,
        tipo: mapa['tipo'] as String,
        valor: (mapa['valor'] as num).toDouble(),
        vetorConhecido: List<int>.from(mapa['vetorConhecido'] as List),
        criadaEm: DateTime.parse(mapa['criadaEm'] as String),
        conflito: mapa['conflito'] as bool? ?? false,
      );
}

/// Último estado confirmado pela agência, para a tela funcionar sem conexão.
class ContaEmCache {
  ContaEmCache({required this.saldo, required this.nomeAluno, required this.vetorAtual, required this.lidaEm});

  final double saldo;
  final String? nomeAluno;
  final List<int> vetorAtual;
  final DateTime lidaEm;

  factory ContaEmCache.daApi(Map<String, dynamic> conta) => ContaEmCache(
        saldo: (conta['saldo'] as num).toDouble(),
        nomeAluno: conta['nomeAluno'] as String?,
        vetorAtual: List<int>.from(conta['vetorAtual'] as List),
        lidaEm: DateTime.now(),
      );

  Map<String, dynamic> paraMapa() => {
        'saldo': saldo,
        'nomeAluno': nomeAluno,
        'vetorAtual': vetorAtual,
        'lidaEm': lidaEm.toIso8601String(),
      };

  factory ContaEmCache.deMapa(Map mapa) => ContaEmCache(
        saldo: (mapa['saldo'] as num).toDouble(),
        nomeAluno: mapa['nomeAluno'] as String?,
        vetorAtual: List<int>.from(mapa['vetorAtual'] as List),
        lidaEm: DateTime.parse(mapa['lidaEm'] as String),
      );
}

/// Armazenamento local com Hive: funciona igual em Android, Linux e web
/// (IndexedDB), sem gerar código nem esquema SQL.
class Armazenamento {
  late final Box<Map> _contas;
  late final Box<Map> _pendentes;

  Future<void> abrir() async {
    await Hive.initFlutter('iceibank');
    _contas = await Hive.openBox<Map>('contas');
    _pendentes = await Hive.openBox<Map>('pendentes');
  }

  ContaEmCache? conta(int id) {
    final mapa = _contas.get(id);
    return mapa == null ? null : ContaEmCache.deMapa(mapa);
  }

  Future<void> salvarConta(int id, ContaEmCache conta) => _contas.put(id, conta.paraMapa());

  /// Em ordem de criação: a fila precisa ser aplicada na ordem em que foi feita.
  List<OperacaoPendente> pendentes(int contaId) => _pendentes.values
      .map(OperacaoPendente.deMapa)
      .where((op) => op.contaId == contaId)
      .toList()
    ..sort((a, b) => a.criadaEm.compareTo(b.criadaEm));

  Future<void> salvarPendente(OperacaoPendente op) => _pendentes.put(op.operacaoId, op.paraMapa());

  Future<void> removerPendente(String operacaoId) => _pendentes.delete(operacaoId);
}
