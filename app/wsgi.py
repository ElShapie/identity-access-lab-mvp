import hmac
import os
import re
import secrets
import sqlite3
from datetime import timedelta
from functools import wraps

import requests
from authlib.integrations.flask_client import OAuth
from flask import Flask, abort, jsonify, redirect, render_template_string, request, session

from app.store import Store

HOME = """<!doctype html><meta charset=utf-8><title>Identity Access Lab</title>
<h1>Identity Access Lab</h1>
<p>Sesión: {{ user.userName }} — rol: {{ user.title }} — cuenta: {{ 'activa' if user.active else 'inactiva' }}</p>
<p><a href=/consulta>Consulta</a> · <a href=/registros>Registros</a> · <a href=/admin/usuarios>Administrar usuarios</a></p>
<form action=/mantenimiento method=post><input type=hidden name=csrf value="{{ csrf }}"><button>Mantenimiento</button></form>
<form action=/admin method=post><input type=hidden name=csrf value="{{ csrf }}"><button>Administración de prueba</button></form>
<form action=/logout method=post><input type=hidden name=csrf value="{{ csrf }}"><button>Cerrar sesión</button></form>"""

USERS = """<!doctype html><meta charset=utf-8><title>Usuarios</title><h1>Usuarios del laboratorio</h1>
<p><a href=/>Inicio</a></p><table border=1 cellpadding=6><tr><th>Correo</th><th>Rol</th><th>Activo</th></tr>
{% for u in users %}<tr><td>{{ u.userName }}</td><td>{{ u.title }}</td><td>{{ u.active }}</td></tr>{% endfor %}</table>
<h2>Crear o actualizar por SCIM</h2><p>Utiliza el endpoint SCIM y token documentados; esta pantalla es solo consulta.</p>"""


