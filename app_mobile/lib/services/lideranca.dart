import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

import '../config.dart';

/// Consulta GET /bully/lider periodicamente. Se a agência consultada não
/// responde, tenta as outras antes de desistir.
class Lideranca extends ChangeNotifier {
  Lideranca({http.Client? cliente}) : _http = cliente ?? http.Client();

  final http.Client _http;
  Timer? _timer;
  int _proximaConsultada = 0;

  /// null = eleição em andamento (a agência ainda não conhece a líder).
  int? lider;
  int? agenciaConsultada;
  DateTime? atualizadoEm;
  bool semResposta = false;

  /// Funcionalidade adicional: trocas de liderança vistas pelo app, mais recente primeiro.
  final List<({int lider, DateTime desde})> historico = [];
  static const _tamanhoHistorico = 10;

  void iniciar() {
    _timer ??= Timer.periodic(intervaloLideranca, (_) => consultar());
    consultar();
  }

  Future<void> consultar() async {
    for (var tentativa = 0; tentativa < numeroAgencias; tentativa++) {
      final agencia = (_proximaConsultada + tentativa) % numeroAgencias;
      try {
        final resposta = await _http.get(urlAgencia(agencia, '/bully/lider')).timeout(const Duration(seconds: 1));
        if (resposta.statusCode != 200) continue;
        final dados = jsonDecode(resposta.body) as Map<String, dynamic>;
        _proximaConsultada = agencia;
        lider = dados['liderAtual'] as int?;
        if (lider != null && (historico.isEmpty || historico.first.lider != lider)) {
          historico.insert(0, (lider: lider!, desde: DateTime.now()));
          if (historico.length > _tamanhoHistorico) historico.removeLast();
        }
        agenciaConsultada = agencia;
        atualizadoEm = DateTime.now();
        semResposta = false;
        notifyListeners();
        return;
      } on Exception {
        continue; // fora do ar ou lenta: tenta a próxima
      }
    }
    semResposta = true;
    atualizadoEm = DateTime.now();
    notifyListeners();
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }
}
