# Módulo Móvil Flutter: Frigate NVR & Control Operativo

Este módulo contiene la integración de la aplicación móvil en Flutter para:
1. **Monitorear en tiempo real las cámaras de Frigate NVR** (Cámara de Entrada, Cámara Interior y Cámara en vivo Zócalo CDMX / Demo).
2. **Registrar cambios de turno de guardias del SOC** directamente desde el dispositivo móvil.

---

## 1. Arquitectura de Conexión Flutter & Frigate NVR

Frigate expone múltiples protocolos para consumir video en clientes móviles:

| Protocolo | Puerto | Endpoint Frigate | Uso recomendado en Flutter |
| :--- | :--- | :--- | :--- |
| **HTTP MJPEG** | `8971` | `http://<IP_NVR>:8971/api/<cam_name>` | Streaming continuo ligero sin dependencias nativas C++ pesadas. |
| **HTTP Snapshot Polling** | `8971` | `http://<IP_NVR>:8971/api/<cam_name>/latest.jpg` | Refresco periódico (1 a 5 FPS) ultra compatible con cualquier versión de Flutter. |
| **RTSP go2rtc** | `8554` | `rtsp://<IP_NVR>:8554/<cam_name>` | Streaming nativo H.264 de ultrabaja latencia (mediante paquetes como `media_kit` o `flutter_vlc_player`). |
| **REST API** | `8971` | `http://<IP_NVR>:8971/api/cameras` | Listado de cámaras, FPS, estado de detección y eventos de seguridad. |

---

## 2. Direcciones IP para Pruebas

- **Desde Emulador Android:**
  - NVR Frigate: `http://10.0.2.2:8971` (RTSP: `rtsp://10.0.2.2:8554`)
  - App Backend Flask: `http://10.0.2.2:8000`
- **Desde Dispositivo Físico Android/iOS (Misma Wi-Fi):**
  - Conecta el celular a la misma red Wi-Fi de tu computadora.
  - Averigua la IP local de tu PC con `ipconfig` (ejemplo: `192.168.1.50`).
  - NVR Frigate: `http://192.168.1.50:8971` (RTSP: `rtsp://192.168.1.50:8554`)
  - App Backend Flask: `http://192.168.1.50:8000`

---

## 3. Configuración Requerida en Android (`AndroidManifest.xml`)

Para permitir que Flutter se conecte a direcciones HTTP y RTSP locales sin HTTPS:

Añade `android:usesCleartextTraffic="true"` en `android/app/src/main/AndroidManifest.xml`:

```xml
<application
    android:label="Identity Access SOC"
    android:name="${applicationName}"
    android:icon="@mipmap/ic_launcher"
    android:usesCleartextTraffic="true">
    ...
</application>
```

Y añade el permiso de Internet:
```xml
<uses-permission android:name="android.permission.INTERNET" />
```

---

## 4. Estructura del Código Dart

- **`lib/services/frigate_api_service.dart`**: Cliente HTTP para comunicarse con la API de Frigate y con la API de turnos del Lab.
- **`lib/widgets/camera_stream_card.dart`**: Widget reutilizable para mostrar cada cámara con badge en vivo, indicador de estado y refresco automático.
- **`lib/screens/frigate_monitor_screen.dart`**: Pantalla principal de monitoreo de cámaras.
- **`lib/screens/mobile_shift_screen.dart`**: Pantalla móvil para formalizar el relevo de guardia.
- **`lib/main.dart`**: Aplicación completa lista para ejecutar con `flutter run`.
