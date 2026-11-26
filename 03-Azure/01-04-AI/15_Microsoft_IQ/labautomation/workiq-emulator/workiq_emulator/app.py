"""Starlette ASGI app: /mcp, /healthz, /admin/* and the read-only /viewer."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from urllib.parse import parse_qs, quote

from starlette.applications import Starlette
from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from starlette.routing import Route
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from . import auth, mcp
from .state import AppState, ToolContext
from .store import PackError
from .viewer import pages

log = logging.getLogger("workiq.app")

MAX_MCP_BODY = 256 * 1024
MAX_ADMIN_BODY = 4 * 1024 * 1024
MAX_ADMIN_ITEM_BODY = 128 * 1024
MAX_FORM_BODY = 4 * 1024
STATIC_DIR = Path(__file__).resolve().parent / "viewer" / "static"
CSP = (
    "default-src 'self'; script-src 'none'; style-src 'self'; img-src 'self' data:; object-src 'none'; "
    "base-uri 'none'; form-action 'self'; frame-ancestors 'none'"
)
SECURITY_HEADERS = [
    (b"content-security-policy", CSP.encode()),
    (b"x-content-type-options", b"nosniff"),
    (b"x-frame-options", b"DENY"),
    (b"referrer-policy", b"no-referrer"),
    (b"cache-control", b"no-store"),
]


class SecurityHeaders:
    """Adds security headers to every response. No CORS headers are ever sent."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                existing = {k.lower() for k, _ in message.get("headers", [])}
                headers = list(message.get("headers", []))
                headers += [(k, v) for k, v in SECURITY_HEADERS if k not in existing]
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_wrapper)


def _json_error(status: int, error: str, message: str, headers: dict | None = None) -> JSONResponse:
    return JSONResponse({"error": error, "message": message}, status_code=status, headers=headers)


def _unauthorized(message: str = "A valid persona key is required: Authorization: Bearer <key>.") -> JSONResponse:
    return _json_error(401, "unauthorized", message, {"WWW-Authenticate": 'Bearer realm="workiq-emulator"'})


MISCONFIGURED = (
    "No persona keys are configured. Set the WORKIQ_KEY_<PERSONA> app settings, "
    "or set WORKIQ_DEV_MODE=true for local development."
)


