import 'package:flutter/material.dart';
import '../models/camera_info.dart';
import '../services/frigate_api_service.dart';
import '../widgets/camera_stream_card.dart';

class FrigateMonitorScreen extends StatefulWidget {
  final FrigateApiService apiService;

  const FrigateMonitorScreen({Key? key, required this.apiService}) : super(key: key);

  @override
  State<FrigateMonitorScreen> createState() => _FrigateMonitorScreenState();
}

class _FrigateMonitorScreenState extends State<FrigateMonitorScreen> {
  late Future<List<CameraInfo>> _camerasFuture;

  @override
  void initState() {
    super.initState();
    _refreshCameras();
  }

  void _refreshCameras() {
    setState(() {
      _camerasFuture = widget.apiService.fetchCameras();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Monitoreo NVR Frigate'),
        backgroundColor: const Color(0xFF1E293B),
        foregroundColor: Colors.white,
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _refreshCameras,
            tooltip: 'Actualizar cámaras',
          ),
        ],
      ),
      body: FutureBuilder<List<CameraInfo>>(
        future: _camerasFuture,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }

          final cameras = snapshot.data ?? [];

          return ListView(
            padding: const EdgeInsets.all(16),
            children: [
              // Banner de estado
              Container(
                margin: const EdgeInsets.only(bottom: 16),
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.blue[50],
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: Colors.blue[200]!),
                ),
                child: Row(
                  children: [
                    Icon(Icons.info_outline, color: Colors.blue[800], size: 20),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        'Conectado a Frigate en ${widget.apiService.frigateBaseUrl}. Visualizando stream en vivo y cámaras preparadas.',
                        style: TextStyle(color: Colors.blue[900], fontSize: 12),
                      ),
                    ),
                  ],
                ),
              ),

              // Lista de cámaras
              ...cameras.map((camera) => CameraStreamCard(camera: camera)).toList(),
            ],
          );
        },
      ),
    );
  }
}
