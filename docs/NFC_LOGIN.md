# Acceso con badge NFC

Módulo opcional que permite abrir sesión en el laboratorio acercando una tarjeta NFC al lector, sin escribir la contraseña.

> **Solo para demostración local.** El módulo guarda credenciales de las cuentas ficticias del laboratorio en el `.env` del host. No lo uses con tarjetas reales, personas reales ni en un entorno compartido.

## Cómo funciona

```
 Lector USB (ACR122U)            Host Windows                   App en Docker            Navegador
        │                            │                             │                        │
        │  lee UID                   │  POST /nfc/tap              │                        │
        │ ─────────────────────────► │ ───────────────────────────► │                        │
        │                            │                             │  comprueba lista blanca │
        │                            │                             │  guarda el toque       │
        │                            │                             │                        │
        │                            │                             │ ◄── POST /nfc/poll ────│
        │                            │                             │ ─────────────────────► │
        │                            │                             │  abre sesión con las  │
        │                            │                             │  credenciales guardadas│
```

1. `tools/nfc-bridge.ps1` corre en el host (donde está el lector USB) y lee el UID de la tarjeta con PC/SC.
2. Cuando detecta una tarjeta nueva envía el UID a `POST /nfc/tap` con el token del puente.
3. La app contrasta el UID con la lista blanca de la tabla `nfc_cards` y, si coincide, deja el toque pendiente en `nfc_taps`.
4. El navegador abierto en la pantalla de acceso consulta `POST /nfc/poll` cada 1,5 s; al recibir el toque, la app inicia sesión en Keycloak con las credenciales guardadas de ese usuario y la página se recarga ya autenticada.

Los toques pendientes se guardan en SQLite (no en memoria) porque la app corre con más de un worker de Gunicorn. Cada toque se consume una sola vez y caduca a los `NFC_TAP_TTL_SECONDS` segundos.

### Cerrar sesión y volver a entrar

Para que la tarjeta no reabra la sesión por su cuenta, el módulo aplica dos reglas:

- **Un toque nunca se guarda si ya hay sesión abierta.** Si pasas la tarjeta estando autenticado, el toque se consume y se descarta (queda anotado en la bitácora como `NFC_TAP_DESCARTADO`); no queda pendiente para más tarde.
- **Al cerrar sesión se descartan los toques pendientes.** Cuando pulsas "cerrar sesión", la app borra cualquier toque que quedara guardado, para que la pantalla de acceso no lo consuma al reiniciar el polling y te vuelva a entrar sin pasar la tarjeta.

Volver a entrar exige, por tanto, **pasar la tarjeta de nuevo** (retirarla del lector y acercarla otra vez). La única excepción es que el puente se reinicie con la tarjeta ya apoyada: en ese caso vuelve a leerla y envía el toque, que es justo lo que se espera.

## Requisitos

- Lector NFC USB (el módulo está probado con **ACS ACR122U**) y una tarjeta ISO14443-A.
- Windows en el host con PowerShell 5.1 o superior; la app puede seguir en Docker o en Linux.
- La app del laboratorio levantada (`docker compose up --build -d`) con `NFC_ENABLED=true`.
- Python 3.10 o posterior solo si se quiere usar el CLI de alta de tarjetas.

## Preparación

### 1. Habilitar el módulo en la app

En `.env`:

```dotenv
NFC_ENABLED=true
NFC_BRIDGE_TOKEN=cambia-este-token-por-uno-de-32-caracteres-o-mas
NFC_LOGIN_USERNAME=admin@example.test
NFC_LOGIN_PASSWORD=
NFC_TAP_TTL_SECONDS=15
```

`NFC_LOGIN_PASSWORD` puede quedar vacío: si el usuario indicado es una cuenta de demostración, la app reutiliza la variable `DEMO_PASSWORD_*` correspondiente (`DEMO_PASSWORD_ADMIN`, `DEMO_PASSWORD_IAM`, etc.). Para una cuenta que no sea de demostración define `NFC_PASSWORD_<USUARIO>` en mayúsculas, por ejemplo `NFC_PASSWORD_MI_USUARIO_EXAMPLE_TEST`.

Levanta de nuevo los servicios para que recojan la configuración:

```bash
docker compose up -d
```

El acceso por badge necesita que el cliente `identity-access-app` de Keycloak tenga habilitado el acceso directo (`directAccessGrantsEnabled`). El realm incluido ya lo trae. Si tu volumen de Keycloak se creó antes de ese cambio, el realm no se vuelve a importar: recrea el laboratorio con `docker compose down -v` y `docker compose up -d`.

