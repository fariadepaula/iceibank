import 'package:material_ui/material_ui.dart';

import '../services/lideranca.dart';

class PainelLideranca extends StatelessWidget {
  const PainelLideranca({super.key, required this.lideranca});

  final Lideranca lideranca;

  @override
  Widget build(BuildContext context) {
    final cores = Theme.of(context).colorScheme;
    return ListenableBuilder(
      listenable: lideranca,
      builder: (context, _) {
        final (icone, cor, titulo) = switch (lideranca) {
          Lideranca(semResposta: true) => (Icons.cloud_off, cores.error, 'Nenhuma agência respondeu'),
          Lideranca(atualizadoEm: null) => (Icons.hourglass_empty, cores.outline, 'Consultando agências...'),
          Lideranca(lider: null) => (Icons.how_to_vote, cores.tertiary, 'Eleição em andamento'),
          Lideranca(:final lider) => (Icons.workspace_premium, cores.primary, 'Líder atual: Agência $lider'),
        };
        final hora = lideranca.atualizadoEm;
        final detalhe = [
          if (lideranca.agenciaConsultada != null && !lideranca.semResposta)
            'segundo a Agência ${lideranca.agenciaConsultada}',
          if (hora != null) 'às ${_hora(hora)}',
        ].join(' ');
        final historico = lideranca.historico;
        return Card(
          clipBehavior: Clip.antiAlias,
          child: Column(
            children: [
              ListTile(
                leading: Icon(icone, color: cor, size: 32),
                title: Text(titulo, style: const TextStyle(fontWeight: FontWeight.w600)),
                subtitle: Text(detalhe.isEmpty ? 'Atualiza sozinho a cada 3 s' : detalhe),
              ),
              if (historico.length > 1)
                ExpansionTile(
                  dense: true,
                  leading: const Icon(Icons.history),
                  title: Text('Histórico de líderes (${historico.length - 1} '
                      '${historico.length == 2 ? 'troca' : 'trocas'})'),
                  children: [
                    for (final (i, item) in historico.indexed)
                      ListTile(
                        dense: true,
                        leading: Icon(i == 0 ? Icons.workspace_premium : Icons.subdirectory_arrow_right, size: 18),
                        title: Text('Agência ${item.lider}${i == 0 ? ' (atual)' : ''}'),
                        trailing: Text('desde ${_hora(item.desde)}'),
                      ),
                  ],
                ),
            ],
          ),
        );
      },
    );
  }

  static String _hora(DateTime t) => '${_doisDigitos(t.hour)}:${_doisDigitos(t.minute)}:${_doisDigitos(t.second)}';

  static String _doisDigitos(int n) => n.toString().padLeft(2, '0');
}
