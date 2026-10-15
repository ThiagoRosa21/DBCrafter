import csv
import io
import json
import sqlite3
import zipfile
from dataclasses import replace
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
import xlwt

from src.converter import ConversionError, Limits, cast_value, convert, parse_types, sql_literal
from tests.conftest import xlsx_bytes


def script(data, extension="csv", **options):
    output, count = convert(data, extension, "records", **options)
    assert count > 0
    return output.getvalue().decode()


def execute(sql, schema):
    with sqlite3.connect(":memory:") as conn:
        conn.execute(schema)
        conn.executescript(sql)
        return conn.execute("SELECT * FROM records").fetchall()


def test_csv_round_trip_does_not_change_identifiers_or_empty_values():
    data = "Código,Nome,Observação\n00123,O'Brien,\n00002,NA,\\N\n00003,NULL,ação\n".encode()
    sql = script(data)
    assert execute(sql, "CREATE TABLE records (codigo TEXT, nome TEXT, observacao TEXT)") == [
        ("00123", "O'Brien", ""),
        ("00002", "NA", None),
        ("00003", "NULL", "ação"),
    ]


def test_injection_payloads_remain_data():
    values = ["'); DROP TABLE records;--", "\\'); SELECT 1;--", "a\nb\r\tc", "&name", '";--', "\\N"]
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow(["value"])
    writer.writerows([[v] for v in values])
    sql = script(stream.getvalue().encode(), null_marker="<NULL>")
    assert execute(sql, "CREATE TABLE records (value TEXT)") == [(v,) for v in values]
    assert len(sql.splitlines()) == len(values)


def test_types_are_explicit_in_csv():
    sql = script(
        b"id,price,active,day\n001,123.450,true,2026-10-15\n",
        types={"id": "integer", "price": "decimal", "active": "boolean", "day": "date"},
    )
    assert "VALUES (1, 123.450, 1, '2026-10-15')" in sql
    assert execute(
        sql, "CREATE TABLE records (id INTEGER, price NUMERIC, active INTEGER, day TEXT)"
    )[0] == (1, 123.45, 1, "2026-10-15")


def test_json_decimal_precision_boolean_and_null():
    sql = script(
        b'[{"price":12345678901234567890.123456789,"id":"001","active":true,"other":null}]', "json"
    )
    assert "12345678901234567890.123456789, '001', 1, NULL" in sql
    assert "'12345678901234567890.123456789'" not in sql


def test_json_key_order_is_not_column_order():
    sql = script(b'[{"a":1,"b":2},{"b":3,"a":4}]', "json")
    assert execute(sql, "CREATE TABLE records (a, b)") == [(1, 2), (4, 3)]


@pytest.mark.parametrize(
    "data",
    [
        b'[{"a":1,"a":2}]',
        b'[{"a":NaN}]',
        b'[{"a":Infinity}]',
        b'[{"a":1e9999}]',
        b'[{"a":{}}]',
        b'[{"a":[]}]',
        b'[{"a":1},{"b":2}]',
        b"[]",
        b"{}",
        b"[1]",
        b"[{}]",
        b'[{"a":"\\u0000"}]',
        b'[{"a":"\\ud800"}]',
        b"[" * 10 + b"0" + b"]" * 10,
        b'[{"a":1},]',
        b'[{"a":1}]junk',
    ],
)
def test_rejects_ambiguous_or_invalid_json(data):
    with pytest.raises(ConversionError):
        script(data, "json")


@pytest.mark.parametrize(
    "table", ["", "x;DROP TABLE x", "x)--", 'x"', "1x", "x y", "a.b.c", "a.", "x" * 64, "../data"]
)
def test_rejects_unsafe_identifiers(table):
    with pytest.raises(ConversionError):
        convert(b"id\n1\n", "csv", table)


def test_schema_and_reserved_identifiers_are_quoted():
    output, _ = convert(b"select\n1\n", "csv", "main.order")
    with sqlite3.connect(":memory:") as conn:
        conn.execute('CREATE TABLE "order" ("select" TEXT)')
        conn.executescript(output.getvalue().decode())
        assert conn.execute('SELECT "select" FROM "order"').fetchone() == ("1",)


@pytest.mark.parametrize("header", ["nome-cliente,nome cliente", "a,a", ",b", "💥", "x" * 64])
def test_rejects_bad_headers(header):
    with pytest.raises(ConversionError):
        script((header + "\n1,2\n").encode())


def test_deterministic_header_normalization():
    sql = script("Árvore,1 coluna\nsim,ok\n".encode())
    assert '("arvore", "c_1_coluna")' in sql


@pytest.mark.parametrize(
    "data", [b"a,b\n1\n", b"a\n1,2\n", b'a\n"unterminated', b"a\n\xff\n", b"a\n"]
)
def test_rejects_broken_csv(data):
    with pytest.raises(ConversionError):
        script(data)


def test_csv_bom_delimiter_and_explicit_null_marker():
    sql = script("\ufeffa;b\n01;vazio\n".encode(), delimiter=";", null_marker="vazio")
    assert execute(sql, "CREATE TABLE records (a TEXT, b TEXT)") == [("01", None)]


def test_requested_limit_stops_before_later_csv_rows_are_parsed():
    sql = script(b'a\n1\n"broken', row_limit=1)
    assert execute(sql, "CREATE TABLE records (a TEXT)") == [("1",)]


@pytest.mark.parametrize("limit", [-1, 0, 10001, True, 1.5])
def test_invalid_row_limits(limit):
    with pytest.raises(ConversionError):
        script(b"a\n1\n", row_limit=limit)