### 2. Leer el UID de tu tarjeta

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\nfc-bridge.ps1 -PrintUid
```

Devuelve el ATR y el UID en los dos órdenes posibles:

```
  ATR       : 3B-8F-80-01-80-4F-0C-A0-00-00-03-06-03-00-01-00-00-00-00-6A
  UID (raw) : C928C70F
  UID (est.): 0FC728C9
```

La app acepta el UID en cualquiera de los dos órdenes, así que puedes registrar el que prefieras.

### 3. Registrar la tarjeta

Desde el contenedor de la app:

```bash
docker compose exec app python -m app.nfc_cli --uid 0FC728C9 --user admin@example.test --label "Tarjeta del administrador"
```

También puedes hacerlo desde la interfaz: entra como `admin@example.test` y usa la página **Badge NFC** del menú lateral.

### 4. Arrancar el puente

En una terminal aparte, en el host:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\nfc-bridge.ps1 -Token "el-mismo-token-del-puente"
```

Deja esa terminal abierta mientras uses el laboratorio. Con `-AppUrl` se apunta a otra URL y con `-IntervalSeconds` se ajusta la frecuencia de lectura.

### 5. Probar

1. Abre <http://localhost:8000> sin iniciar sesión.
2. Acércate la tarjeta al lector: la consola del puente muestra `Tarjeta detectada` y `[OK]`.
3. La pantalla muestra *Tarjeta aceptada* y se recarga ya dentro, con el rol del usuario asignado a la tarjeta.

## Comprobaciones y solución de problemas

| Síntoma | Causa habitual | Comprobación |
|---|---|---|
| El puente dice `tarjeta no registrada en la app` | La tarjeta no está en la lista blanca | `docker compose exec app python -m app.nfc_cli --uid <UID> --user admin@example.test` |
| El puente dice `token del puente incorrecto` | `NFC_BRIDGE_TOKEN` no coincide con el `-Token` del puente | Compara el `.env` con el argumento `-Token` |
| El puente dice `la app no responde` | La app no está levantada o el puerto no es `8000` | `docker compose ps` y `-AppUrl` |
| El puente no detecta ninguna tarjeta | Lector sin conexión, tarjeta mal apoyada o servicio de tarjetas parado | Revisa el cable USB y `Get-Service scardsvr` |
| La pantalla nunca abre sesión | El toque caducó antes de que el navegador lo consumiera | Sube `NFC_TAP_TTL_SECONDS` y no cierres la pestaña de acceso |
| La pantalla muestra `No hay credenciales guardadas para ...` | Falta la contraseña del usuario asignado | Define `NFC_PASSWORD_<USUARIO>` o `NFC_LOGIN_PASSWORD` |
| Keycloak responde `unauthorized_client` al toque | El realm se importó antes de habilitar el acceso directo | Recrea el volumen de Keycloak con `docker compose down -v` y vuelve a levantar |

En algunos equipos `SCardListReaders()` provoca el cierre del proceso de Windows, por eso el puente toma el nombre del lector del registro `Calais` en lugar de enumerarlo.

## Superficie de ataque y límites del módulo

- `POST /nfc/tap` exige el token del puente (`NFC_BRIDGE_TOKEN`, 32 caracteres o más) y solo acepta tarjetas de la lista blanca de usuarios activos.
- `POST /nfc/poll` exige el token CSRF de la sesión y consume el toque una sola vez.
- La lista blanca vive en la base local de la app, de modo que la app sigue siendo la autoridad: el puente solo propone un UID.
- Las credenciales se guardan en el `.env` del host, fuera de Git. Es una simplificación propia del laboratorio: en un entorno real conviene un secreto de Keycloak con *token exchange* en lugar de la contraseña del usuario.
- La comparación de UID no resiste clonación: una tarjeta clonada con el mismo UID obtiene el mismo acceso.
- El primer navegador que consulta consume el toque; el módulo está pensado para un único puesto de trabajo.
- La sesión que se abre es la de Keycloak: los roles, la vigencia y la revocación siguen mandando sobre lo que el badge permite.

## Archivos

- [`tools/nfc-bridge.ps1`](../tools/nfc-bridge.ps1): puente de Windows (PC/SC → HTTP).
- [`app/nfc_cli.py`](../app/nfc_cli.py): alta y baja de tarjetas desde la terminal.
- [`app/store.py`](../app/store.py): tablas `nfc_cards` y `nfc_taps`.
- [`app/wsgi.py`](../app/wsgi.py): rutas `/nfc/tap`, `/nfc/poll` y `/nfc`.
