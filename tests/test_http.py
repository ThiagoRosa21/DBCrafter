import io
import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

import pytest
from werkzeug.datastructures import MultiDict

from src import create_app
from src.converter import Limits
from tests.conftest import upload


def test_homepage_matches_supported_formats_and_has_accessible_form(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b".csv,.json,.xlsx,.xls" in response.data
    assert b'lang="pt-BR"' in response.data
    assert b'for="file-upload"' in response.data
    assert b"column-types" in response.data
    assert client.get("/static/style.css").status_code == 200


def test_success_download_is_private_and_does_not_create_files(client, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    response = upload(client)
    assert response.status_code == 200
    assert response.mimetype == "application/sql"
    assert response.headers["X-Converted-Rows"] == "1"
    assert "attachment; filename=inserts.sql" == response.headers["Content-Disposition"]
    assert response.headers["Cache-Control"] == "no-store"
    assert "ETag" not in response.headers
    assert list(tmp_path.iterdir()) == []


def test_upload_stream_never_spools_to_disk(app):
    with app.test_request_context(
        "/process", method="POST", data={"file-upload": (io.BytesIO(b"a" * 600_000), "a.csv")}
    ):
        from flask import request

        assert isinstance(request.files["file-upload"].stream, io.BytesIO)


def test_concurrent_users_receive_only_their_own_data(app):
    def job(index):
        with app.test_client() as client:
            response = upload(client, f"id,secret\n{index},private_value_{index:03d}\n".encode())
            return index, response.status_code, response.data

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(job, range(32)))
    for index, status, body in results:
        assert status == 200
        assert f"private_value_{index:03d}".encode() in body
        assert body.count(b"private_value_") == 1


@pytest.mark.parametrize(
    "fields",
    [
        {"table-name": ""},
        {"table-name": "a; DROP TABLE a"},
        {"limit": "-1"},
        {"limit": "0"},
        {"limit": "10001"},
        {"limit": "1.5"},
        {"limit": "١"},
        {"dialect": "bogus"},
        {"column-types": '{"missing":"text"}'},
        {"column-types": '{"id":[]}'},
        {"archive_type": "json"},
        {"delimiter": "||"},
        {"null-marker": ""},
        {"unknown": "value"},
    ],
)
def test_invalid_form_fields(client, fields):
    assert upload(client, **fields).status_code == 400


def test_missing_upload_and_duplicate_fields(client):
    assert client.post("/process", data={"table-name": "records"}).status_code == 400
    body = MultiDict(
        [
            ("table-name", "records"),
            ("table-name", "other"),
            ("file-upload", (io.BytesIO(b"a\n1"), "a.csv")),
        ]
    )
    assert client.post("/process", data=body).status_code == 400


def test_multiple_files_rejected(client):
    body = MultiDict(
        [
            ("table-name", "records"),
            ("file-upload", (io.BytesIO(b"a\n1"), "a.csv")),
            ("file-upload", (io.BytesIO(b"a\n2"), "b.csv")),
        ]
    )
    assert client.post("/process", data=body).status_code == 400


def test_request_body_and_file_limit(app):
    app.config["MAX_CONTENT_LENGTH"] = 1000
    assert upload(app.test_client(), b"a\n" + b"x" * 1001).status_code == 413
    app.config["MAX_CONTENT_LENGTH"] = 10000
    app.config["CONVERSION_LIMITS"] = replace(Limits(), upload_bytes=10)
    assert upload(app.test_client(), b"a\n" + b"x" * 11).status_code == 400


def test_form_parts_limit(app):
    app.config["MAX_FORM_PARTS"] = 2
    assert upload(app.test_client(), dialect="sqlite").status_code == 413


def test_rate_limit_and_forwarded_ip_spoofing():
    app = create_app({"TESTING": True, "UPLOAD_RATE_LIMIT": "1 per minute"})
    client = app.test_client()
    assert upload(client).status_code == 200
    response = client.post("/process", headers={"X-Forwarded-For": "203.0.113.7"})
    assert response.status_code == 429
    assert "Retry-After" in response.headers


def test_global_limit_across_distinct_clients():
    app = create_app({"TESTING": True, "GLOBAL_RATE_LIMIT": "1 per minute"})
    client = app.test_client()
    assert upload(client).status_code == 200
    response = client.post("/process", environ_overrides={"REMOTE_ADDR": "203.0.113.8"})
    assert response.status_code == 429


def test_cross_site_requests_are_rejected(client):
    for headers in [
        {"Origin": "https://evil.invalid"},
        {"Origin": "null"},
        {"Origin": "https://["},
        {"Sec-Fetch-Site": "cross-site"},
    ]:
        assert client.post("/process", headers=headers).status_code == 403


def test_same_origin_request(client):
    data = {"file-upload": (io.BytesIO(b"a\n1\n"), "a.csv"), "table-name": "records"}
    assert (
        client.post("/process", data=data, headers={"Origin": "http://localhost"}).status_code
        == 200
    )


def test_security_headers_on_success_and_error(client):
    for response in [
        client.get("/"),
        client.get("/missing"),
        upload(client),
        upload(client, b"broken", filename="bad.json"),
    ]:
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]
        assert response.headers["Referrer-Policy"] == "no-referrer"
        assert response.headers["Cache-Control"] == "no-store"
    assert "Strict-Transport-Security" in client.get("/", base_url="https://localhost").headers


def test_debug_is_disabled_even_if_config_requests_it():
    assert not create_app({"DEBUG": True}).debug


def test_parser_error_does_not_leak_data(client):
    response = upload(client, b'[{"SECRET_CELL": private}]', filename="broken.json")
    assert response.status_code == 400
    assert b"SECRET_CELL" not in response.data
    assert b"Traceback" not in response.data


def test_unexpected_errors_are_generic_and_logs_exclude_content(client, monkeypatch, caplog):
    def broken(*args, **kwargs):
        raise RuntimeError("private-data-and-server-path")

    monkeypatch.setattr("src.views.convert", broken)
    with caplog.at_level(logging.ERROR):
        response = upload(client)
    assert response.status_code == 500
    assert b"private-data-and-server-path" not in response.data
    assert "private-data-and-server-path" not in caplog.text
    assert "RuntimeError" in caplog.text


def test_health_check(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json == {"status": "ok"}
