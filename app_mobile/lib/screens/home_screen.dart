import 'package:flutter/services.dart';
import 'package:material_ui/material_ui.dart';

import '../services/api_client.dart';
import '../services/armazenamento.dart';
import '../services/conta_offline.dart';
import '../services/lideranca.dart';
import '../services/sessao.dart';
import '../widgets/painel_lideranca.dart';

enum _Operacao { deposito, saque }

class HomeScreen extends StatefulWidget {
  const HomeScreen({
    super.key,
    required this.sessao,
    required this.api,
    required this.lideranca,
    required this.armazenamento,
  });

  final Sessao sessao;
  final ApiClient api;
  final Lideranca lideranca;
  final Armazenamento armazenamento;

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  late final ContaOffline _conta;
  String? _erroSaldo;

  _Operacao _operacao = _Operacao.deposito;
  final _valor = TextEditingController();
  final _destino = TextEditingController();
  final _valorTransferencia = TextEditingController();
  bool _enviando = false;

  int get _id => widget.sessao.contaId!;

  @override
  void initState() {
    super.initState();
    _conta = ContaOffline(contaId: _id, api: widget.api, armazenamento: widget.armazenamento);
    _atualizarSaldo();
  }

  @override
  void dispose() {
    _conta.dispose();
    super.dispose();
  }

