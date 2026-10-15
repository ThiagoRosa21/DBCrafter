"""Flask application factory."""

import io
import logging

from flask import Flask, Request, render_template, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.exceptions import HTTPException
from werkzeug.middleware.proxy_fix import ProxyFix

from .converter import Limits


class MemoryUploadRequest(Request):
    def _get_file_stream(
        self, total_content_length, content_type, filename=None, content_length=None
    ):
        # MAX_CONTENT_LENGTH bounds the whole body before/while it is read.
        return io.BytesIO()


def create_app(test_config=None):
    app = Flask(__name__)
    app.request_class = MemoryUploadRequest
    app.config.from_mapping(
        MAX_CONTENT_LENGTH=5 * 1024 * 1024 + 64 * 1024,
        MAX_FORM_MEMORY_SIZE=64 * 1024,
        MAX_FORM_PARTS=8,
        RATELIMIT_STORAGE_URI="memory://",
        RATELIMIT_HEADERS_ENABLED=True,
        UPLOAD_RATE_LIMIT="10 per minute",
        GLOBAL_RATE_LIMIT="60 per minute",
        TRUSTED_PROXY_HOPS=0,
        CONVERSION_LIMITS=Limits(),
    )
    app.config.from_prefixed_env(prefix="DBCRAFTER")
    if test_config:
        app.config.update(test_config)
    app.config["DEBUG"] = False
    hops = app.config["TRUSTED_PROXY_HOPS"]
    if type(hops) is not int or not 0 <= hops <= 5:
        raise ValueError("TRUSTED_PROXY_HOPS must be an integer between 0 and 5")
    if hops:
        # Enable only behind proxies that cannot be bypassed by direct connections.
        app.wsgi_app = ProxyFix(
            app.wsgi_app, x_for=hops, x_proto=hops, x_host=0, x_port=0, x_prefix=0
        )

    limiter = Limiter(key_func=get_remote_address, app=app, default_limits=[])
    app.extensions["dbcrafter_limiter"] = limiter
    from .views import create_routes

    app.register_blueprint(create_routes(limiter))

    @app.after_request
    def security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; style-src 'self'; img-src 'self'; "
            "form-action 'self'; base-uri 'none'; frame-ancestors 'none'"
        )
        response.headers["Cache-Control"] = "no-store"
        if request.is_secure:
            response.headers["Strict-Transport-Security"] = "max-age=31536000"
        return response

    @app.errorhandler(HTTPException)
    def http_error(error):
        messages = {
            400: "Requisição inválida. Verifique os campos enviados.",
            403: "Origem da requisição não permitida.",
            404: "Página não encontrada.",
            405: "Método não permitido.",
            413: "O arquivo ou formulário excede o limite permitido.",
            429: "Muitas conversões. Aguarde antes de tentar novamente.",
        }
        response = error.get_response()
        response.set_data(
            render_template(
                "error.html",
                message=messages.get(error.code, "Não foi possível atender à requisição."),
            )
        )
        response.content_type = "text/html; charset=utf-8"
        return response

    @app.errorhandler(Exception)
    def unexpected_error(error):
        # Exception messages and tracebacks can contain private cell contents.
        app.logger.error("Unhandled conversion request error (%s)", type(error).__name__)
        return render_template(
            "error.html", message="Erro interno. Tente novamente mais tarde."
        ), 500

    app.logger.setLevel(logging.INFO)
    return app
