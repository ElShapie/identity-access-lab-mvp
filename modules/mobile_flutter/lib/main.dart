import 'package:flutter/material.dart';
import 'screens/frigate_monitor_screen.dart';
import 'screens/mobile_shift_screen.dart';
import 'services/frigate_api_service.dart';

void main() {
  runApp(const IdentityAccessApp());
}

class IdentityAccessApp extends StatelessWidget {
  const IdentityAccessApp({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Identity Access Mobile SOC',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF146EF5),
          primary: const Color(0xFF146EF5),
        ),
        useMaterial3: true,
      ),
      home: const MainNavigationScreen(),
    );
  }
}

class MainNavigationScreen extends StatefulWidget {
  const MainNavigationScreen({Key? key}) : super(key: key);

  @override
  State<MainNavigationScreen> createState() => _MainNavigationScreenState();
}

class _MainNavigationScreenState extends State<MainNavigationScreen> {
  int _currentIndex = 0;

  // Servicio configurado para el entorno de laboratorio
  // En emulador: '10.0.2.2'. En dispositivo real en Wi-Fi: IP de tu PC ej. '192.168.1.100'
  final _apiService = FrigateApiService(
    frigateHost: '10.0.2.2',
    frigatePort: 8971,
    rtspPort: 8554,
    backendHost: '10.0.2.2',
    backendPort: 8000,
  );

  @override
  Widget build(BuildContext context) {
    final screens = [
      FrigateMonitorScreen(apiService: _apiService),
      MobileShiftScreen(apiService: _apiService),
    ];

    return Scaffold(
      body: screens[_currentIndex],
      bottomNavigationBar: NavigationBar(
        selectedIndex: _currentIndex,
        onDestinationSelected: (idx) => setState(() => _currentIndex = idx),
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.videocam_outlined),
            selectedIcon: Icon(Icons.videocam),
            label: 'Cámaras NVR',
          ),
          NavigationDestination(
            icon: Icon(Icons.swap_horiz_outlined),
            selectedIcon: Icon(Icons.swap_horiz),
            label: 'Cambio de Turno',
          ),
        ],
      ),
    );
  }
}
