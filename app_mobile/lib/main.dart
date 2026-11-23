import 'package:material_ui/material_ui.dart';

import 'screens/home_screen.dart';
import 'screens/login_screen.dart';
import 'services/api_client.dart';
import 'services/lideranca.dart';
import 'services/sessao.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final sessao = Sessao();
  await sessao.carregar();
  runApp(IceibankApp(sessao: sessao, api: ApiClient(sessao), lideranca: Lideranca()..iniciar()));
}

class IceibankApp extends StatelessWidget {
  const IceibankApp({super.key, required this.sessao, required this.api, required this.lideranca});

  final Sessao sessao;
  final ApiClient api;
  final Lideranca lideranca;

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
            ? HomeScreen(sessao: sessao, api: api, lideranca: lideranca)
            : LoginScreen(sessao: sessao, api: api, lideranca: lideranca),
      ),
    );
  }
}
