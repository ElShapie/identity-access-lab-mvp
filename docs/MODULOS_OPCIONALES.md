# Módulos opcionales

El Compose principal solo levanta Keycloak y la aplicación. Los siguientes módulos se conservan separados para que se puedan preparar después del recorrido de identidad digital.

## RFID

Archivos: [`modules/rfid/control_acceso.ino`](../modules/rfid/control_acceso.ino) y [`modules/rfid/registrar_tarjetas.py`](../modules/rfid/registrar_tarjetas.py).

### Requisitos

- Arduino Uno y lector MFRC522 compatibles con el ejemplo; confirmar el modelo real antes de cablear.
- Lector alimentado a 3.3 V y adaptación de niveles cuando corresponda.
- Arduino IDE, biblioteca MFRC522 y Python 3.10 o posterior.
- Puerto serie accesible; Python usa `pyserial`.
- Las tarjetas y sus UID deben ser de prueba, autorizados y guardados fuera de Git.

### Preparación

1. Revisa los comentarios del `.ino`, el cableado de fabricante y la guía de seguridad del lector. No conectes si el modelo no coincide.
2. Instala la biblioteca MFRC522 en Arduino IDE, carga el sketch y confirma primero que todas las lecturas se deniegan.
3. Sustituye los cuatro marcadores pendientes con UID ficticios o aprobados para la demostración; nunca publiques UID reales.
4. En una terminal Python crea un entorno virtual e instala la dependencia:

   ```bash
   python -m venv .venv
   # Windows PowerShell:
   .\.venv\Scripts\python.exe -m pip install "pyserial>=3.5,<4"
   # macOS/Linux:
   .venv/bin/python -m pip install "pyserial>=3.5,<4"
   ```

5. Cierra Arduino Serial Monitor y ejecuta el registrador desde `modules/rfid/`:

   ```bash
   python registrar_tarjetas.py --puerto COM3 --archivo eventos_rfid.csv
   ```

   En Linux el puerto suele ser `/dev/ttyACM0`. Escribe `E` para entrada o `S` para salida.

El CSV puede contener datos de acceso y UID; permanece local y no se añade al repositorio. El prototipo compara UID y no ofrece protección contra clonación. Una lectura permitida tampoco demuestra por sí sola que una persona cruzó una puerta.

## Video con Frigate

Archivos: [`modules/video/compose.yml`](../modules/video/compose.yml), [`config.example.yml`](../modules/video/config.example.yml) y [`.env.example`](../modules/video/.env.example).

### Requisitos

- Docker Engine + Compose, equipo con espacio suficiente y puertos locales disponibles.
- Cámaras IP o teléfonos que ofrezcan streams compatibles; usuario y contraseña propios.
- URL real del stream, red local autorizada y política de retención aprobada.
- La configuración de ejemplo necesita modificar IP, URL y ruta RTSP.

### Arranque independiente

1. Copia `modules/video/` a un equipo dedicado o entra en esa carpeta.
2. Crea `config/`, `media/` y `certs/`; copia `config.example.yml` a `config/config.yml` y `.env.example` a `.env`.
3. Cambia IPs y rutas por los valores reales. No uses el `.env.example` como credencial.
4. Revisa el destino del puerto publicado en `compose.yml`; conserva el enlace a una IP local concreta y no expongas Frigate a Internet.
5. Revisa el esquema con `docker compose config --quiet`, después ejecuta `docker compose pull` y `docker compose up -d`.
6. Cambia la contraseña inicial de Frigate, crea una cuenta de solo consulta para SOC y verifica reproducción antes de afirmar que la retención o grabación continua funciona.

El ejemplo contiene valores de red ficticios y una ruta RTSP de reemplazo. El stream MJPEG puede consumir más CPU al grabar. Calcula el espacio con una muestra de las cámaras reales. Las instrucciones de TLS/usuarios dependen de la dirección del NVR; para un uso compartido, configura HTTPS con certificados válidos.

## Microsoft 365 / Entra

No existe un contenedor local que replique las cuentas/licencias y políticas de Microsoft 365. Este módulo requiere un tenant de práctica autorizado, licencias apropiadas y un administrador que apruebe los ejercicios. OneLogin y Microsoft 365 son sistemas separados en este laboratorio; no se sincronizan automáticamente.

Antes del ejercicio, define las cuentas ficticias, MFA, roles y evidencia permitida. Nunca guardes secretos, capturas identificables, registros reales ni datos de personas en el repositorio. Si no hay tenant de prueba, se puede presentar el flujo como diseño y no como integración ejecutada.
