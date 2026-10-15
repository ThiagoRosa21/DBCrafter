"""HTTP validation and responses; conversion lives in converter.py."""

from pathlib import PurePath
from urllib.parse import urlsplit

from flask import Blueprint, abort, current_app, render_template, request, send_file

from .converter import ConversionError, convert, parse_types


def create_routes(limiter):
    routes = Blueprint("web", __name__)

    @routes.get("/")
    def homepage_view():
        return render_template("homepage.html", limits=current_app.config["CONVERSION_LIMITS"])

    @routes.get("/healthz")
    def health():
        return {"status": "ok"}

    @routes.post("/process")
    @limiter.limit(lambda: current_app.config["UPLOAD_RATE_LIMIT"])
    @limiter.limit(
        lambda: current_app.config["GLOBAL_RATE_LIMIT"], key_func=lambda: "global-upload"
    )
    def process():
        origin = request.headers.get("Origin")
        if request.headers.get("Sec-Fetch-Site") == "cross-site":
            abort(403)
        if origin:
            try:
                parsed = urlsplit(origin)
                if parsed.scheme not in {"http", "https"} or parsed.netloc != request.host:
                    abort(403)
            except ValueError:
                abort(403)
        limits = current_app.config["CONVERSION_LIMITS"]
        try:
            files = request.files.getlist("file-upload")
            if len(files) != 1 or len(request.files) != 1 or not files[0].filename:
                raise ConversionError("Envie exatamente um arquivo CSV, JSON, XLSX ou XLS.")
            allowed = {
                "table-name",
                "archive_type",
                "limit",
                "dialect",
                "column-types",
                "delimiter",
                "null-marker",
            }
            if set(request.form) - allowed or any(
                len(request.form.getlist(key)) != 1 for key in request.form
            ):
                raise ConversionError("Formulário inválido: há campos desconhecidos ou duplicados.")
            table = request.form.get("table-name", "").strip()
            dialect = request.form.get("dialect", "sqlite")
            extension = PurePath(files[0].filename).suffix.lower().lstrip(".")
            selected = request.form.get("archive_type", "auto")
            expected = "excel" if extension in {"xlsx", "xls"} else extension
            if selected not in {"auto", expected}:
                raise ConversionError("O tipo selecionado não corresponde à extensão do arquivo.")
            raw_limit = request.form.get("limit", "")
            if raw_limit and (
                not raw_limit.isascii() or not raw_limit.isdigit() or len(raw_limit) > 6
            ):
                raise ConversionError("Informe um limite de linhas inteiro e positivo.")
            output, count = convert(
                files[0].read(limits.upload_bytes + 1),
                extension,
                table,
                dialect,
                row_limit=int(raw_limit) if raw_limit else None,
                types=parse_types(request.form.get("column-types", "")),
                delimiter=request.form.get("delimiter", ","),
                null_marker=request.form.get("null-marker", "\\N"),
                limits=limits,
            )
        except ConversionError as error:
            return render_template("error.html", message=str(error)), 400
        response = send_file(
            output,
            as_attachment=True,
            download_name="inserts.sql",
            mimetype="application/sql",
            etag=False,
            max_age=0,
        )
        response.headers["X-Converted-Rows"] = str(count)
        return response

    return routes
