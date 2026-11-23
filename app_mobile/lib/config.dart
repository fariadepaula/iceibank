/// Espelha agencia/app/config.py: 3 agências em portas consecutivas.
const int portaBase = 4071; // 4000 + OFFSET pessoal (71)
const int numeroAgencias = 3;

/// No emulador Android, o "localhost" do computador é 10.0.2.2:
///   flutter run --dart-define=AGENCIA_HOST=10.0.2.2
const String hostAgencias = String.fromEnvironment('AGENCIA_HOST', defaultValue: 'localhost');

Uri urlAgencia(int id, String caminho) => Uri.parse('http://$hostAgencias:${portaBase + id}$caminho');

/// Frequência de consulta da liderança: rápido o bastante para o failover
/// aparecer em poucos segundos (o heartbeat do backend também roda a cada 3 s).
const Duration intervaloLideranca = Duration(seconds: 3);
