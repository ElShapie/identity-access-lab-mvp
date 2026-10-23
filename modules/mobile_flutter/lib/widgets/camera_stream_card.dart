import 'dart:async';
import 'package:flutter/material.dart';
import '../models/camera_info.dart';

class CameraStreamCard extends StatefulWidget {
  final CameraInfo camera;
  final VoidCallback? onTap;

  const CameraStreamCard({
    Key? key,
    required this.camera,
    this.onTap,
  }) : super(key: key);

  @override
  State<CameraStreamCard> createState() => _CameraStreamCardState();
}

class _CameraStreamCardState extends State<CameraStreamCard> {
  Timer? _refreshTimer;
  int _cacheBuster = DateTime.now().millisecondsSinceEpoch;
  bool _hasError = false;

  @override
  void initState() {
    super.initState();
    // Actualiza la captura cada 1.5 segundos simulando stream continuo ligero
    if (widget.camera.isOnline) {
      _refreshTimer = Timer.periodic(const Duration(milliseconds: 1500), (timer) {
        if (mounted) {
          setState(() {
            _cacheBuster = DateTime.now().millisecondsSinceEpoch;
            _hasError = false;
          });
        }
      });
    }
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final camera = widget.camera;

    return Card(
      elevation: 2,
      margin: const EdgeInsets.only(bottom: 16),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      clipBehavior: Clip.antiAlias,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Visor de video / snapshot
          AspectRatio(
            aspectRatio: 16 / 9,
            child: Stack(
              children: [
                Positioned.fill(
                  child: Container(
                    color: Colors.black,
                    child: camera.isOnline && !_hasError
                        ? Image.network(
                            '${camera.snapshotUrl}?t=$_cacheBuster',
                            fit: BoxFit.cover,
                            errorBuilder: (context, error, stackTrace) {
                              return _buildFallbackView(camera);
                            },
                            loadingBuilder: (context, child, loadingProgress) {
                              if (loadingProgress == null) return child;
                              return const Center(
                                child: CircularProgressIndicator(
                                  strokeWidth: 2,
                                  color: Colors.blueAccent,
                                ),
                              );
                            },
                          )
                        : _buildFallbackView(camera),
                  ),
                ),
                // Badge EN VIVO / DESCONECTADA
                Positioned(
                  top: 10,
                  left: 10,
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      color: camera.isOnline
                          ? Colors.redAccent.withOpacity(0.9)
                          : Colors.black54,
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        if (camera.isOnline) ...[
                          const Icon(Icons.circle, size: 8, color: Colors.white),
                          const SizedBox(width: 4),
                          const Text(
                            'EN VIVO',
                            style: TextStyle(
                              color: Colors.white,
                              fontSize: 10,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ] else ...[
                          const Text(
                            'EN ESPERA (ANDROID)',
                            style: TextStyle(
                              color: Colors.white70,
                              fontSize: 10,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ],
                      ],
                    ),
                  ),
                ),
                // Botón expandir pantalla completa
                Positioned(
                  bottom: 8,
                  right: 8,
                  child: IconButton(
                    icon: const Icon(Icons.fullscreen, color: Colors.white),
                    onPressed: () => _showFullscreenDialog(context),
                  ),
                ),
              ],
            ),
          ),
          // Metadatos y detalles de cámara
          Padding(
            padding: const EdgeInsets.all(12),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      camera.name,
                      style: const TextStyle(
                        fontWeight: FontWeight.bold,
                        fontSize: 14,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      camera.location,
                      style: TextStyle(
                        color: Colors.grey[600],
                        fontSize: 12,
                      ),
                    ),
                  ],
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: camera.isOnline
                        ? Colors.green.withOpacity(0.12)
                        : Colors.orange.withOpacity(0.12),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Text(
                    camera.isOnline ? 'RTSP ACTIVO' : 'NO DETECTADA',
                    style: TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.bold,
                      color: camera.isOnline ? Colors.green[800] : Colors.orange[800],
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildFallbackView(CameraInfo camera) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              camera.isOnline ? Icons.videocam_off : Icons.phone_android,
              color: Colors.white38,
              size: 40,
            ),
            const SizedBox(height: 8),
            Text(
              camera.isOnline
                  ? 'Reconectando con NVR Frigate...'
                  : 'Cámara móvil Android pendiente de conexión Wi-Fi',
              textAlign: TextAlign.center,
              style: const TextStyle(color: Colors.white70, fontSize: 11),
            ),
          ],
        ),
      ),
    );
  }

  void _showFullscreenDialog(BuildContext context) {
    showDialog(
      context: context,
      builder: (ctx) {
        return Dialog(
          backgroundColor: Colors.black,
          insetPadding: EdgeInsets.zero,
          child: Stack(
            children: [
              Center(
                child: Image.network(
                  '${widget.camera.snapshotUrl}?t=$_cacheBuster',
                  fit: BoxFit.contain,
                  errorBuilder: (_, __, ___) => _buildFallbackView(widget.camera),
                ),
              ),
              Positioned(
                top: 20,
                right: 20,
                child: IconButton(
                  icon: const Icon(Icons.close, color: Colors.white, size: 28),
                  onPressed: () => Navigator.of(ctx).pop(),
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}
