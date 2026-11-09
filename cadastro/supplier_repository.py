"""Supplier storage in a separate table; never writes to customer records."""

from datetime import datetime, timezone

from .database import get_db
from .supplier_validation import FIELDS, REQUIRED
from .validation import missing_fields, search_key


def init_schema(db):
    columns = ", ".join(f"{field} TEXT NOT NULL DEFAULT ''" for field in FIELDS)
    db.execute(f"CREATE TABLE IF NOT EXISTS fornecedores (id INTEGER PRIMARY KEY AUTOINCREMENT, {columns}, criado_em TEXT NOT NULL, atualizado_em TEXT NOT NULL)")


def serialize(row):
    if row is None:
        return None
    supplier = dict(row)
    supplier["campos_pendentes"] = missing_fields(supplier, REQUIRED)
    supplier["completo"] = not supplier["campos_pendentes"]
    return supplier


def list_suppliers():
    records = [serialize(row) for row in get_db().execute("SELECT * FROM fornecedores")]
    return sorted(records, key=lambda record: (not bool(record["nome"]), search_key(record["nome"]), record["id"]))


def get_supplier(supplier_id):
    return serialize(get_db().execute("SELECT * FROM fornecedores WHERE id = ?", (supplier_id,)).fetchone())


def save_supplier(supplier, supplier_id=None):
    db = get_db()
    timestamp = datetime.now(timezone.utc).isoformat()
    values = [supplier[field] for field in FIELDS]
    with db:
        if supplier_id is None:
            columns = [*FIELDS, "criado_em", "atualizado_em"]
            cursor = db.execute(f"INSERT INTO fornecedores ({', '.join(columns)}) VALUES ({', '.join('?' for _ in columns)})", values + [timestamp, timestamp])
            supplier_id = cursor.lastrowid
        else:
            cursor = db.execute(f"UPDATE fornecedores SET {', '.join(f'{field} = ?' for field in FIELDS)}, atualizado_em = ? WHERE id = ?", values + [timestamp, supplier_id])
            if not cursor.rowcount:
                return None
    return get_supplier(supplier_id)


def delete_supplier(supplier_id):
    db = get_db()
    with db:
        cursor = db.execute("DELETE FROM fornecedores WHERE id = ?", (supplier_id,))
    return bool(cursor.rowcount)
