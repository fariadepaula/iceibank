import 'package:flutter/services.dart';
import 'package:material_ui/material_ui.dart';

import '../services/api_client.dart';
import '../services/lideranca.dart';
import '../services/sessao.dart';
import '../widgets/painel_lideranca.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key, required this.sessao, required this.api, required this.lideranca});

  final Sessao sessao;
  final ApiClient api;
  final Lideranca lideranca;

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _conta = TextEditingController();
  final _senha = TextEditingController();
  String? _erro;
  bool _enviando = false;

  @override
  void initState() {
    super.initState();
    _erro = widget.sessao.avisoSaida;
  }

  Future<void> _entrar() async {
    final conta = int.tryParse(_conta.text);
    if (conta == null || _senha.text.isEmpty) {
      setState(() => _erro = 'Informe o número da conta e a senha.');
      return;
    }
    setState(() {
      _enviando = true;
      _erro = null;
    });
    try {
      final resposta = await widget.api.post('/auth/login', {'idConta': conta, 'senha': _senha.text}, autenticado: false);
      await widget.sessao.entrar(conta, resposta['access_token'] as String);
    } on ApiException catch (e) {
      if (mounted) setState(() => _erro = e.mensagem);
    } finally {
      if (mounted) setState(() => _enviando = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 420),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Icon(Icons.account_balance, size: 56, color: Theme.of(context).colorScheme.primary),
                  const SizedBox(height: 8),
                  Text('ICEIBank', textAlign: TextAlign.center, style: Theme.of(context).textTheme.headlineMedium),
                  const SizedBox(height: 24),
                  TextField(
                    controller: _conta,
                    decoration: const InputDecoration(labelText: 'Número da conta', border: OutlineInputBorder()),
                    keyboardType: TextInputType.number,
                    inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                    textInputAction: TextInputAction.next,
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: _senha,
                    decoration: const InputDecoration(labelText: 'Senha', border: OutlineInputBorder()),
                    obscureText: true,
                    onSubmitted: (_) => _entrar(),
                  ),
                  const SizedBox(height: 16),
                  FilledButton(
                    onPressed: _enviando ? null : _entrar,
                    child: Text(_enviando ? 'Entrando...' : 'Entrar'),
                  ),
                  if (_erro != null) ...[
                    const SizedBox(height: 12),
                    Text(_erro!, style: TextStyle(color: Theme.of(context).colorScheme.error), textAlign: TextAlign.center),
                  ],
                  const SizedBox(height: 24),
                  PainelLideranca(lideranca: widget.lideranca),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
