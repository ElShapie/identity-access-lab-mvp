# Conectar un tenant OneLogin (opcional)

Esta guía describe la adaptación; el Compose predeterminado usa Keycloak local y no necesita cuenta OneLogin. No conectes un tenant institucional sin autorización del administrador.

## Requisitos externos

- Tenant OneLogin y aplicación OIDC de servidor autorizados.
- URL HTTPS pública para la app con certificado válido y callback estable.
- Un conector SCIM que pueda enviar la versión del perfil implementado por esta app; comprobarlo con una cuenta no productiva.
- Secretos almacenados fuera del repositorio.

El modo Compose de demo está enlazado a localhost y no publica una URL HTTPS. No basta con cambiar `APP_BASE_URL` para usarlo desde OneLogin; hace falta un proxy HTTPS y configurar el callback público.

## MFA/TOTP del proveedor

La exigencia TOTP configurada en `keycloak/identity-access-realm.json` solo protege el realm local de demostración. No se transfiere a OneLogin al cambiar el proveedor OIDC. Para el ejercicio OneLogin, habilita una política MFA/TOTP en el tenant autorizado y prueba el flujo con una cuenta no productiva; no des por protegida la aplicación por la configuración local de Keycloak.

## Configuración OIDC de la app

1. En OneLogin registra una aplicación OIDC de tipo servidor con Authorization Code.
2. Registra exactamente `<APP_BASE_URL>/auth/callback` como redirect URI.
3. Usa el client ID, secreto y URL de discovery (`.well-known/openid-configuration`) del tenant.
4. En el despliegue autorizado configura:

   - `APP_BASE_URL=https://<host-autorizado>`
   - `OIDC_METADATA_URL=https://<tenant>/.well-known/openid-configuration`
   - `OIDC_CLIENT_ID` y `OIDC_CLIENT_SECRET` con valores del tenant

5. El Compose incluido está diseñado para Keycloak local: establece las variables `OIDC_INTERNAL_*` y habilita `AUTHLIB_INSECURE_TRANSPORT` para HTTP de laboratorio. Para OneLogin, prepara una configuración de despliegue separada que no incluya esas variables, usa el `OIDC_METADATA_URL` externo y sirve la aplicación detrás de un proxy TLS confiable. No intentes cambiar a OneLogin editando solo el `.env` del Compose local.
6. Aprovisiona primero los usuarios por SCIM con roles permitidos; luego prueba OIDC con un usuario de laboratorio.

## Limitación SCIM que debes verificar antes de integrar

El perfil de este MVP es deliberadamente reducido. En particular, el token compartido y el esquema `title` de rol son decisiones de laboratorio. Verifica en el conector OneLogin los métodos, campos, paginación y operación de suspensión/desactivación que enviará. Ejecuta una prueba de alta, cambio de rol, desactivación y sesión existente, y conserva solo evidencia ficticia.

Si el conector requiere una función que no está implementada, no la declares soportada: amplía y prueba el perfil en una rama separada antes de usarla.

