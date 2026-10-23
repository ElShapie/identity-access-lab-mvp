class CameraInfo {
  final String id;
  final String name;
  final String location;
  final bool isOnline;
  final String streamUrl;
  final String snapshotUrl;
  final String rtspUrl;

  const CameraInfo({
    required this.id,
    required this.name,
    required this.location,
    required this.isOnline,
    required this.streamUrl,
    required this.snapshotUrl,
    required this.rtspUrl,
  });

  factory CameraInfo.fromConfig({
    required String id,
    required String serverBaseUrl,
    required String rtspBaseUrl,
    String? customName,
    String? location,
    bool isOnline = true,
  }) {
    return CameraInfo(
      id: id,
      name: customName ?? _formatCameraName(id),
      location: location ?? _formatCameraLocation(id),
      isOnline: isOnline,
      streamUrl: '$serverBaseUrl/api/$id',
      snapshotUrl: '$serverBaseUrl/api/$id/latest.jpg',
      rtspUrl: '$rtspBaseUrl/$id',
    );
  }

  static String _formatCameraName(String id) {
    switch (id) {
      case 'cam_entrada':
        return 'Cámara 1 (Entrada)';
      case 'cam_interior':
        return 'Cámara 2 (Interior)';
      case 'zocalo_cdmx':
        return 'Cámara Demo (Zócalo CDMX)';
      default:
        return id.replaceAll('_', ' ').toUpperCase();
    }
  }

  static String _formatCameraLocation(String id) {
    switch (id) {
      case 'cam_entrada':
        return 'Torniquete & Lector RFID';
      case 'cam_interior':
        return 'Pasillo Principal & Sala de Espera';
      case 'zocalo_cdmx':
        return 'Transmisión En Vivo (YouTube/HLS)';
      default:
        return 'Área General SOC';
    }
  }
}