@pytest.mark.parametrize(
    "changes,data",
    [
        ({"upload_bytes": 3}, b"a\n1\n"),
        ({"output_bytes": 10}, b"a\n1\n"),
        ({"rows": 1}, b"a\n1\n2\n"),
        ({"columns": 1}, b"a,b\n1,2\n"),
        ({"cells": 1}, b"a,b\n1,2\n"),
        ({"cell_chars": 3}, b"a\nlong\n"),
        ({"seconds": -1}, b"a\n1\n"),
    ],
)
def test_resource_limits(changes, data):
    with pytest.raises(ConversionError):
        script(data, limits=replace(Limits(), **changes))


def test_xlsx_native_types_dates_and_trailing_nulls():
    data = xlsx_bytes(
        [
            ["id", "price", "active", "day", "other"],
            ["001", 12.5, True, datetime(2026, 10, 15), None],
        ]
    )
    sql = script(data, "xlsx")
    assert execute(
        sql, "CREATE TABLE records (id TEXT, price REAL, active INTEGER, day TEXT, other TEXT)"
    ) == [("001", 12.5, 1, "2026-10-15 00:00:00", None)]


def test_xlsx_formula_rejected():
    with pytest.raises(ConversionError, match="fórmulas"):
        script(xlsx_bytes([["result"], ["=1+1"]]), "xlsx")


def test_xlsx_zip_limit_is_applied_before_parser():
    with pytest.raises(ConversionError, match="descompactado"):
        script(xlsx_bytes([["id"], [1]]), "xlsx", limits=replace(Limits(), zip_bytes=10))


def test_xlsx_rejects_xml_entity_expansion():
    source = io.BytesIO(xlsx_bytes([["id"], [1]]))
    target = io.BytesIO()
    with zipfile.ZipFile(source) as old, zipfile.ZipFile(target, "w") as new:
        for item in old.infolist():
            content = old.read(item.filename)
            if item.filename == "xl/worksheets/sheet1.xml":
                content = (
                    b'<!DOCTYPE worksheet [<!ENTITY private SYSTEM "file:///etc/passwd">]>'
                    + content.replace(b">id<", b">&private;<")
                )
            new.writestr(item, content)
    with pytest.raises(ConversionError):
        script(target.getvalue(), "xlsx")


def test_xls_legacy_reader_handles_values():
    book = xlwt.Workbook()
    sheet = book.add_sheet("Data")
    for row, values in enumerate([["id", "amount"], ["001", 12.5]]):
        for column, value in enumerate(values):
            sheet.write(row, column, value)
    data = io.BytesIO()
    book.save(data)
    sql = script(data.getvalue(), "xls")
    assert execute(sql, "CREATE TABLE records (id TEXT, amount REAL)") == [("001", 12.5)]


@pytest.mark.parametrize("extension", ["xlsx", "xls", "json"])
def test_extension_is_not_trusted_as_content(extension):
    with pytest.raises(ConversionError):
        script(b"not a workbook or JSON", extension)


def test_postgresql_escaping_and_native_types():
    sql = script(
        json.dumps([{"name": "\\'; SELECT 1; --\n", "active": True, "amount": 42}]).encode(),
        "json",
        dialect="postgresql",
    )
    assert "E'\\\\''; SELECT 1; --\\n', TRUE, 42" in sql
    assert len(sql.splitlines()) == 1


def test_mysql_text_is_mode_independent_utf8_hex():
    value = "ação\\';--\n"
    sql = script(json.dumps([{"name": value}]).encode(), "json", dialect="mysql")
    assert "CONVERT(X'" + value.encode().hex() + "' USING utf8mb4)" in sql
    assert "INSERT INTO `records` (`name`)" in sql


def test_oracle_identifiers_and_client_substitution():
    sql = script(
        json.dumps([{"name": "A&B\nC", "active": True}]).encode(), "json", dialect="oracle"
    )
    assert 'INSERT INTO "RECORDS" ("NAME", "ACTIVE")' in sql
    assert "'A' || CHR(38) || 'B' || CHR(10) || 'C', 1" in sql
    assert "&" not in sql


def test_oracle_empty_text_is_not_silently_changed_to_null():
    with pytest.raises(ConversionError, match="vazio"):
        script(b"a,b\n1,\n", dialect="oracle")


@pytest.mark.parametrize("dialect", ["postgresql", "mysql", "oracle"])
def test_temporal_literals(dialect):
    assert sql_literal(date(2026, 10, 15), dialect) == "DATE '2026-10-15'"
    assert sql_literal(datetime(2026, 10, 15, 12, 30), dialect) == "TIMESTAMP '2026-10-15 12:30:00'"


def test_timezone_is_preserved_or_rejected():
    value = datetime(2026, 10, 15, tzinfo=timezone.utc)
    assert "+00:00" in sql_literal(value, "postgresql")
    with pytest.raises(ConversionError):
        sql_literal(value, "mysql")


@pytest.mark.parametrize("value", [float("inf"), float("nan"), Decimal("NaN"), Decimal("1e999")])
def test_no_nonfinite_or_unbounded_numbers(value):
    with pytest.raises(ConversionError):
        sql_literal(value, "sqlite")


@pytest.mark.parametrize(
    "value,target",
    [
        ("1.1", "integer"),
        ("12,34", "decimal"),
        ("maybe", "boolean"),
        ("2026-02-30", "date"),
        ("yesterday", "datetime"),
    ],
)
def test_invalid_explicit_types_do_not_guess(value, target):
    with pytest.raises(ConversionError):
        cast_value(value, target)


@pytest.mark.parametrize(
    "raw", ["[]", '{"id":"unknown"}', '{"id":[]}', '{"id":"text","id":"integer"}', "not JSON"]
)
def test_type_map_validation(raw):
    with pytest.raises(ConversionError):
        parse_types(raw)
