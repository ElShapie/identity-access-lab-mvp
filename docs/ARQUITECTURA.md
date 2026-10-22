# Arquitectura y límites

## Componentes

```text
Navegador ── OIDC ──> Keycloak (contenedor local, puerto 8081)
    │                         │
    │                         ▲
    └──── HTTP ──> Flask/Gunicorn (puerto 8000) ──> SQLite (volumen app_data)
                      ▲        │
        SCIM 2.0 ─────┘        ▲
                              │
Lector USB ──> puente NFC del host ──> POST /nfc/tap
```

Los dos puertos del host se enlazan a `127.0.0.1`. El contenedor de la app usa una URL de descubrimiento OIDC local que lee metadata de Keycloak por la red privada de Compose y reescribe token, userinfo y JWKS a direcciones internas. El `issuer` y la URL de autorización permanecen en `http://localhost:8081`, que es lo que usa el navegador. Esto evita pedir al usuario que añada nombres al archivo `hosts`.

El puente NFC es un componente opcional del host, no del contenedor: el lector USB no puede abrirse desde la red de Compose. El puente solo propone un UID; la app sigue siendo la autoridad que decide si esa tarjeta está habilitada. Detalle en [`NFC_LOGIN.md`](NFC_LOGIN.md).

## Flujo OIDC

1. `/login` inicia Authorization Code en Keycloak.
2. Keycloak autentica una cuenta del realm `identity-access` y vuelve a `/auth/callback`.
3. La app valida el intercambio OIDC mediante Authlib, toma `sub` y correo y busca el usuario local aprovisionado.
4. El `sub` queda vinculado una sola vez al usuario local. Un segundo `sub` no puede reclamar esa cuenta vinculada.
5. Cada acción protegida vuelve a consultar el usuario y el rol en SQLite. Cambios o bajas SCIM se aplican también a una sesión abierta.

La búsqueda inicial usa el correo. Para uso externo real hay que definir el proceso de alta y cambio de correo en el directorio, y confirmar que los usuarios locales se aprovisionan con la identidad correcta.

## Roles

| Rol | Consulta | Mantenimiento | Admin | Registros |
|---|---:|---:|---:|---:|
| `admin` | Sí | Sí | Sí | Sí |
| `mantenimiento` | Sí | Sí | No | No |
| `auditor` | Sí | No | No | Sí |
| `consulta` | Sí | No | No | No |
| `sin_acceso` | No | No | No | No |

La app es la autoridad para las acciones locales. El claim `lab_role` del token local sirve como dato demostrativo; los permisos se basan en el rol aprovisionado en la base local.

## Perfil SCIM implementado

El laboratorio implementa una parte pequeña de SCIM 2.0 para `Users`: listar y filtrar por `userName eq "correo"`, crear, leer, PATCH de `userName`, `title` y `active`, y desactivar mediante DELETE. `Groups` responde una lista vacía. La operación DELETE conserva el registro y lo desactiva para preservar trazabilidad.

No es una implementación completa de RFC 7643/7644 ni está certificada con OneLogin. No admite filtros generales, grupos, bulk, todos los atributos, todos los operadores PATCH ni toda semántica PUT. El token Bearer es un secreto compartido de laboratorio y autoriza operaciones administrativas SCIM.

## Seguridad de la demostración

- Secretos desde `.env`, ignorado por Git; la app requiere al menos 32 caracteres para `APP_SECRET` y `SCIM_TOKEN`.
- Cookies `HttpOnly`, `SameSite=Lax`; `Secure` se activa al usar `APP_BASE_URL=https://...`.
- CSRF para formularios POST; permisos revisados en el servidor.
- Límite de tamaño de request y límite de 500 eventos almacenados.
- Contenedores enlazados solo a loopback en la configuración incluida.

El modo local usa HTTP y marca `AUTHLIB_INSECURE_TRANSPORT` para que OIDC funcione en localhost. No uses esta configuración para desplegar en red. Producción requiere HTTPS, secretos propios, base de datos y copias, controles de red, monitoreo, pruebas de integración y revisión de seguridad.

## Documentación de referencia

- [Keycloak: contenedores](https://www.keycloak.org/server/containers)
- [Keycloak: importar un realm al inicio](https://www.keycloak.org/server/importExport)
- [Keycloak: health checks](https://www.keycloak.org/server/health)
- [Keycloak: configuración de producción](https://www.keycloak.org/server/configuration-production)
- [Authlib: cliente OIDC para Flask](https://docs.authlib.org/en/v1.6.6/client/flask.html)
- [Flask: opciones de despliegue](https://flask.palletsprojects.com/en/stable/deploying/)