def create_app():
    app = Flask(__name__)
    app.secret_key = os.environ["APP_SECRET"]
    app.config.update(
        SESSION_COOKIE_SECURE=False,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        PERMANENT_SESSION_LIFETIME=timedelta(minutes=15),
        MAX_CONTENT_LENGTH=65536,
    )
    base = os.environ.get("APP_BASE_URL", "http://localhost:8000").rstrip("/")
    scim_token = os.environ["SCIM_TOKEN"]
    if len(app.secret_key) < 32 or len(scim_token) < 32 or not base.startswith(("http://localhost", "https://")):
        raise RuntimeError("Configura secretos de 32+ caracteres y APP_BASE_URL localhost HTTP o HTTPS")
    app.config["SESSION_COOKIE_SECURE"] = base.startswith("https://")
    store = Store(os.environ.get("APP_DB", "data/lab.sqlite"))
    oauth = OAuth(app)
    oauth.register(
        name="idp",
        client_id=os.environ["OIDC_CLIENT_ID"],
        client_secret=os.environ["OIDC_CLIENT_SECRET"],
        server_metadata_url=os.environ["OIDC_METADATA_URL"],
        client_kwargs={"scope": "openid profile email"},
    )

    def scim_auth(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            expected = "Bearer " + scim_token
            if not hmac.compare_digest(request.headers.get("Authorization", ""), expected):
                return scim_error("No autorizado", 401)
            return fn(*args, **kwargs)
        return wrapped

    def require(action):
        def decorate(fn):
            @wraps(fn)
            def wrapped(*args, **kwargs):
                uid = session.get("uid")
                if not uid:
                    return redirect("/login")
                if not store.permitted(uid, action):
                    store.event(uid, action, "DENEGADO")
                    abort(403)
                if request.method == "POST" and not hmac.compare_digest(request.form.get("csrf", ""), session.get("csrf", "")):
                    abort(400)
                store.event(uid, action, "PERMITIDO")
                return fn(*args, **kwargs)
            return wrapped
        return decorate

    def scim_error(detail, status):
        return jsonify({"schemas": ["urn:ietf:params:scim:api:messages:2.0:Error"], "detail": detail, "status": str(status)}), status

    @app.get("/health")
    def health():
        return jsonify(status="ok")

    @app.get("/oidc/metadata")
    def oidc_metadata():
        """Descubre Keycloak desde la red Docker y usa URL internas para llamadas del servidor."""
        url = os.environ.get("OIDC_INTERNAL_METADATA_URL")
        if not url:
            return scim_error("Proxy de metadata local no configurado", 404)
        try:
            data = requests.get(url, timeout=5).json()
        except requests.RequestException:
            return jsonify(error="Proveedor OIDC local no disponible"), 503
        internal = os.environ.get("OIDC_INTERNAL_BASE_URL", "").rstrip("/")
        for key, suffix in (("token_endpoint", "/token"), ("userinfo_endpoint", "/userinfo"), ("jwks_uri", "/certs")):
            data[key] = internal + suffix
        return jsonify(data)

    @app.get("/")
    def home():
        uid = session.get("uid")
        user = store.get(uid) if uid else None
        if user and not user.get("active"):
            session.clear()
            user = None
        if not user:
            return "<h1>Identity Access Lab</h1><p><a href='/login'>Iniciar sesión</a></p>"
        session.setdefault("csrf", secrets.token_urlsafe(32))
        return render_template_string(HOME, user=user, csrf=session["csrf"])

    @app.get("/login")
    def login():
        return oauth.idp.authorize_redirect(base + "/auth/callback", prompt="login")

    @app.get("/auth/callback")
    def callback():
        try:
            token = oauth.idp.authorize_access_token()
            identity = token.get("userinfo") or oauth.idp.userinfo(token=token)
            if not identity or not identity.get("sub") or not identity.get("email"):
                abort(403)
            user = store.by_name(identity["email"])
            if not user or not user.get("active") or not store.bind_identity(user["id"], str(identity["sub"])):
                store.event("desconocido", "LOGIN", "DENEGADO")
                abort(403)
            session.clear()
            session["uid"] = user["id"]
            session["csrf"] = secrets.token_urlsafe(32)
            session.permanent = True
            store.event(user["id"], "LOGIN_OIDC", "PERMITIDO")
            return redirect("/")
        except Exception:
            app.logger.warning("Inicio OIDC rechazado o incompleto")
            abort(403)

    @app.get("/consulta")
    @require("consulta")
    def consultation():
        return "<h1>Consulta permitida</h1><a href='/'>Inicio</a>"

    @app.post("/mantenimiento")
    @require("mantenimiento")
    def maintenance():
        return "<h1>Mantenimiento permitido</h1><a href='/'>Inicio</a>"

    @app.post("/admin")
    @require("admin")
    def administration():
        return "<h1>Administración permitida</h1><a href='/'>Inicio</a>"

    @app.get("/registros")
    @require("registros")
    def records():
        return jsonify(store.events())

    @app.get("/admin/usuarios")
    @require("admin")
    def admin_users():
        return render_template_string(USERS, users=store.all())

    @app.post("/logout")
    def logout():
        if not session.get("uid") or not hmac.compare_digest(request.form.get("csrf", ""), session.get("csrf", "")):
            abort(400)
        store.event(session["uid"], "LOGOUT_APP", "OK")
        session.clear()
        return redirect("/")

    @app.route("/scim/v2/Users", methods=["GET", "POST"])
    @scim_auth
    def scim_users():
        if request.method == "GET":
            query = request.args.get("filter", "")
            if query:
                match = re.fullmatch(r'userName\s+eq\s+"([^"]+)"', query, re.IGNORECASE)
                if not match:
                    return scim_error('Solo se admite userName eq "correo"', 400)
                found = store.by_name(match.group(1))
                resources = [found] if found else []
            else:
                resources = store.all()
            start = max(1, request.args.get("startIndex", 1, type=int))
            count = max(0, min(100, request.args.get("count", 100, type=int)))
            page = resources[start - 1:start - 1 + count]
            return jsonify(schemas=["urn:ietf:params:scim:api:messages:2.0:ListResponse"], totalResults=len(resources), startIndex=start, itemsPerPage=len(page), Resources=page)
        try:
            result = store.save(request.get_json(force=True))
            response = jsonify(result)
            response.status_code = 201
            response.headers["Location"] = base + "/scim/v2/Users/" + result["id"]
            return response
        except sqlite3.IntegrityError:
            return scim_error("Usuario duplicado", 409)
        except (ValueError, TypeError):
            return scim_error("Datos no válidos", 400)

    @app.route("/scim/v2/Users/<user_id>", methods=["GET", "PUT", "PATCH", "DELETE"])
    @scim_auth
    def scim_user(user_id):
        current = store.get(user_id)
        if not current:
            return scim_error("Usuario no encontrado", 404)
        if request.method == "GET":
            return jsonify(current)
        if request.method == "DELETE":
            store.deactivate(user_id)
            return "", 204
        try:
            payload = request.get_json(force=True)
            if request.method == "PATCH":
                changes = {}
                if not isinstance(payload, dict) or not isinstance(payload.get("Operations"), list):
                    return scim_error("PATCH requiere Operations", 400)
                for operation in payload["Operations"]:
                    if not isinstance(operation, dict) or operation.get("op", "").lower() not in ("replace", "add"):
                        return scim_error("Operación PATCH no admitida", 400)
                    path = operation.get("path")
                    value = operation.get("value")
                    if path in ("active", "title", "userName"):
                        changes[path] = value
                    elif path is None and isinstance(value, dict):
                        changes.update(value)
                    else:
                        return scim_error("Ruta PATCH no admitida", 400)
                payload = changes
            return jsonify(store.save(payload, user_id))
        except sqlite3.IntegrityError:
            return scim_error("Usuario duplicado", 409)
        except (ValueError, TypeError):
            return scim_error("Datos no válidos", 400)

    @app.get("/scim/v2/Groups")
    @scim_auth
    def scim_groups():
        return jsonify(schemas=["urn:ietf:params:scim:api:messages:2.0:ListResponse"], totalResults=0, startIndex=1, itemsPerPage=0, Resources=[])

    return app


app = create_app()
