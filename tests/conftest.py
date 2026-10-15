import io

import pytest
from openpyxl import Workbook

from src import create_app


@pytest.fixture
def app():
    return create_app({"TESTING": True, "RATELIMIT_ENABLED": False})


@pytest.fixture
def client(app):
    return app.test_client()


def xlsx_bytes(rows):
    book = Workbook()
    for row in rows:
        book.active.append(row)
    stream = io.BytesIO()
    book.save(stream)
    book.close()
    return stream.getvalue()


def upload(client, data=b"id,name\n001,Ana\n", filename="input.csv", **fields):
    form = {"file-upload": (io.BytesIO(data), filename), "table-name": "records"}
    form.update(fields)
    return client.post("/process", data=form, content_type="multipart/form-data")
