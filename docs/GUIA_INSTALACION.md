# Guía de instalación y recorrido de prueba

Esta guía levanta la demostración local completa con Docker Compose. Sigue los pasos en orden; los valores de `.env.example` son ficticios y solo deben usarse en `localhost`.

## 1. Requisitos

- Windows 10/11 con Docker Desktop y backend WSL 2, macOS con Docker Desktop o Linux con Docker Engine.
- Docker Compose v2 (comando `docker compose`, con espacio).
- 4 GB de RAM libres para Keycloak y la app. Cierra máquinas virtuales pesadas si Keycloak reinicia por falta de memoria.
- Puertos TCP locales `8000` y `8081` disponibles.
- Conexión a Internet la primera vez para descargar imágenes y paquetes de Python.
- Navegador moderno.

En Windows/macOS se recomienda Docker Desktop, que incluye Engine, CLI y Compose; en Linux se puede usar Docker Engine con el plugin Compose. Sigue la [guía oficial de Docker Desktop](https://docs.docker.com/desktop/) o el [resumen oficial de instalación de Compose](https://docs.docker.com/compose/install/). Después de instalar, abre Docker Desktop o inicia el servicio Docker antes de seguir.

No hace falta instalar Python, Java, Keycloak, Flask ni una base de datos en el equipo anfitrión: se ejecutan en contenedores.

## 2. Descargar y preparar

En una terminal, clona el repositorio y entra en la carpeta:

```bash
git clone https://github.com/ElShapie/identity-access-lab-mvp.git
cd identity-access-lab-mvp
```

En Windows también puedes abrir PowerShell en esa carpeta; los siguientes comandos de Compose son iguales.

Copia el archivo de entorno:

```powershell
Copy-Item .env.example .env
```

En macOS/Linux:

```bash
cp .env.example .env
chmod 600 .env
```

El archivo ya contiene contraseñas ficticias para el laboratorio local, no credenciales productivas. Para una práctica compartida, reemplaza las contraseñas antes del primer arranque. No subas `.env` a GitHub. La plantilla se ignora mediante `.gitignore`.

## 3. Validar el Compose antes de iniciar

```bash
docker compose config --quiet
```

Si aparece que falta una variable, confirma que `.env` está junto a `compose.yaml` y que conserva los nombres de `.env.example`.

## 4. Levantar la aplicación

```bash
docker compose up --build -d
docker compose ps
```

La primera compilación descarga la imagen de Python y puede tardar. Keycloak importa el realm y las tres cuentas demo cuando crea por primera vez su volumen.

Espera a ver `healthy` en Keycloak y la app. Comprueba los logs si aún dice `starting`:

```bash
docker compose logs --tail=100 keycloak app
```

Comprueba salud de la aplicación:

```text
http://localhost:8000/health
```

Resultado esperado: `{"status":"ok"}`. Abre después <http://localhost:8000>.

## 5. Probar inicio de sesión y roles

En el inicio de la app, pulsa **Iniciar sesión**. Keycloak muestra la pantalla local del realm. Usa una de estas cuentas, cuya contraseña está en `.env`:

| Correo | Área | Rol | Pruebas esperadas |
|---|---|---|---|
| `ingeniero@example.test` | Laboratorio | `mantenimiento` | Consulta y mantenimiento permitidos; administración denegada |
| `auditor@example.test` | Laboratorio | `auditor` | Consulta y registros permitidos; mantenimiento denegado |
| `admin@example.test` | Laboratorio | `admin` | Consulta, mantenimiento, administración y registros permitidos |
| `rrhh@example.test` | RRHH | `consulta` | Solo consulta |
| `ti@example.test` | TI | `mantenimiento` | Consulta y mantenimiento |
| `iam@example.test` | IAM | `admin` | Administración y registros |
| `soc-auditoria@example.test` | SOC / Auditoría | `auditor` | Consulta y registros |
| `seguridad-fisica@example.test` | Seguridad Física | `consulta` | Solo consulta |

Las contraseñas iniciales están en `.env.example`. Cámbialas antes de una demostración compartida. Las cuentas son ficticias. Los roles de este MVP son globales; no limitan permisos por área. Keycloak solo importa las cuentas la primera vez que se crea su volumen.

### Configurar TOTP en el primer acceso

Después de ingresar la contraseña de cualquier cuenta local, Keycloak obliga a configurar un autenticador TOTP. Escanea el QR con una app compatible y escribe el código de seis dígitos para confirmar. En los siguientes inicios se solicitará un nuevo código de la app. Mantén sincronizados el reloj del servidor y del teléfono.

Esta política se aplica a Keycloak local; la conexión opcional con OneLogin necesita MFA configurado por separado en ese proveedor. Si se pierde el autenticador, un administrador debe restablecer el OTP de la cuenta en Keycloak. El realm actualizado se importa solo al crear el volumen: reiniciar el laboratorio con `docker compose down -v` elimina las cuentas y eventos locales.

La página de usuarios (`/admin/usuarios`) sirve para que un administrador confirme los roles locales. No permite modificar usuarios directamente; las modificaciones del ejercicio pasan por SCIM.

## 6. Probar SCIM y una baja durante una sesión abierta

El contenedor incluye un cliente de demostración que toma el token desde su entorno. No es necesario copiar el token a la línea de comandos ni a una captura.

1. Inicia sesión como ingeniero en el navegador y conserva esa pestaña abierta.
2. En otra terminal ejecuta:

   ```bash
   docker compose exec app python -m app.scim_cli ingeniero@example.test --active false
   ```

3. Vuelve a la pestaña anterior. Intenta consulta o mantenimiento. La app debe responder `403`, porque vuelve a consultar el estado local en cada acción protegida.
4. Reactiva la cuenta:

   ```bash
   docker compose exec app python -m app.scim_cli ingeniero@example.test --active true
   ```

5. Comprueba cambio de rol a auditor y vuelta a mantenimiento:

   ```bash
   docker compose exec app python -m app.scim_cli ingeniero@example.test --role auditor
   docker compose exec app python -m app.scim_cli ingeniero@example.test --role mantenimiento
   ```

El script utiliza PATCH sobre `/scim/v2/Users`. También se puede consultar la API con curl:

```bash
curl -i http://localhost:8000/scim/v2/Users
```

Sin `Authorization: Bearer ...` la respuesta debe ser `401`. No pegues el token en historial de terminal, Issues, capturas o conversaciones.

## 7. Verificar eventos

Inicia sesión como auditor o administrador y abre <http://localhost:8000/registros>. Verás los últimos 100 eventos. La base conserva como máximo los 500 más recientes para que la demo no crezca sin límite.

## 8. Apagar y reiniciar

```bash
docker compose down
```

Esto detiene contenedores y conserva las cuentas y eventos en volúmenes locales. Para volver a iniciar:

```bash
docker compose up -d
```

Para borrar por completo los datos de práctica y volver al estado inicial:

```bash
docker compose down -v
```

Este último comando elimina las bases de datos y las cuentas de Keycloak y de la aplicación. No lo ejecutes si necesitas conservar evidencias o resultados.

## 9. Problemas frecuentes

### `port is already allocated` o la página no abre

Otro proceso usa `8000` o `8081`. Detén ese proceso o cambia el puerto del lado izquierdo en `ports` de `compose.yaml`. Si cambias Keycloak de `8081`, actualiza `KC_HOSTNAME`, `redirectUris` en el realm, `APP_BASE_URL` y las URLs de la guía.

### Keycloak queda `starting` o se reinicia

Revisa `docker compose logs --tail=150 keycloak`. La primera importación puede tardar; comprueba que Docker tenga RAM suficiente. Valida que `.env` tenga todas las variables requeridas y reinicia con `docker compose up -d`.

### Login vuelve a la app con `403`

Confirma que el usuario de Keycloak usa exactamente el correo `@example.test`, que existe en la tabla local y está activo. Comprueba que el callback es `http://localhost:8000/auth/callback` y que el cliente tiene el mismo `OIDC_CLIENT_SECRET` que `.env`. Si el realm ya fue importado, los cambios en el JSON no reimportan el realm existente; para reiniciar la demo desde cero usa `docker compose down -v`.

### Cambié `.env` pero Keycloak conserva la contraseña anterior

Keycloak importa configuración solamente cuando crea el realm por primera vez. La contraseña guardada en el volumen no se reemplaza al reiniciar. Cambia la contraseña desde la consola de Keycloak o elimina los volúmenes de demo para empezar desde cero.

### App muestra `Proveedor OIDC local no disponible`

Comprueba `docker compose ps` y `docker compose logs keycloak`. El app espera a que Keycloak esté saludable, pero puede tardar algo más en la primera ejecución. Reinicia la app cuando Keycloak indique `healthy`.

### La consola de Keycloak

Está en <http://localhost:8081>. Las credenciales administrativas son `KEYCLOAK_ADMIN` y `KEYCLOAK_ADMIN_PASSWORD` en `.env`. Es una consola local de laboratorio; no la expongas a otras redes.

## 10. Qué demuestra y qué no

Demuestra login OIDC local, permisos en servidor, CSRF en formularios, actualización/baja SCIM y auditoría local. No demuestra MFA, integración real con OneLogin, alta automática desde un directorio externo, seguridad RFID, cámaras ni una operación de producción. Para OneLogin, usa la guía separada y un entorno autorizado con HTTPS.

