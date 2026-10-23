from __future__ import annotations

from starlette.responses import JSONResponse


class RequestSizeLimitMiddleware:
    def __init__(self, app, upload_max_bytes: int):
        self.app = app
        self.upload_max_bytes = max(1024, upload_max_bytes)

    async def __call__(self, scope, receive, send):
        sensitive = scope.get("path", "").startswith(("/v1/auth/", "/v1/projects", "/v1/geometry/generate", "/v1/geometry/edit", "/v1/geometry/calibrate"))
        if scope["type"] != "http" or not sensitive:
            await self.app(scope, receive, send)
            return
        maximum = self.upload_max_bytes if scope["path"].startswith("/v1/geometry/generate-from-image") else 64 * 1024
        headers = dict(scope.get("headers", []))
        raw_length = headers.get(b"content-length")
        if raw_length:
            try:
                if int(raw_length) > maximum:
                    response = JSONResponse({"detail": "Request body exceeds the configured size limit."}, status_code=413)
                    await response(scope, receive, send)
                    return
            except ValueError:
                response = JSONResponse({"detail": "Invalid Content-Length header."}, status_code=400)
                await response(scope, receive, send)
                return
        received = 0
        rejected = False

        async def limited_receive():
            nonlocal received, rejected
            message = await receive()
            if message["type"] == "http.request" and not rejected:
                received += len(message.get("body", b""))
                if received > maximum:
                    rejected = True
                    return {"type": "http.request", "body": b"", "more_body": False}
            return message

        async def guarded_send(message):
            if rejected and message["type"] == "http.response.start":
                response = JSONResponse({"detail": "Request body exceeds the configured size limit."}, status_code=413)
                await response(scope, receive, send)
                return
            if not rejected:
                await send(message)

        await self.app(scope, limited_receive, guarded_send)
