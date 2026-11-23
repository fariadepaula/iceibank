import 'package:flutter/services.dart';
import 'package:material_ui/material_ui.dart';

import '../services/api_client.dart';
import '../services/lideranca.dart';
import '../services/sessao.dart';
import '../widgets/painel_lideranca.dart';

enum _Operacao { deposito, saque }

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key, required this.sessao, required this.api, required this.lideranca});

  final Sessao sessao;
  final ApiClient api;
  final Lideranca lideranca;

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  double? _saldo;
  String? _nome;
  String? _erroSaldo;
  bool _carregando = false;

  _Operacao _operacao = _Operacao.deposito;
  final _valor = TextEditingController();
  final _destino = TextEditingController();
  final _valorTransferencia = TextEditingController();
  bool _enviando = false;

  int get _conta => widget.sessao.contaId!;

  @override
  void initState() {
    super.initState();
    _atualizarSaldo();
  }

  void _aplicarConta(Map<String, dynamic> conta) {
    _saldo = (conta['saldo'] as num).toDouble();
    _nome = conta['nomeAluno'] as String?;
    _erroSaldo = null;
  }

  Future<void> _atualizarSaldo() async {
    setState(() => _carregando = true);
    try {
      final conta = await widget.api.get('/contas/$_conta');
      if (mounted) setState(() => _aplicarConta(conta));
    } on ApiException catch (e) {
      if (mounted) setState(() => _erroSaldo = e.mensagem);
    } finally {
      if (mounted) setState(() => _carregando = false);
    }
  }

  double? _lerValor(TextEditingController campo) {
    final valor = double.tryParse(campo.text.replaceAll(',', '.'));
    if (valor == null || valor <= 0) {
      _avisar('Informe um valor maior que zero.', erro: true);
      return null;
    }
    return valor;
  }

  Future<void> _executar(Future<void> Function() acao) async {
    setState(() => _enviando = true);
    try {
      await acao();
    } on ApiException catch (e) {
      _avisar(e.mensagem, erro: true);
    } finally {
      if (mounted) setState(() => _enviando = false);
    }
  }

  Future<void> _depositarOuSacar() async {
    final valor = _lerValor(_valor);
    if (valor == null) return;
    final rota = _operacao == _Operacao.deposito ? 'depositar' : 'sacar';
    await _executar(() async {
      final conta = await widget.api.post('/contas/$_conta/$rota', {'valor': valor});
      setState(() => _aplicarConta(conta));
      _valor.clear();
      _avisar(_operacao == _Operacao.deposito ? 'Depósito realizado.' : 'Saque realizado.');
    });
  }

  Future<void> _transferir() async {
    final destino = int.tryParse(_destino.text);
    if (destino == null) {
      _avisar('Informe a conta de destino.', erro: true);
      return;
    }
    final valor = _lerValor(_valorTransferencia);
    if (valor == null) return;
    await _executar(() async {
      final resposta = await widget.api.post('/transferencias', {
        'idOrigem': _conta,
        'idDestino': destino,
        'valor': valor,
        'operacaoId': novoOperacaoId(),
      });
      _destino.clear();
      _valorTransferencia.clear();
      _avisar(resposta['mensagem'] as String? ?? 'Transferência enviada.');
      await _atualizarSaldo();
    });
  }

  void _avisar(String mensagem, {bool erro = false}) {
    if (!mounted) return;
    final cores = Theme.of(context).colorScheme;
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(SnackBar(
        content: Text(mensagem, style: erro ? TextStyle(color: cores.onErrorContainer) : null),
        backgroundColor: erro ? cores.errorContainer : null,
      ));
  }

  @override
  Widget build(BuildContext context) {
    final tema = Theme.of(context);
    return Scaffold(
      appBar: AppBar(
        title: Text('Conta $_conta'),
        actions: [
          IconButton(tooltip: 'Atualizar saldo', onPressed: _carregando ? null : _atualizarSaldo, icon: const Icon(Icons.refresh)),
          IconButton(tooltip: 'Sair', onPressed: () => widget.sessao.sair(), icon: const Icon(Icons.logout)),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _atualizarSaldo,
        child: ListView(
          // Largura de celular mesmo em tela grande (web/desktop)
          padding: EdgeInsets.symmetric(
            horizontal: MediaQuery.sizeOf(context).width > 592 ? (MediaQuery.sizeOf(context).width - 560) / 2 : 16,
            vertical: 16,
          ),
          children: [
            PainelLideranca(lideranca: widget.lideranca),
            const SizedBox(height: 8),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(20),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(_nome ?? 'Saldo', style: tema.textTheme.titleMedium),
                    const SizedBox(height: 4),
                    if (_saldo != null)
                      Text(_formatarReais(_saldo!), style: tema.textTheme.displaySmall)
                    else if (_carregando)
                      const LinearProgressIndicator(),
                    if (_erroSaldo != null)
                      Padding(
                        padding: const EdgeInsets.only(top: 8),
                        child: Text(_erroSaldo!, style: TextStyle(color: tema.colorScheme.error)),
                      ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 8),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    SegmentedButton<_Operacao>(
                      segments: const [
                        ButtonSegment(value: _Operacao.deposito, label: Text('Depósito'), icon: Icon(Icons.south_west)),
                        ButtonSegment(value: _Operacao.saque, label: Text('Saque'), icon: Icon(Icons.north_east)),
                      ],
                      selected: {_operacao},
                      onSelectionChanged: (s) => setState(() => _operacao = s.first),
                    ),
                    const SizedBox(height: 12),
                    _campoValor(_valor, 'Valor'),
                    const SizedBox(height: 12),
                    FilledButton(
                      onPressed: _enviando ? null : _depositarOuSacar,
                      child: Text(_operacao == _Operacao.deposito ? 'Depositar' : 'Sacar'),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 8),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Text('Transferência', style: tema.textTheme.titleMedium),
                    const SizedBox(height: 12),
                    TextField(
                      controller: _destino,
                      decoration: const InputDecoration(labelText: 'Conta de destino', border: OutlineInputBorder()),
                      keyboardType: TextInputType.number,
                      inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                    ),
                    const SizedBox(height: 12),
                    _campoValor(_valorTransferencia, 'Valor da transferência'),
                    const SizedBox(height: 12),
                    FilledButton.tonal(onPressed: _enviando ? null : _transferir, child: const Text('Transferir')),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _campoValor(TextEditingController controle, String rotulo) => TextField(
        controller: controle,
        decoration: InputDecoration(labelText: rotulo, prefixText: 'R\$ ', border: const OutlineInputBorder()),
        keyboardType: const TextInputType.numberWithOptions(decimal: true),
        inputFormatters: [FilteringTextInputFormatter.allow(RegExp(r'[0-9.,]'))],
      );

  static String _formatarReais(double valor) {
    final partes = valor.toStringAsFixed(2).split('.');
    final inteiro = partes[0].replaceAllMapped(RegExp(r'\B(?=(\d{3})+(?!\d))'), (_) => '.');
    return 'R\$ $inteiro,${partes[1]}';
  }
}
