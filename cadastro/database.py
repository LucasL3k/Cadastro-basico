"""SQLite storage: parameterized statements and committed atomic transactions."""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from flask import current_app, g

from .validation import FIELDS, missing_fields, search_key


def get_db():
    if "db" not in g:
        db = sqlite3.connect(current_app.config["DATABASE"], timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA busy_timeout = 10000")
        db.execute("PRAGMA synchronous = FULL")
        g.db = db
    return g.db


def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_app(app):
    from .supplier_repository import init_schema as init_suppliers

    database_path = Path(app.config["DATABASE"])
    database_path.parent.mkdir(parents=True, exist_ok=True)
    app.teardown_appcontext(close_db)
    with app.app_context():
        db = get_db()
        # DELETE journaling leaves one portable .sqlite3 file after each transaction.
        db.execute("PRAGMA journal_mode = DELETE")
        columns = ", ".join(f"{field} TEXT NOT NULL DEFAULT ''" for field in FIELDS)
        with db:
            db.execute(f"CREATE TABLE IF NOT EXISTS clientes (id INTEGER PRIMARY KEY AUTOINCREMENT, {columns}, criado_em TEXT NOT NULL, atualizado_em TEXT NOT NULL)")
            init_suppliers(db)


def serialize(row):
    if row is None:
        return None
    customer = dict(row)
    customer["campos_pendentes"] = missing_fields(customer)
    customer["completo"] = not customer["campos_pendentes"]
    return customer


def list_customers():
    customers = [serialize(row) for row in get_db().execute("SELECT * FROM clientes")]
    return sorted(customers, key=lambda c: (not bool(c["nome"]), search_key(c["nome"]), search_key(c["sobrenome"]), c["id"]))


def get_customer(customer_id):
    return serialize(get_db().execute("SELECT * FROM clientes WHERE id = ?", (customer_id,)).fetchone())


def create_customer(customer):
    db = get_db()
    timestamp = datetime.now(timezone.utc).isoformat()
    columns = [*FIELDS, "criado_em", "atualizado_em"]
    values = [customer[field] for field in FIELDS] + [timestamp, timestamp]
    with db:
        cursor = db.execute(f"INSERT INTO clientes ({', '.join(columns)}) VALUES ({', '.join('?' for _ in columns)})", values)
    return get_customer(cursor.lastrowid)


def update_customer(customer_id, customer):
    db = get_db()
    values = [customer[field] for field in FIELDS] + [datetime.now(timezone.utc).isoformat(), customer_id]
    with db:
        cursor = db.execute(f"UPDATE clientes SET {', '.join(f'{field} = ?' for field in FIELDS)}, atualizado_em = ? WHERE id = ?", values)
    return get_customer(customer_id) if cursor.rowcount else None


def delete_customer(customer_id):
    db = get_db()
    with db:
        cursor = db.execute("DELETE FROM clientes WHERE id = ?", (customer_id,))
    return bool(cursor.rowcount)
