import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from cadastro import create_app
from tests.fixtures import complete_customer, complete_supplier


class SupplierTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = str(Path(self.temp.name) / "clientes.sqlite3")
        self.config = {"TESTING": True, "DATABASE": self.path}
        self.app = create_app(self.config)
        self.client = self.app.test_client()

    def tearDown(self):
        self.temp.cleanup()

    def create(self, **changes):
        response = self.client.post("/api/fornecedores", json=complete_supplier(**changes))
        self.assertEqual(response.status_code, 201, response.json)
        return response.json

    def test_additive_migration_preserves_legacy_customers_and_sequence(self):
        self.client.post("/api/clientes", json=complete_customer(observacoes="Preservar exatamente estes dados."))
        self.client.post("/api/clientes", json=complete_customer(nome="José"))
        with closing(sqlite3.connect(self.path)) as db:
            db.execute("DROP TABLE fornecedores")
            db.commit()
            schema = db.execute("SELECT sql FROM sqlite_master WHERE name='clientes'").fetchone()
            rows = db.execute("SELECT * FROM clientes ORDER BY id").fetchall()
            sequence = db.execute("SELECT seq FROM sqlite_sequence WHERE name='clientes'").fetchone()
        for _ in range(2):
            create_app(self.config)
        with closing(sqlite3.connect(self.path)) as db:
            self.assertEqual(db.execute("SELECT sql FROM sqlite_master WHERE name='clientes'").fetchone(), schema)
            self.assertEqual(db.execute("SELECT * FROM clientes ORDER BY id").fetchall(), rows)
            self.assertEqual(db.execute("SELECT seq FROM sqlite_sequence WHERE name='clientes'").fetchone(), sequence)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM fornecedores").fetchone()[0], 0)
            self.assertEqual(db.execute("PRAGMA integrity_check").fetchone()[0], "ok")

    def test_supplier_crud_is_isolated_from_same_id_customer(self):
        customer = self.client.post("/api/clientes", json=complete_customer()).json
        supplier = self.create()
        self.assertEqual(customer["id"], supplier["id"])
        url = f"/api/fornecedores/{supplier['id']}"
        self.assertEqual(self.client.get(url).json["cnpj"], "11.222.333/0001-81")
        changed = self.client.put(url, json=complete_supplier(nome="Aurora & Filhos", fornecimento="Papel e suprimentos."))
        self.assertEqual(changed.status_code, 200)
        self.assertEqual(changed.json["fornecimento"], "Papel e suprimentos.")
        self.assertEqual(changed.json["criado_em"], supplier["criado_em"])
        self.assertEqual(self.client.delete(url, json={"confirmar_exclusao": True}).status_code, 204)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.get(f"/api/clientes/{customer['id']}").json, customer)

    def test_real_and_fictitious_cnpj_values_can_be_saved(self):
        for cnpj in ("11.222.333/0001-81", "12.ABC.345/01DE-35", "00.000.000/E08G-12", "00.000.000/0000-00", "11.111.111/1111-11", "11.222.333/0001-80", "12.ABC.345/01DE-36"):
            with self.subTest(cnpj=cnpj):
                supplier = self.create(cnpj=cnpj.lower())
                self.assertEqual(supplier["cnpj"], cnpj)
                self.assertTrue(supplier["completo"])
                url = f"/api/fornecedores/{supplier['id']}"
                self.assertEqual(self.client.get(url).json["cnpj"], cnpj)
                updated = self.client.put(url, json=complete_supplier(cnpj="12.345.678/9012-34"))
                self.assertEqual(updated.status_code, 200)
                self.assertEqual(updated.json["cnpj"], "12.345.678/9012-34")

    def test_malformed_cnpj_is_not_bypassed_by_confirmation(self):
        for cnpj in ("11222333000181", "ab", "12.ABC.345/01DE-AA", "12.345.678/9012-3"):
            with self.subTest(cnpj=cnpj):
                response = self.client.post("/api/fornecedores", json=complete_supplier(cnpj=cnpj, confirmar_incompleto=True))
                self.assertEqual(response.status_code, 422)
                self.assertIn("cnpj", response.json["errors"])
        self.assertEqual(self.client.get("/api/fornecedores").json, [])

    def test_incomplete_and_delete_require_confirmation(self):
        response = self.client.post("/api/fornecedores", json={"nome": "Empresa"})
        self.assertEqual(response.status_code, 409)
        self.assertIn("cnpj", response.json["missing"])
        self.assertIn("fornecimento", response.json["missing"])
        supplier = self.client.post("/api/fornecedores", json={"nome": "Empresa", "confirmar_incompleto": True}).json
        self.assertFalse(supplier["completo"])
        url = f"/api/fornecedores/{supplier['id']}"
        self.assertEqual(self.client.put(url, json={"nome": "Outra empresa"}).status_code, 409)
        self.assertEqual(self.client.delete(url, json={}).status_code, 409)
        self.assertEqual(self.client.get(url).json["nome"], "Empresa")
        self.assertEqual(self.client.post("/api/fornecedores", json={"confirmar_incompleto": True}).status_code, 422)

    def test_validation_covers_contacts_and_supply(self):
        for changes in ({"email": "empresa@"}, {"telefone": "123"}, {"cep": "123"}, {"uf": "ZZ"}, {"fornecimento": "x" * 2001}, {"nome": 123}):
            with self.subTest(changes=str(changes)[:40]):
                response = self.client.post("/api/fornecedores", json=complete_supplier(**changes))
                self.assertEqual(response.status_code, 422)
        saved = self.create()
        response = self.client.put(f"/api/fornecedores/{saved['id']}", json=complete_supplier(cnpj="inválido"))
        self.assertEqual(response.status_code, 422)
        self.assertEqual(self.client.get(f"/api/fornecedores/{saved['id']}").json, saved)

    def test_persistence_alphabetical_sort_and_safe_text(self):
        self.create(nome="Zeta")
        self.create(nome="Ágata & Cia.", fornecimento="<script>alert('x')</script>'); DROP TABLE clientes; --")
        restarted = create_app(self.config).test_client()
        suppliers = restarted.get("/api/fornecedores").json
        self.assertEqual([record["nome"] for record in suppliers], ["Ágata & Cia.", "Zeta"])
        self.assertIn("<script>", suppliers[0]["fornecimento"])
        self.assertEqual(restarted.get("/api/clientes").status_code, 200)

    def test_missing_supplier_and_invalid_payload(self):
        for payload in ([], "invalid", 123):
            self.assertEqual(self.client.post("/api/fornecedores", json=payload).status_code, 422)
        self.assertEqual(self.client.get("/api/fornecedores/999").status_code, 404)
        self.assertEqual(self.client.put("/api/fornecedores/999", json=complete_supplier()).status_code, 404)
        self.assertEqual(self.client.delete("/api/fornecedores/999", json={"confirmar_exclusao": True}).status_code, 404)


if __name__ == "__main__":
    unittest.main()