def create_app(state: AppState | None = None) -> Starlette:
    st = state or AppState()
    if st.settings.ignored_keys:
        log.warning("ignored keys shorter than 16 characters: %s", ", ".join(st.settings.ignored_keys))
    log.info("workiq emulator ready: items=%d auth=%s", st.store.item_count(), st.settings.auth_mode)

    def base_url(request: Request) -> str:
        if st.settings.public_base_url:
            return st.settings.public_base_url
        proto = request.headers.get("x-forwarded-proto", request.url.scheme).split(",")[0].strip()
        return f"{proto}://{request.url.netloc}"

    def origin_ok(request: Request) -> bool:
        origin = request.headers.get("origin")
        if not origin:
            return True
        return origin.rstrip("/") == base_url(request) or origin.rstrip("/") == f"{request.url.scheme}://{request.url.netloc}"

    async def read_body(request: Request, limit: int) -> bytes | None:
        cl = request.headers.get("content-length")
        if cl and cl.isdigit() and int(cl) > limit:
            return None
        body = await request.body()
        return None if len(body) > limit else body

    def resolve_persona(request: Request) -> str | None:
        if st.settings.auth_mode == "keys":
            return auth.persona_for_key(st.settings, auth.parse_bearer(request.headers.get("authorization")))
        pid = (request.headers.get("x-workiq-persona") or "").strip()
        return pid if pid in st.store.personas else None

    # -- MCP ------------------------------------------------------------------

    async def mcp_post(request: Request) -> Response:
        if st.settings.auth_mode == "misconfigured":
            return _json_error(503, "server_misconfigured", MISCONFIGURED)
        if not origin_ok(request):
            return _json_error(403, "forbidden", "Cross-origin requests are not allowed.")
        pid = resolve_persona(request)
        if pid is None:
            return _unauthorized()
        ctype = request.headers.get("content-type", "").split(";")[0].strip().lower()
        if ctype != "application/json":
            return _json_error(415, "unsupported_media_type", "Content-Type must be application/json.")
        body = await read_body(request, MAX_MCP_BODY)
        if body is None:
            return _json_error(413, "payload_too_large", f"The request body is larger than {MAX_MCP_BODY} bytes.")
        store = st.store
        ctx = ToolContext(state=st, store=store, persona=store.personas[pid], base_url=base_url(request))
        result = await run_in_threadpool(mcp.handle, body, ctx)
        for level, line in ctx.logs:
            log.log(level, line)
        if result.payload is None:
            return Response(status_code=result.status, headers=result.headers)
        accept = request.headers.get("accept", "")
        if "text/event-stream" in accept and "application/json" not in accept:
            data = json.dumps(result.payload, ensure_ascii=False)
            return Response(f"event: message\ndata: {data}\n\n", status_code=result.status, media_type="text/event-stream", headers=result.headers)
        return JSONResponse(result.payload, status_code=result.status, headers=result.headers)

    async def mcp_other(request: Request) -> Response:
        return Response(status_code=405, headers={"Allow": "POST"})

    async def healthz(request: Request) -> Response:
        return JSONResponse({"status": "ok", "items": st.store.item_count()})

    # -- Admin ----------------------------------------------------------------

    def admin_check(request: Request) -> Response | None:
        if not st.settings.admin_key:
            return _json_error(403, "admin_disabled", "Admin endpoints are disabled because WORKIQ_ADMIN_KEY is not set.")
        if not auth.is_admin(st.settings, auth.parse_bearer(request.headers.get("authorization"))):
            return _unauthorized("A valid admin key is required.")
        return None

    async def admin_seed(request: Request) -> Response:
        if denied := admin_check(request):
            return denied
        body = await read_body(request, MAX_ADMIN_BODY)
        if body is None:
            return _json_error(413, "payload_too_large", f"The pack is larger than {MAX_ADMIN_BODY} bytes.")
        try:
            store = st.replace_pack(json.loads(body))
        except json.JSONDecodeError:
            return _json_error(400, "invalid_json", "The body is not valid JSON.")
        except PackError as err:
            return _json_error(400, "invalid_pack", str(err))
        log.info("admin seed replaced: items=%d", store.item_count())
        return JSONResponse({"status": "ok", "items": store.item_count()})

    async def admin_items(request: Request) -> Response:
        if denied := admin_check(request):
            return denied
        body = await read_body(request, MAX_ADMIN_ITEM_BODY)
        if body is None:
            return _json_error(413, "payload_too_large", f"The item is larger than {MAX_ADMIN_ITEM_BODY} bytes.")
        try:
            item = json.loads(body)
            if isinstance(item, dict) and item.get("id") in st.store.by_item_id:
                raise PackError(f"item '{item['id']}': duplicate id")
            store = st.append_item(item)
        except json.JSONDecodeError:
            return _json_error(400, "invalid_json", "The body is not valid JSON.")
        except PackError as err:
            return _json_error(400, "invalid_item", str(err))
        log.info("admin item appended: type=%s items=%d", item.get("type"), store.item_count())
        return JSONResponse({"status": "ok", "id": item["id"], "items": store.item_count()}, status_code=201)

    async def admin_reset(request: Request) -> Response:
        if denied := admin_check(request):
            return denied
        store = st.reset()
        log.info("admin reset: items=%d", store.item_count())
        return JSONResponse({"status": "ok", "items": store.item_count()})

    async def admin_pack(request: Request) -> Response:
        if denied := admin_check(request):
            return denied
        return JSONResponse(st.store.pack)

    # -- Viewer ---------------------------------------------------------------

    def viewer_persona(request: Request):
        pid = auth.read_session(st.settings, request.cookies.get(auth.SESSION_COOKIE))
        return st.store.personas.get(pid) if pid else None

    def to_login(request: Request) -> Response:
        return RedirectResponse(f"/viewer/login?next={quote(request.url.path, safe='/')}", status_code=303)

    def safe_next(value: str | None) -> str:
        if value and value.startswith("/viewer/") and "//" not in value and "\\" not in value and len(value) < 300:
            return value
        return "/viewer/mail"

    def misconfigured_page() -> HTMLResponse:
        return HTMLResponse(pages.message_page("Service not configured", MISCONFIGURED), status_code=503)

    async def viewer_root(request: Request) -> Response:
        return RedirectResponse("/viewer/mail", status_code=303)

    async def login_get(request: Request) -> Response:
        if st.settings.auth_mode == "misconfigured":
            return misconfigured_page()
        if viewer_persona(request):
            return RedirectResponse("/viewer/mail", status_code=303)
        return HTMLResponse(pages.login_page(next_url=safe_next(request.query_params.get("next")), dev_hint=st.settings.auth_mode == "dev"))

    async def login_post(request: Request) -> Response:
        if st.settings.auth_mode == "misconfigured":
            return misconfigured_page()
        if not origin_ok(request):
            return HTMLResponse(pages.message_page("Forbidden", "Cross-origin form posts are not allowed."), status_code=403)
        body = await read_body(request, MAX_FORM_BODY)
        if body is None:
            return HTMLResponse(pages.message_page("Too large", "The form is too large."), status_code=413)
        form = parse_qs(body.decode("utf-8", "replace"), max_num_fields=5)
        key = (form.get("key") or [""])[0].strip()
        nxt = safe_next((form.get("next") or [""])[0])
        dev = st.settings.auth_mode == "dev"
        pid = (key if key in st.store.personas else None) if dev else auth.persona_for_key(st.settings, key)
        if not pid:
            log.info("viewer login failed")
            return HTMLResponse(pages.login_page("That key is not valid.", nxt, dev), status_code=401)
        resp = RedirectResponse(nxt, status_code=303)
        resp.set_cookie(
            auth.SESSION_COOKIE,
            auth.make_session(st.settings, pid),
            max_age=auth.SESSION_TTL_SECONDS,
            path="/viewer",
            secure=base_url(request).startswith("https://"),
            httponly=True,
            samesite="strict",
        )
        log.info("viewer login persona=%s", pid)
        return resp

    async def logout(request: Request) -> Response:
        if not origin_ok(request):
            return HTMLResponse(pages.message_page("Forbidden", "Cross-origin form posts are not allowed."), status_code=403)
        resp = RedirectResponse("/viewer/login", status_code=303)
        resp.delete_cookie(auth.SESSION_COOKIE, path="/viewer", secure=base_url(request).startswith("https://"), httponly=True, samesite="strict")
        return resp

    def section(kind: str | None, render):
        async def handler(request: Request) -> Response:
            if st.settings.auth_mode == "misconfigured":
                return misconfigured_page()
            persona = viewer_persona(request)
            if not persona:
                return to_login(request)
            store = st.store
            selected = None
            gid = request.path_params.get("gid")
            if gid is not None:
                selected = store.get_visible(gid, persona.id, kind)
                if selected is None:
                    # Same answer for "missing" and "not yours", so the viewer is no existence oracle.
                    return HTMLResponse(pages.message_page("Not found", "This item does not exist or you do not have access to it.", persona), status_code=404)
            return HTMLResponse(render(store, persona, selected))

        return handler

    async def people(request: Request) -> Response:
        if st.settings.auth_mode == "misconfigured":
            return misconfigured_page()
        persona = viewer_persona(request)
        if not persona:
            return to_login(request)
        return HTMLResponse(pages.people_page(st.store, persona))

    async def activity(request: Request) -> Response:
        if st.settings.auth_mode == "misconfigured":
            return misconfigured_page()
        persona = viewer_persona(request)
        if not persona:
            return to_login(request)
        return HTMLResponse(pages.activity_page(persona, st.activity(persona.id)))

    css = (STATIC_DIR / "style.css").read_bytes()

    async def static_css(request: Request) -> Response:
        return Response(css, media_type="text/css", headers={"Cache-Control": "public, max-age=3600"})

    async def root(request: Request) -> Response:
        return RedirectResponse("/viewer", status_code=303)

    routes = [
        Route("/", root, methods=["GET"]),
        Route("/mcp", mcp_post, methods=["POST"]),
        Route("/mcp", mcp_other, methods=["GET", "DELETE", "PUT", "PATCH"]),
        Route("/healthz", healthz, methods=["GET"]),
        Route("/admin/seed", admin_seed, methods=["POST"]),
        Route("/admin/items", admin_items, methods=["POST"]),
        Route("/admin/reset", admin_reset, methods=["POST"]),
        Route("/admin/pack", admin_pack, methods=["GET"]),
        Route("/viewer", viewer_root, methods=["GET"]),
        Route("/viewer/login", login_get, methods=["GET"]),
        Route("/viewer/login", login_post, methods=["POST"]),
        Route("/viewer/logout", logout, methods=["POST"]),
        Route("/viewer/static/style.css", static_css, methods=["GET"]),
        Route("/viewer/mail", section("email", pages.mail_page), methods=["GET"]),
        Route("/viewer/mail/{gid}", section("email", pages.mail_page), methods=["GET"]),
        Route("/viewer/chats", section("chat", pages.chats_page), methods=["GET"]),
        Route("/viewer/chats/{gid:path}", section("chat", pages.chats_page), methods=["GET"]),
        Route("/viewer/calendar", section("event", pages.calendar_page), methods=["GET"]),
        Route("/viewer/calendar/{gid}", section("event", pages.calendar_page), methods=["GET"]),
        Route("/viewer/files", section("file", pages.files_page), methods=["GET"]),
        Route("/viewer/files/{gid}", section("file", pages.files_page), methods=["GET"]),
        Route("/viewer/people", people, methods=["GET"]),
        Route("/viewer/people/{gid}", people, methods=["GET"]),
        Route("/viewer/activity", activity, methods=["GET"]),
    ]
    app = Starlette(routes=routes)
    app.state.wiq = st
    return SecurityHeaders(app)  # type: ignore[return-value]
