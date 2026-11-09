import io
import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError

from cadastro import create_app
from tests.fixtures import complete_customer


class CustomerApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.temp.name) / "clientes.sqlite3")
        self.app = create_app({"TESTING": True, "DATABASE": self.db_path})
        self.client = self.app.test_client()

    def tearDown(self):
        self.temp.cleanup()

    def create(self, **changes):
        response = self.client.post("/api/clientes", json=complete_customer(**changes))
        self.assertEqual(response.status_code, 201, response.json)
        return response.json

    def test_initial_page_and_empty_database(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'lang="pt-BR"', response.data)
        self.assertIn("default-src 'self'", response.headers["Content-Security-Policy"])
        self.assertEqual(self.client.get("/api/clientes").json, [])

    def test_create_read_update_and_delete(self):
        customer = self.create()
        url = f"/api/clientes/{customer['id']}"
        self.assertEqual(self.client.get(url).json["nome"], "Ana")
        updated = self.client.put(url, json=complete_customer(nome="Maria", observacoes="Nova observação"))
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json["observacoes"], "Nova observação")
        self.assertEqual(updated.json["criado_em"], customer["criado_em"])
        self.assertNotEqual(updated.json["atualizado_em"], customer["atualizado_em"])
        self.assertEqual(self.client.delete(url, json={"confirmar_exclusao": True}).status_code, 204)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.get("/api/clientes").json, [])

    def test_delete_requires_explicit_confirmation(self):
        customer = self.create()
        for payload in ({}, {"confirmar_exclusao": "true"}, {"confirmar_exclusao": False}, []):
            self.assertEqual(self.client.delete(f"/api/clientes/{customer['id']}", json=payload).status_code, 409)
        self.assertEqual(len(self.client.get("/api/clientes").json), 1)

    def test_incomplete_requires_confirmation_for_create_and_update(self):
        response = self.client.post("/api/clientes", json={"nome": "Ana"})
        self.assertEqual(response.status_code, 409)
        self.assertIn("email", response.json["missing"])
        self.assertEqual(self.client.get("/api/clientes").json, [])
        created = self.client.post("/api/clientes", json={"nome": "Ana", "confirmar_incompleto": True})
        self.assertEqual(created.status_code, 201)
        self.assertFalse(created.json["completo"])
        url = f"/api/clientes/{created.json['id']}"
        self.assertEqual(self.client.put(url, json={"nome": "Maria"}).status_code, 409)
        self.assertEqual(self.client.get(url).json["nome"], "Ana")

    def test_empty_record_cannot_be_saved_even_with_confirmation(self):
        self.assertEqual(self.client.post("/api/clientes", json={"confirmar_incompleto": True}).status_code, 422)

    def test_invalid_formats_never_bypass_validation(self):
        for field, value in [("email", "ana@exemplo"), ("email", ".ana@exemplo.com"), ("email", "ana..b@exemplo.com"), ("email", "ana@-exemplo.com"), ("telefone", "11999991234"), ("telefone", "(00)99999-9999"), ("cep", "123"), ("uf", "ZZ"), ("nome", "Ana123"), ("sobrenome", "<script>"), ("observacoes", "x" * 2001), ("cidade", 123)]:
            with self.subTest(field=field, value=str(value)[:30]):
                response = self.client.post("/api/clientes", json=complete_customer(**{field: value}, confirmar_incompleto=True))
                self.assertEqual(response.status_code, 422)
                self.assertIn(field, response.json["errors"])
        self.assertEqual(self.client.get("/api/clientes").json, [])

    def test_valid_landline_and_unicode_names(self):
        customer = self.create(nome="João", sobrenome="D’Ávila-Santos", telefone="(21)3333-4444", email="joao+contato@empresa.com.br")
        self.assertTrue(customer["completo"])

    def test_alphabetical_sort_ignores_accents_and_case(self):
        for name, surname in [("zélia", "Alves"), ("Ana", "Zanon"), ("Álvaro", "Silva"), ("ana", "Abreu")]:
            self.create(nome=name, sobrenome=surname)
        result = self.client.get("/api/clientes").json
        self.assertEqual([(c["nome"], c["sobrenome"]) for c in result], [("Álvaro", "Silva"), ("ana", "Abreu"), ("Ana", "Zanon"), ("zélia", "Alves")])

    def test_persists_across_app_restart_and_file_is_sqlite(self):
        customer = self.create()
        restarted = create_app({"TESTING": True, "DATABASE": self.db_path}).test_client()
        self.assertEqual(restarted.get(f"/api/clientes/{customer['id']}").json, customer)
        self.assertEqual(Path(self.db_path).read_bytes()[:16], b"SQLite format 3\x00")
        with closing(sqlite3.connect(self.db_path)) as connection:
            self.assertEqual(connection.execute("PRAGMA integrity_check").fetchone()[0], "ok")

    def test_concurrent_writes_commit_all_records(self):
        def write_one(_):
            with self.app.test_client() as client:
                return client.post("/api/clientes", json=complete_customer()).status_code
        with ThreadPoolExecutor(max_workers=4) as executor:
            self.assertEqual(list(executor.map(write_one, range(12))), [201] * 12)
        self.assertEqual(len(self.client.get("/api/clientes").json), 12)

    def test_database_error_returns_failure_without_success_message(self):
        with patch("cadastro.database.create_customer", side_effect=sqlite3.OperationalError("disk full")), self.assertLogs(self.app.logger, level="ERROR"):
            response = self.client.post("/api/clientes", json=complete_customer())
        self.assertEqual(response.status_code, 503)
        self.assertEqual(self.client.get("/api/clientes").json, [])

    def test_observations_are_stored_as_text_and_sql_is_parameterized(self):
        text = "<script>alert('x')</script>'); DROP TABLE clientes; --"
        customer = self.create(observacoes=text)
        self.assertEqual(customer["observacoes"], text)
        self.assertEqual(len(self.client.get("/api/clientes").json), 1)

    def test_missing_customers(self):
        self.assertEqual(self.client.get("/api/clientes/123").status_code, 404)
        self.assertEqual(self.client.put("/api/clientes/123", json=complete_customer()).status_code, 404)
        self.assertEqual(self.client.delete("/api/clientes/123", json={"confirmar_exclusao": True}).status_code, 404)

    def test_json_and_same_origin_are_enforced(self):
        self.assertEqual(self.client.post("/api/clientes", data={"nome": "Ana"}).status_code, 415)
        self.assertEqual(self.client.post("/api/clientes", json=complete_customer(), headers={"Origin": "https://other.example"}).status_code, 403)
        for payload in ([], "invalid", 15, None):
            response = self.client.post("/api/clientes", data=json.dumps(payload), content_type="application/json")
            self.assertEqual(response.status_code, 422)
        self.assertEqual(self.client.post("/api/clientes", data="{", content_type="application/json").status_code, 422)

    def test_cep_success(self):
        data = {"logradouro": "Praça da Sé", "bairro": "Sé", "localidade": "São Paulo", "uf": "SP"}
        with patch("cadastro.urlopen", return_value=io.BytesIO(json.dumps(data).encode())):
            response = self.client.get("/api/cep/01001000")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["cidade"], "São Paulo")

    def test_cep_unknown_malformed_and_offline(self):
        self.assertEqual(self.client.get("/api/cep/123").status_code, 422)
        with patch("cadastro.urlopen", return_value=io.BytesIO(b'{"erro": true}')):
            self.assertEqual(self.client.get("/api/cep/99999999").status_code, 404)
        with patch("cadastro.urlopen", side_effect=URLError("offline")):
            self.assertEqual(self.client.get("/api/cep/01001000").status_code, 502)


if __name__ == "__main__":
    unittest.main()
