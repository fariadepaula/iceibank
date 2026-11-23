import 'package:material_ui/material_ui.dart';

import 'screens/home_screen.dart';
import 'screens/login_screen.dart';
import 'services/api_client.dart';
import 'services/armazenamento.dart';
import 'services/lideranca.dart';
import 'services/sessao.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final sessao = Sessao();
  await sessao.carregar();
  final armazenamento = Armazenamento();
  await armazenamento.abrir();
  runApp(IceibankApp(
    sessao: sessao,
    api: ApiClient(sessao),
    lideranca: Lideranca()..iniciar(),
    armazenamento: armazenamento,
  ));
}

class IceibankApp extends StatelessWidget {
  const IceibankApp({super.key, required this.sessao, required this.api, required this.lideranca, required this.armazenamento});

  final Sessao sessao;
  final ApiClient api;
  final Lideranca lideranca;
  final Armazenamento armazenamento;

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'ICEIBank',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(colorSchemeSeed: const Color(0xFF1B5E9A), useMaterial3: true),
      darkTheme: ThemeData(colorSchemeSeed: const Color(0xFF1B5E9A), brightness: Brightness.dark, useMaterial3: true),
      home: ListenableBuilder(
        listenable: sessao,
        builder: (context, _) => sessao.autenticada
            ? HomeScreen(
                key: ValueKey(sessao.contaId),
                sessao: sessao,
                api: api,
                lideranca: lideranca,
                armazenamento: armazenamento,
              )
            : LoginScreen(sessao: sessao, api: api, lideranca: lideranca),
      ),
    );
  }
}
