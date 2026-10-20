# Identity Access Lab MVP

Laboratorio autocontenido para aprender el flujo de identidad digital: inicio de sesión OIDC, permisos por rol, altas y bajas por SCIM y registro de auditoría. El modo incluido usa Keycloak local en Docker para que el ejercicio pueda levantarse sin un tenant externo.

> **Solo para demostración local.** Compose publica los servicios en `127.0.0.1`. No expongas estos contenedores a Internet ni uses nombres, credenciales, tarjetas o datos reales. La configuración de desarrollo no es un despliegue de producción.

## Inicio rápido

Requisitos: Docker Desktop o Docker Engine con el complemento `docker compose`, 4 GB de RAM disponibles y puertos locales `8000` y `8081` libres.

1. Copia `.env.example` como `.env`.
2. Ejecuta `docker compose up --build -d`.
3. Espera a que Keycloak y la aplicación estén saludables:

   ```bash
   docker compose ps
   ```

4. Abre <http://localhost:8000> y pulsa **Iniciar sesión**.
5. Usa `ingeniero@example.test` y la contraseña de demostración indicada en `.env.example`.

El inicio de Keycloak puede tardar un minuto la primera vez. La guía completa, incluyendo comprobaciones y solución de problemas, está en [`docs/GUIA_INSTALACION.md`](docs/GUIA_INSTALACION.md).

## Recorrido del MVP

1. Inicia sesión como ingeniero y prueba consulta y mantenimiento.
2. Intenta administrar; la app debe devolver `403`.
3. Inicia sesión como auditor y consulta los eventos; mantenimiento debe quedar denegado.
4. Envía una actualización SCIM para desactivar al ingeniero; la sesión abierta debe perder acceso a las acciones protegidas.
5. Reactiva la cuenta para continuar probando.

Los comandos reproducibles están en la guía de instalación. El rol y el estado que autorizan acciones viven en la base local de la aplicación; SCIM es la vía documentada para sincronizar esos cambios.

## Componentes

- **Keycloak 26.7.3:** proveedor OIDC local; importa un realm de demostración al iniciar por primera vez.
- **Flask + Gunicorn:** login OIDC, permisos por rol, CSRF, sesión y subconjunto SCIM 2.0.
- **SQLite:** persistencia local de usuarios y últimos 500 eventos.
- **Docker Compose:** red interna, volúmenes persistentes, healthchecks y puertos ligados a localhost.
- **Módulos opcionales:** ejemplos de RFID y Frigate conservados fuera del arranque predeterminado; ejercicios de Microsoft 365 requieren un tenant autorizado.

La app ofrece una matriz pequeña: `admin`, `mantenimiento`, `auditor`, `consulta` y `sin_acceso`. Consulta el detalle en [`docs/ARQUITECTURA.md`](docs/ARQUITECTURA.md).

Para las extensiones consulta [`docs/MODULOS_OPCIONALES.md`](docs/MODULOS_OPCIONALES.md). No son necesarias para iniciar el MVP.

## Comandos útiles

```bash
docker compose logs -f app keycloak
docker compose restart app
docker compose down
```

`docker compose down` conserva datos. Para borrar el laboratorio y su base de datos local de Keycloak, usa `docker compose down -v`; esta acción elimina los datos guardados.

## Integración con OneLogin

El código usa descubrimiento OIDC configurable. La guía [`docs/ONelogin.md`](docs/ONelogin.md) describe cómo cambiar del proveedor local a un tenant autorizado, habilitar HTTPS y mapear la cuenta local. SCIM implementa únicamente las operaciones documentadas en el perfil de este MVP; no debe declararse compatibilidad SCIM completa.

## Validación

Las pruebas locales se ejecutan con `python -m unittest discover -s tests -v`. Para comprobar contenedores y realm, sigue la guía de instalación. Las pruebas automatizadas no sustituyen una validación con un tenant, equipo o proveedor real.

## Licencia

MIT; ver [`LICENSE`](LICENSE).