  Future<void> _atualizarSaldo() async {
    try {
      await _conta.atualizar();
      if (mounted) setState(() => _erroSaldo = null);
    } on ApiException catch (e) {
      if (mounted) setState(() => _erroSaldo = e.mensagem);
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
    final deposito = _operacao == _Operacao.deposito;
    await _executar(() async {
      final aplicada = await _conta.registrar(deposito ? 'DEPOSITO' : 'SAQUE', valor);
      _valor.clear();
      final nome = deposito ? 'Depósito' : 'Saque';
      _avisar(aplicada ? '$nome realizado.' : '$nome guardado offline: será sincronizado quando a conexão voltar.');
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
      try {
        final resposta = await widget.api.post('/transferencias', {
          'idOrigem': _id,
          'idDestino': destino,
          'valor': valor,
          'operacaoId': novoOperacaoId(),
        });
        _destino.clear();
        _valorTransferencia.clear();
        _avisar(resposta['mensagem'] as String? ?? 'Transferência enviada.');
      } on ApiException catch (e) {
        // O backend só sincroniza depósito/saque; transferência offline não é aceita
        if (e.semConexao) throw ApiException('Transferência exige conexão com as agências. Tente de novo quando estiver online.');
        rethrow;
      }
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
    final largura = MediaQuery.sizeOf(context).width;
    return Scaffold(
      appBar: AppBar(
        title: Text('Conta $_id'),
        actions: [
          IconButton(tooltip: 'Atualizar saldo', onPressed: _atualizarSaldo, icon: const Icon(Icons.refresh)),
          IconButton(tooltip: 'Sair', onPressed: () => widget.sessao.sair(), icon: const Icon(Icons.logout)),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _atualizarSaldo,
        child: ListenableBuilder(
          listenable: _conta,
          builder: (context, _) => ListView(
            // Largura de celular mesmo em tela grande (web/desktop)
            padding: EdgeInsets.symmetric(horizontal: largura > 592 ? (largura - 560) / 2 : 16, vertical: 16),
            children: [
              if (!_conta.online) _faixaOffline(tema),
              PainelLideranca(lideranca: widget.lideranca),
              const SizedBox(height: 8),
              _cartaoSaldo(tema),
              if (_conta.temConflito) ...[const SizedBox(height: 8), _cartaoConflito(tema)],
              if (_conta.pendentes.isNotEmpty) ...[const SizedBox(height: 8), _cartaoPendentes(tema)],
              const SizedBox(height: 8),
              _cartaoDepositoSaque(),
              const SizedBox(height: 8),
              _cartaoTransferencia(tema),
            ],
          ),
        ),
      ),
    );
  }

  Widget _faixaOffline(ThemeData tema) {
    final lida = _conta.cache?.lidaEm;
    return Card(
      color: tema.colorScheme.tertiaryContainer,
      child: ListTile(
        leading: Icon(Icons.wifi_off, color: tema.colorScheme.onTertiaryContainer),
        title: Text('Sem conexão com as agências', style: TextStyle(color: tema.colorScheme.onTertiaryContainer)),
        subtitle: Text(
          lida == null
              ? 'Nenhum saldo guardado neste aparelho ainda.'
              : 'Mostrando o último saldo conhecido (${_hora(lida)}). Depósitos e saques ficam pendentes.',
          style: TextStyle(color: tema.colorScheme.onTertiaryContainer),
        ),
      ),
    );
  }

  Widget _cartaoSaldo(ThemeData tema) {
    final cache = _conta.cache;
    final provisorio = _conta.saldoProvisorio;
    final temPendente = _conta.pendentes.any((op) => !op.conflito);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(cache?.nomeAluno ?? 'Saldo', style: tema.textTheme.titleMedium),
            const SizedBox(height: 4),
            if (provisorio != null)
              Row(
                children: [
                  Text(_reais(provisorio), style: tema.textTheme.displaySmall),
                  if (temPendente) ...[
                    const SizedBox(width: 12),
                    Chip(
                      avatar: _conta.sincronizando
                          ? const SizedBox.square(dimension: 14, child: CircularProgressIndicator(strokeWidth: 2))
                          : const Icon(Icons.schedule, size: 16),
                      label: Text(_conta.sincronizando ? 'Sincronizando' : 'Provisório'),
                    ),
                  ],
                ],
              )
            else
              const LinearProgressIndicator(),
            if (temPendente && cache != null)
              Padding(
                padding: const EdgeInsets.only(top: 4),
                child: Text('Confirmado pela agência: ${_reais(cache.saldo)}', style: tema.textTheme.bodySmall),
              ),
            if (_erroSaldo != null)
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Text(_erroSaldo!, style: TextStyle(color: tema.colorScheme.error)),
              ),
          ],
        ),
      ),
    );
  }

  Widget _cartaoConflito(ThemeData tema) {
    final cores = tema.colorScheme;
    return Card(
      color: cores.errorContainer,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(children: [
              Icon(Icons.sync_problem, color: cores.onErrorContainer),
              const SizedBox(width: 8),
              Text('Conflito de sincronização', style: tema.textTheme.titleMedium?.copyWith(color: cores.onErrorContainer)),
            ]),
            const SizedBox(height: 8),
            Text(_conta.avisoConflito ?? '', style: TextStyle(color: cores.onErrorContainer)),
            if (_conta.cache != null)
              Text(
                'Saldo real agora: ${_reais(_conta.cache!.saldo)}',
                style: TextStyle(color: cores.onErrorContainer, fontWeight: FontWeight.w600),
              ),
            for (final op in _conta.pendentes.where((op) => op.conflito))
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Wrap(spacing: 8, crossAxisAlignment: WrapCrossAlignment.center, children: [
                  Text('${_nomeOperacao(op)} ${_reais(op.valor)}', style: TextStyle(color: cores.onErrorContainer)),
                  OutlinedButton(onPressed: () => _conta.descartar(op), child: const Text('Descartar')),
                  FilledButton(onPressed: () => _conta.reaplicar(op), child: const Text('Aplicar mesmo assim')),
                ]),
              ),
          ],
        ),
      ),
    );
  }

  Widget _cartaoPendentes(ThemeData tema) {
    final normais = _conta.pendentes.where((op) => !op.conflito).toList();
    if (normais.isEmpty) return const SizedBox.shrink();
    return Card(
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 8),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
              child: Text(
                _conta.temConflito ? 'Aguardando resolver o conflito' : 'Pendentes de sincronização',
                style: tema.textTheme.titleSmall,
              ),
            ),
            for (final op in normais)
              ListTile(
                dense: true,
                leading: const Icon(Icons.cloud_upload_outlined),
                title: Text('${_nomeOperacao(op)} de ${_reais(op.valor)}'),
                subtitle: Text('feito às ${_hora(op.criadaEm)}'),
                trailing: const Text('pendente'),
              ),
          ],
        ),
      ),
    );
  }

  Widget _cartaoDepositoSaque() => Card(
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
      );

  Widget _cartaoTransferencia(ThemeData tema) => Card(
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
      );

  Widget _campoValor(TextEditingController controle, String rotulo) => TextField(
        controller: controle,
        decoration: InputDecoration(labelText: rotulo, prefixText: 'R\$ ', border: const OutlineInputBorder()),
        keyboardType: const TextInputType.numberWithOptions(decimal: true),
        inputFormatters: [FilteringTextInputFormatter.allow(RegExp(r'[0-9.,]'))],
      );

  static String _nomeOperacao(OperacaoPendente op) => op.tipo == 'DEPOSITO' ? 'Depósito' : 'Saque';

  static String _hora(DateTime t) =>
      '${t.hour.toString().padLeft(2, '0')}:${t.minute.toString().padLeft(2, '0')}:${t.second.toString().padLeft(2, '0')}';

  static String _reais(double valor) {
    final partes = valor.toStringAsFixed(2).split('.');
    final inteiro = partes[0].replaceAllMapped(RegExp(r'\B(?=(\d{3})+(?!\d))'), (_) => '.');
    return 'R\$ $inteiro,${partes[1]}';
  }
}
