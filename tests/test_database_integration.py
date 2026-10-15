"""Opt-in integration tests against disposable databases provisioned by CI."""

import json
import os
from datetime import date, datetime
from decimal import Decimal

import pytest

from src.converter import convert


@pytest.mark.parametrize("dialect", ["postgresql", "mysql"])
def test_generated_sql_round_trip_in_real_database(dialect):
    env_name = "TEST_POSTGRES_DSN" if dialect == "postgresql" else "TEST_MYSQL_HOST"
    if not os.environ.get(env_name):
        pytest.skip(f"{env_name} is not configured; no real database was contacted")
    if dialect == "postgresql":
        import psycopg

        connection = psycopg.connect(os.environ[env_name])
    else:
        import pymysql

        connection = pymysql.connect(
            host=os.environ[env_name],
            user="root",
            password="test-only",
            database="dbcrafter_test",
            charset="utf8mb4",
        )
    values = ["ação\\'; DROP TABLE records; --\n", "O'Brien & x\t"]
    records = [
        {
            "id": "001",
            "name": value,
            "active": True,
            "amount": "12345678901234567890.123456789",
            "day": "2026-10-15",
            "happened": "2026-10-15T18:00:00",
        }
        for value in values
    ]
    sql, _ = convert(
        json.dumps(records).encode(),
        "json",
        "records",
        dialect=dialect,
        types={"amount": "decimal", "day": "date", "happened": "datetime"},
    )
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "CREATE TEMPORARY TABLE records (id VARCHAR(20), name TEXT, active BOOLEAN, amount DECIMAL(30,9), day DATE, happened TIMESTAMP)"
            )
            for statement in sql.getvalue().decode().splitlines():
                cursor.execute(statement)
            cursor.execute("SELECT id, name, active, amount, day, happened FROM records")
            rows = cursor.fetchall()
            assert len(rows) == len(values)
            for row, value in zip(rows, values, strict=True):
                assert tuple(row) == (
                    "001",
                    value,
                    True,
                    Decimal("12345678901234567890.123456789"),
                    date(2026, 10, 15),
                    datetime(2026, 10, 15, 18),
                )
    finally:
        connection.close()
