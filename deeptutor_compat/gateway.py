import os
from typing import Iterable

import httpx
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


BACKEND_PORT = _int("BACKEND_PORT", 8001)
FRONTEND_PORT = _int("FRONTEND_PORT", 3782)


def create_gateway_app() -> FastAPI:
    """
    A thin compat gateway that makes DeepTutor look like the agent_gateway
    contract expected by dynamic_router:
      - listens on a single port (dynamic_router uses CONTAINER_PORT, default 3000)
      - GET /health for readiness
      - proxies /api/* and /docs, /openapi.json to backend
      - proxies everything else to the Next.js frontend
      - proxies WebSocket /api/v1/ws to backend
    """

    gateway_app = FastAPI(title="DeepTutor Compat Gateway", docs_url=None, redoc_url=None)

    @gateway_app.get("/health")
    async def health():
        return {"status": "ok"}

    def _backend_url(path: str, query: str | None) -> str:
        url = f"http://127.0.0.1:{BACKEND_PORT}{path}"
        if query:
            url += f"?{query}"
        return url

    def _frontend_url(path: str, query: str | None) -> str:
        url = f"http://127.0.0.1:{FRONTEND_PORT}{path}"
        if query:
            url += f"?{query}"
        return url

    def _copy_headers(src: Iterable[tuple[str, str]]) -> dict[str, str]:
        # Keep cookies/auth, but strip hop-by-hop headers.
        skip = {
            "host",
            "connection",
            "keep-alive",
            "proxy-authenticate",
            "proxy-authorization",
            "te",
            "trailers",
            "transfer-encoding",
            "upgrade",
        }
        out: dict[str, str] = {}
        for k, v in src:
            if k.lower() not in skip:
                out[k] = v
        return out

    @gateway_app.websocket("/api/v1/ws")
    async def ws_proxy(ws: WebSocket):
        await ws.accept()
        upstream = f"ws://127.0.0.1:{BACKEND_PORT}/api/v1/ws"

        # Prefer websockets if available (uvicorn[standard] installs it).
        import websockets  # type: ignore

        try:
            async with websockets.connect(
                upstream,
                extra_headers=_copy_headers(ws.headers.raw),
                max_size=None,
            ) as upstream_ws:

                async def _client_to_upstream():
                    try:
                        while True:
                            msg = await ws.receive()
                            if "text" in msg and msg["text"] is not None:
                                await upstream_ws.send(msg["text"])
                            elif "bytes" in msg and msg["bytes"] is not None:
                                await upstream_ws.send(msg["bytes"])
                            else:
                                break
                    except WebSocketDisconnect:
                        pass
                    except RuntimeError:
                        pass

                async def _upstream_to_client():
                    try:
                        async for msg in upstream_ws:
                            if isinstance(msg, bytes):
                                await ws.send_bytes(msg)
                            else:
                                await ws.send_text(msg)
                    except RuntimeError:
                        pass

                import asyncio

                await asyncio.gather(_client_to_upstream(), _upstream_to_client())
        finally:
            try:
                await ws.close()
            except RuntimeError:
                pass

    @gateway_app.api_route(
        "/{path:path}",
        methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"],
    )
    async def proxy_all(request: Request, path: str):
        # Route selection:
        # - backend: /api/*, /docs, /openapi.json (and any future backend root assets)
        # - frontend: everything else
        full_path = "/" + path
        to_backend = (
            full_path.startswith("/api/")
            or full_path == "/api"
            or full_path.startswith("/docs")
            or full_path == "/openapi.json"
        )

        target = (
            _backend_url(full_path, request.url.query) if to_backend else _frontend_url(full_path, request.url.query)
        )

        headers = _copy_headers(request.headers.items())
        body = await request.body()

        timeout = httpx.Timeout(300.0, connect=10.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            upstream = await client.send(
                client.build_request(
                    method=request.method,
                    url=target,
                    headers=headers,
                    content=body,
                ),
                stream=True,
            )

            resp_headers = dict(upstream.headers)
            for h in ("transfer-encoding", "connection", "keep-alive"):
                resp_headers.pop(h, None)

            async def stream_body():
                async for chunk in upstream.aiter_bytes():
                    yield chunk
                await upstream.aclose()

            return StreamingResponse(
                content=stream_body(),
                status_code=upstream.status_code,
                headers=resp_headers,
            )

    return gateway_app


app = create_gateway_app()

