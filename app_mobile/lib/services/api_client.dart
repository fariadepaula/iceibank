import 'dart:async';
import 'dart:convert';
import 'dart:math';

import 'package:http/http.dart' as http;

import '../config.dart';
import 'sessao.dart';

class ApiException implements Exception {
  ApiException(this.mensagem, {this.status, this.corpo = const {}});

  final String mensagem;

  /// null quando nenhuma agência respondeu (sem conexão).
  final int? status;
  final Map<String, dynamic> corpo;

  bool get semConexao => status == null;

  @override
  String toString() => mensagem;
}

/// Cliente da API do ICEIBank. Qualquer agência serve de porta de entrada (o
/// backend encaminha para a dona da conta), então se uma não responde o
/// cliente tenta a próxima das 3 conhecidas.
class ApiClient {
  ApiClient(this.sessao, {http.Client? cliente}) : _http = cliente ?? http.Client();

  final Sessao sessao;
  final http.Client _http;
  int _agenciaPreferida = 0;

  /// Agência que respondeu por último (exibida na tela, só informativo).
  int get agenciaAtual => _agenciaPreferida;

  Future<Map<String, dynamic>> get(String caminho) => _requisitar('GET', caminho);

  Future<Map<String, dynamic>> post(String caminho, Map<String, dynamic> corpo, {bool autenticado = true}) =>
      _requisitar('POST', caminho, corpo: corpo, autenticado: autenticado);

  Future<Map<String, dynamic>> _requisitar(
    String metodo,
    String caminho, {
    Map<String, dynamic>? corpo,
    bool autenticado = true,
  }) async {
    final cabecalhos = {'Content-Type': 'application/json'};
    if (autenticado && sessao.token != null) cabecalhos['Authorization'] = 'Bearer ${sessao.token}';

    for (var tentativa = 0; tentativa < numeroAgencias; tentativa++) {
      final agencia = (_agenciaPreferida + tentativa) % numeroAgencias;
      final http.Response resposta;
      try {
        final requisicao = http.Request(metodo, urlAgencia(agencia, caminho))..headers.addAll(cabecalhos);
        if (corpo != null) requisicao.body = jsonEncode(corpo);
        resposta = await http.Response.fromStream(await _http.send(requisicao)).timeout(const Duration(seconds: 5));
      } on http.ClientException {
        continue; // conexão recusada: a requisição nem chegou, é seguro tentar outra agência
      } on TimeoutException {
        // A requisição pode ter sido aplicada e só a resposta se perdeu: repetir
        // um POST noutra agência poderia aplicar duas vezes. Só GET é repetido.
        if (metodo == 'GET') continue;
        throw ApiException('A agência demorou para responder. Confira o saldo antes de tentar de novo.');
      }
      _agenciaPreferida = agencia;
      return _tratar(resposta);
    }
    throw ApiException('Nenhuma agência respondeu. Verifique sua conexão.');
  }

  Future<Map<String, dynamic>> _tratar(http.Response resposta) async {
    Map<String, dynamic> dados;
    try {
      final decodificado = jsonDecode(utf8.decode(resposta.bodyBytes));
      dados = decodificado is Map<String, dynamic> ? decodificado : {'dados': decodificado};
    } on FormatException {
      dados = {};
    }

    if (resposta.statusCode >= 200 && resposta.statusCode < 300) return dados;

    final detalhe = dados['detail'];
    final mensagem = detalhe is String ? detalhe : 'Erro ${resposta.statusCode}.';
    if (resposta.statusCode == 401 && sessao.autenticada) {
      await sessao.sair(aviso: 'Sessão expirada, faça login novamente.');
    }
    throw ApiException(mensagem, status: resposta.statusCode, corpo: dados);
  }
}

final _aleatorio = Random.secure();

/// Identificador único de operação: torna transferências e sincronizações
/// idempotentes no backend (reenviar não aplica duas vezes).
String novoOperacaoId() => List.generate(16, (_) => _aleatorio.nextInt(256).toRadixString(16).padLeft(2, '0')).join();
