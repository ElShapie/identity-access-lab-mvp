import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/camera_info.dart';

class FrigateApiService {
  // Configuración de red para el entorno de laboratorio
  // En emulador Android usar 10.0.2.2; en dispositivo físico usar la IP LAN de la PC
  final String frigateHost;
  final int frigatePort;
  final int rtspPort;
  final String backendHost;
  final int backendPort;

  FrigateApiService({
    this.frigateHost = '10.0.2.2',
    // Frigate publica la API HTTP/WebRTC plana en :5000 (la :8971 es HTTPS con auth).
    // Para la app móvil se usa el puerto plano; ver docs/GUIA_NVR_FRIGATE.md.
    this.frigatePort = 5000,
    this.rtspPort = 8554,
    this.backendHost = '10.0.2.2',
    this.backendPort = 8000,
  });

  String get frigateBaseUrl => 'http://$frigateHost:$frigatePort';
  String get rtspBaseUrl => 'rtsp://$frigateHost:$rtspPort';
  String get backendBaseUrl => 'http://$backendHost:$backendPort';

  /// Obtiene la lista de cámaras configuradas y su estado
  Future<List<CameraInfo>> fetchCameras() async {
    try {
      final response = await http.get(
        Uri.parse('$frigateBaseUrl/api/config'),
      ).timeout(const Duration(seconds: 4));

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        // Frigate expone las cámaras en /api/config -> cameras
        final cameras = (data is Map<String, dynamic> && data['cameras'] is Map<String, dynamic>)
            ? data['cameras'] as Map<String, dynamic>
            : (data is Map<String, dynamic> ? data : <String, dynamic>{});
        if (cameras.isNotEmpty) {
          return cameras.keys.map((camId) {
            return CameraInfo.fromConfig(
              id: camId,
              serverBaseUrl: frigateBaseUrl,
              rtspBaseUrl: rtspBaseUrl,
              isOnline: true,
            );
          }).toList();
        }
      }
    } catch (_) {
      // Fallback a las cámaras predefinidas del laboratorio si Frigate aún está iniciando
    }

    // Cámaras estándar del Identity Access Lab
    return [
      CameraInfo.fromConfig(
        id: 'zocalo_cdmx',
        serverBaseUrl: frigateBaseUrl,
        rtspBaseUrl: rtspBaseUrl,
        customName: 'Cámara Demo (Zócalo CDMX)',
        location: 'Transmisión En Vivo (YouTube/HLS)',
        isOnline: true,
      ),
      CameraInfo.fromConfig(
        id: 'cam_entrada',
        serverBaseUrl: frigateBaseUrl,
        rtspBaseUrl: rtspBaseUrl,
        customName: 'Cámara 1 (Entrada)',
        location: 'Torniquete & Lector RFID',
        isOnline: false, // Inactiva hasta conectar el teléfono Android 1
      ),
      CameraInfo.fromConfig(
        id: 'cam_interior',
        serverBaseUrl: frigateBaseUrl,
        rtspBaseUrl: rtspBaseUrl,
        customName: 'Cámara 2 (Interior)',
        location: 'Pasillo Principal & Sala de Espera',
        isOnline: false, // Inactiva hasta conectar el teléfono Android 2
      ),
    ];
  }

  /// Registra el cambio de turno enviándolo al backend Flask del laboratorio
  Future<bool> submitShiftHandover({
    required String operatorName,
    required String shift,
    required String status,
    required String notes,
    required List<String> verifiedCameras,
  }) async {
    try {
      final response = await http.post(
        Uri.parse('$backendBaseUrl/api/turno'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          'operator': operatorName,
          'shift': shift,
          'status': status,
          'description': notes,
          'cams': verifiedCameras,
          'source': 'mobile_flutter_app',
        }),
      ).timeout(const Duration(seconds: 5));

      return response.statusCode == 200;
    } catch (_) {
      return false;
    }
  }
}
