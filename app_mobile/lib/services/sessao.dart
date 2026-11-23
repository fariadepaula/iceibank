import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Token JWT e conta logada, persistidos para sobreviver a um reinício do app.
class Sessao extends ChangeNotifier {
  static const _chaveToken = 'iceibank_token';
  static const _chaveConta = 'iceibank_conta_id';

  String? token;
  int? contaId;

  /// Motivo da última saída forçada (ex.: token expirado), exibido no login.
  String? avisoSaida;

  bool get autenticada => token != null && contaId != null;

  Future<void> carregar() async {
    final prefs = await SharedPreferences.getInstance();
    token = prefs.getString(_chaveToken);
    contaId = prefs.getInt(_chaveConta);
    notifyListeners();
  }

  Future<void> entrar(int conta, String novoToken) async {
    token = novoToken;
    contaId = conta;
    avisoSaida = null;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_chaveToken, novoToken);
    await prefs.setInt(_chaveConta, conta);
    notifyListeners();
  }

  Future<void> sair({String? aviso}) async {
    token = null;
    contaId = null;
    avisoSaida = aviso;
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_chaveToken);
    await prefs.remove(_chaveConta);
    notifyListeners();
  }
}
