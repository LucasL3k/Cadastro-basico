"""Real Chromium E2E tests; all customer data lives in a temporary SQLite file."""

import logging
import tempfile
import threading
import unittest
from pathlib import Path

from playwright.sync_api import expect, sync_playwright
from werkzeug.serving import make_server

from cadastro import create_app
from tests.fixtures import complete_customer, complete_supplier


class BrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.app = create_app({"TESTING": True, "DATABASE": str(Path(cls.temp.name) / "browser.sqlite3")})
        cls.server = make_server("127.0.0.1", 0, cls.app, threaded=True)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        logging.getLogger("werkzeug").setLevel(logging.ERROR)
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch()
        cls.results = Path(__file__).resolve().parent.parent / "test-results"
        cls.results.mkdir(exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()
        cls.server.shutdown()
        cls.thread.join()
        cls.temp.cleanup()

    def setUp(self):
        with self.app.test_client() as client:
            for customer in client.get("/api/clientes").json:
                client.delete(f"/api/clientes/{customer['id']}", json={"confirmar_exclusao": True})
            for supplier in client.get("/api/fornecedores").json:
                client.delete(f"/api/fornecedores/{supplier['id']}", json={"confirmar_exclusao": True})
        self.context = self.browser.new_context(viewport={"width": 1440, "height": 1000}, locale="pt-BR")
        self.page = self.context.new_page()
        self.errors = []
        self.page.on("pageerror", lambda error: self.errors.append(str(error)))
        self.page.goto(self.base)
        expect(self.page.locator("#results-label")).to_have_text("0 clientes")

    def tearDown(self):
        self.context.close()
        self.assertEqual(self.errors, [], "Browser JavaScript errors")

    def seed(self, **changes):
        with self.app.test_client() as client:
            response = client.post("/api/clientes", json=complete_customer(**changes))
            self.assertEqual(response.status_code, 201)
            return response.json

    def fill_form(self, **changes):
        for key, value in complete_customer(**changes).items():
            locator = self.page.locator(f"#field-{key}")
            if key == "uf":
                locator.select_option(value)
            else:
                locator.fill(value)

    def test_empty_state_and_complete_create_edit_view_delete(self):
        page = self.page
        expect(page.get_by_text("Sua lista começa com uma conexão")).to_be_visible()
        page.screenshot(path=str(self.results / "desktop-vazio.png"), full_page=True)
        page.locator('[data-action="new"]').first.click()
        self.fill_form()
        page.screenshot(path=str(self.results / "formulario.png"), full_page=True)
        page.locator("#save-customer").click()
        expect(page.locator("#editor")).not_to_be_visible()
        expect(page.locator("#customer-rows tr")).to_have_count(1)
        page.reload()
        expect(page.get_by_role("button", name="Ana Oliveira", exact=True)).to_be_visible()
        page.get_by_role("button", name="Visualizar Ana Oliveira em tela cheia").click()
        expect(page.locator("#detail-title")).to_have_text("Ana Oliveira")
        expect(page.locator("#details")).to_have_css("width", "1440px")
        page.screenshot(path=str(self.results / "visualizacao.png"), full_page=True)
        page.get_by_role("button", name="Editar cadastro", exact=True).click()
        page.locator("#field-nome").fill("Beatriz")
        page.locator("#save-customer").click()
        expect(page.get_by_role("button", name="Beatriz Oliveira", exact=True)).to_be_visible()
        page.get_by_role("button", name="Excluir Beatriz Oliveira", exact=True).click()
        expect(page.locator("#confirmation")).to_be_visible()
        page.locator("#confirm-cancel").click()
        expect(page.locator("#customer-rows tr")).to_have_count(1)
        page.get_by_role("button", name="Excluir Beatriz Oliveira", exact=True).click()
        page.locator("#confirm-accept").click()
        expect(page.locator("#customer-rows tr")).to_have_count(0)

    def test_incomplete_and_invalid_forms(self):
        page = self.page
        page.locator('[data-action="new"]').first.click()
        page.locator("#field-nome").fill("Carlos")
        page.locator("#field-email").fill("invalido@")
        page.locator("#save-customer").click()
        expect(page.locator("#confirmation")).not_to_be_visible()
        expect(page.locator("#field-email")).to_have_attribute("aria-invalid", "true")
        expect(page.locator("#field-sobrenome")).to_have_attribute("aria-invalid", "true")
        page.locator("#field-email").fill("")
        page.locator("#save-customer").click()
        expect(page.locator("#confirm-title")).to_have_text("Salvar com campos pendentes?")
        page.locator("#confirm-cancel").click()
        expect(page.locator("#field-nome")).to_have_value("Carlos")
        page.locator("#save-customer").click()
        page.locator("#confirm-accept").click()
        expect(page.locator("#customer-rows tr")).to_have_count(1)
        expect(page.locator(".status-badge")).to_have_text("Pendente")
        page.get_by_role("button", name="Editar Carlos", exact=True).click()
        expect(page.locator("#field-email")).to_have_attribute("aria-invalid", "true")
        page.keyboard.press("Escape")
        expect(page.locator("#editor")).not_to_be_visible()

    def test_search_filters_sort_and_reset(self):
        page = self.page
        self.seed(nome="Zélia", sobrenome="Costa", email="zelia@exemplo.com", cidade="Curitiba", uf="PR")
        self.seed(nome="Álvaro", sobrenome="Mendes", email="alvaro@exemplo.com")
        self.seed(nome="Beatriz", sobrenome="Lima", email="bia@exemplo.com", telefone="", confirmar_incompleto=True)
        page.reload()
        expect(page.locator(".customer-name")).to_have_text(["Álvaro Mendes", "Beatriz Lima", "Zélia Costa"])
        page.screenshot(path=str(self.results / "desktop-clientes.png"), full_page=True)
        for query, result in [("alvaro", "Álvaro Mendes"), ("COSTA", "Zélia Costa"), ("bia@exemplo", "Beatriz Lima")]:
            page.locator("#search").fill(query)
            expect(page.locator(".customer-name")).to_have_text([result])
        page.locator("#search").fill("nadaencontrado")
        expect(page.get_by_text("Nenhum cliente encontrado")).to_be_visible()
        page.get_by_role("button", name="Limpar busca e filtros").click()
        page.locator("#filter-toggle").click()
        page.locator("#filter-city").select_option("Curitiba")
        expect(page.locator(".customer-name")).to_have_text(["Zélia Costa"])
        page.locator("#filter-state").select_option("SP")
        expect(page.get_by_text("Nenhum cliente encontrado")).to_be_visible()
        page.locator("#clear-filters").click()
        page.locator('[data-status="pending"]').click()
        expect(page.locator(".customer-name")).to_have_text(["Beatriz Lima"])
        page.locator('[data-status="complete"]').click()
        expect(page.locator(".customer-name")).to_have_text(["Álvaro Mendes", "Zélia Costa"])

    def test_cep_lookup_masks_and_failure_manual_entry(self):
        page = self.page
        page.route("**/api/cep/01001000", lambda route: route.fulfill(json={"logradouro": "Praça da Sé", "bairro": "Sé", "cidade": "São Paulo", "uf": "SP"}))
        page.locator('[data-action="new"]').first.click()
        page.locator("#field-telefone").fill("11999991234")
        expect(page.locator("#field-telefone")).to_have_value("(11)99999-1234")
        page.locator("#field-cep").fill("01001000")
        expect(page.locator("#field-cep")).to_have_value("01001-000")
        page.locator("#lookup-cep").click()
        expect(page.locator("#field-logradouro")).to_have_value("Praça da Sé")
        expect(page.locator("#field-cidade")).to_have_value("São Paulo")
        expect(page.locator("#field-uf")).to_have_value("SP")
        page.route("**/api/cep/99999999", lambda route: route.fulfill(status=404, json={"message": "CEP não encontrado. Preencha manualmente."}))
        page.locator("#field-cep").fill("99999999")
        page.locator("#lookup-cep").click()
        expect(page.locator("#cep-status")).to_contain_text("CEP não encontrado")
        page.locator("#field-logradouro").fill("Rua manual")
        expect(page.locator("#field-logradouro")).to_have_value("Rua manual")

    def test_save_failure_keeps_form_and_values(self):
        page = self.page
        page.route("**/api/clientes", lambda route: route.fulfill(status=503, json={"message": "Não foi possível salvar agora."}) if route.request.method == "POST" else route.continue_())
        page.locator('[data-action="new"]').first.click()
        self.fill_form()
        page.locator("#save-customer").click()
        expect(page.locator("#form-error")).to_have_text("Não foi possível salvar agora.")
        expect(page.locator("#field-nome")).to_have_value("Ana")
        expect(page.locator("#save-customer")).to_be_enabled()
        expect(page.locator("#editor")).to_be_visible()

    def test_notes_are_rendered_without_html_execution(self):
        self.seed(observacoes='<img src=x onerror="window.xss=true">')
        self.page.reload()
        self.page.get_by_role("button", name="Visualizar Ana Oliveira em tela cheia").click()
        expect(self.page.locator(".notes-text")).to_have_text('<img src=x onerror="window.xss=true">')
        self.assertIsNone(self.page.evaluate("window.xss"))

    def test_mobile_table_form_and_details_fit_viewport(self):
        page = self.page
        self.seed(nome="Ana", sobrenome="Oliveira")
        self.seed(nome="Bruno", sobrenome="Almeida", email="bruno@exemplo.com")
        page.set_viewport_size({"width": 390, "height": 844})
        page.reload()
        expect(page.locator("#customer-rows tr")).to_have_count(2)
        self.assertLessEqual(page.evaluate("document.documentElement.scrollWidth"), 390)
        page.screenshot(path=str(self.results / "celular-clientes.png"), full_page=True)
        page.get_by_role("button", name="Editar Ana Oliveira", exact=True).click()
        expect(page.locator("#field-nome")).to_be_visible()
        self.assertLessEqual(page.locator("#editor").evaluate("el => el.scrollWidth"), 390)
        page.locator("#field-nome").fill("Amanda")
        page.locator("#save-customer").click()
        expect(page.get_by_role("button", name="Amanda Oliveira", exact=True)).to_be_visible()
        page.get_by_role("button", name="Visualizar Amanda Oliveira em tela cheia").click()
        self.assertLessEqual(page.locator("#details").evaluate("el => el.scrollWidth"), 390)
        page.screenshot(path=str(self.results / "celular-visualizacao.png"), full_page=True)
        page.get_by_role("button", name="Voltar para clientes").click()
        expect(page.locator("#details")).not_to_be_visible()

    def test_narrow_and_tablet_layouts(self):
        self.seed()
        page = self.page
        for width in (320, 768, 1024):
            with self.subTest(width=width):
                page.set_viewport_size({"width": width, "height": 900})
                page.reload()
                expect(page.locator("#customer-rows tr")).to_have_count(1)
                self.assertLessEqual(page.evaluate("document.documentElement.scrollWidth"), width)
                icon_box = page.locator(".search-box > [data-icon]").bounding_box()
                input_box = page.locator("#search").bounding_box()
                self.assertGreater(icon_box["x"], input_box["x"])
                page.locator('[data-action="new"]').first.click()
                self.assertLessEqual(page.locator("#editor").evaluate("el => el.scrollWidth"), width)
                page.keyboard.press("Escape")

    def test_delete_from_details_failure_and_confirmation(self):
        self.seed()
        page = self.page
        page.reload()
        page.get_by_role("button", name="Visualizar Ana Oliveira em tela cheia").click()
        page.route("**/api/clientes/*", lambda route: route.fulfill(status=503, json={"message": "Falha ao excluir; tente novamente."}) if route.request.method == "DELETE" else route.continue_())
        page.get_by_role("button", name="Excluir", exact=True).click()
        page.keyboard.press("Escape")
        expect(page.locator("#confirmation")).not_to_be_visible()
        page.get_by_role("button", name="Excluir", exact=True).click()
        page.locator("#confirm-accept").click()
        expect(page.locator("#details .toast")).to_contain_text("Falha ao excluir")
        expect(page.locator("#details")).to_be_visible()
        page.unroute("**/api/clientes/*")
        page.get_by_role("button", name="Excluir", exact=True).click()
        page.locator("#confirm-accept").click()
        expect(page.locator("#details")).not_to_be_visible()
        expect(page.locator("#customer-rows tr")).to_have_count(0)

    def test_red_brand_and_floating_create_on_desktop_and_mobile(self):
        page = self.page
        expect(page).to_have_title("Vermelho · Clientes")
        expect(page.locator(".brand")).to_contain_text("Vermelho")
        expect(page.locator(".page-footer")).to_contain_text("Cadastro de clientes e empresas")
        expect(page.locator(".page-footer")).to_contain_text("Busque de forma rápida seus contatos")
        self.assertNotIn("azul", page.locator("body").inner_text().lower())
        for _ in range(12):
            self.seed()
        for width in (1440, 768, 390, 320):
            with self.subTest(width=width):
                page.set_viewport_size({"width": width, "height": 900})
                page.reload()
                expect(page.locator("#customer-rows tr")).to_have_count(12)
                button = page.locator("#new-record")
                expect(button).to_have_css("position", "fixed")
                color = button.evaluate("el => getComputedStyle(el).backgroundColor")
                rgb = [int(part) for part in color.removeprefix("rgb(").removesuffix(")").split(",")]
                self.assertGreater(rgb[0], rgb[1] + 60)
                self.assertGreater(rgb[0], rgb[2] + 60)
                before = button.bounding_box()
                self.assertLessEqual(width - before["x"] - before["width"], 32)
                self.assertLessEqual(900 - before["y"] - before["height"], 32)
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                after = button.bounding_box()
                self.assertAlmostEqual(before["y"], after["y"], delta=1)
                self.assertLessEqual(page.evaluate("document.documentElement.scrollWidth"), width)
                button.click()
                expect(page.locator("#editor")).to_be_visible()
                expect(button).not_to_be_visible()
                page.keyboard.press("Escape")
                expect(button).to_be_visible()
                page.evaluate("window.scrollTo(0, 0)")
                if width in (1440, 390):
                    page.screenshot(path=str(self.results / f"vermelho-flutuante-{width}.png"))

    def test_supplier_create_edit_search_and_delete_preserves_customer(self):
        page = self.page
        existing = self.seed()
        page.reload()
        page.locator('[data-directory="fornecedores"]').click()
        expect(page.locator("#results-label")).to_have_text("0 fornecedores")
        page.locator("#new-record").click()
        for key, value in complete_supplier().items():
            if key == "uf": page.locator(f"#field-{key}").select_option(value)
            else: page.locator(f"#field-{key}").fill(value)
        page.screenshot(path=str(self.results / "vermelho-formulario-fornecedor.png"), full_page=True)
        page.locator("#save-customer").click()
        expect(page.locator(".customer-name")).to_have_text(["Aurora Materiais Ltda."])
        page.reload()
        expect(page.locator("#page-title")).to_have_text("Seus fornecedores.")
        for query in ("Aurora", "11222333000181", "embalagens", "contato@aurora"):
            page.locator("#search").fill(query)
            expect(page.locator(".customer-name")).to_have_text(["Aurora Materiais Ltda."])
        page.locator("#search").fill("")
        page.screenshot(path=str(self.results / "vermelho-fornecedores.png"), full_page=True)
        page.get_by_role("button", name="Visualizar Aurora Materiais Ltda. em tela cheia").click()
        expect(page.locator(".notes-text")).to_have_text("Materiais de escritório e embalagens.")
        expect(page.locator("#details")).to_contain_text("11.222.333/0001-81")
        page.get_by_role("button", name="Editar cadastro", exact=True).click()
        page.locator("#field-nome").fill("Aurora & Filhos")
        page.locator("#field-fornecimento").fill("Papel e suprimentos.")
        page.locator("#save-customer").click()
        expect(page.locator(".customer-name")).to_have_text(["Aurora & Filhos"])
        page.get_by_role("button", name="Excluir Aurora & Filhos", exact=True).click()
        expect(page.locator("#confirm-title")).to_have_text("Excluir este fornecedor?")
        page.locator("#confirm-cancel").click()
        expect(page.locator("#customer-rows tr")).to_have_count(1)
        page.get_by_role("button", name="Excluir Aurora & Filhos", exact=True).click()
        page.locator("#confirm-accept").click()
        expect(page.locator("#customer-rows tr")).to_have_count(0)
        page.locator('[data-directory="clientes"]').click()
        expect(page.locator(".customer-name")).to_have_text(["Ana Oliveira"])
        with self.app.test_client() as client:
            self.assertEqual(client.get(f"/api/clientes/{existing['id']}").json, existing)

    def test_supplier_cnpj_validation_incomplete_confirmation_and_mobile(self):
        page = self.page
        page.set_viewport_size({"width": 390, "height": 844})
        page.locator('[data-directory="fornecedores"]').click()
        expect(page.locator("#results-label")).to_have_text("0 fornecedores")
        page.locator("#new-record").click()
        page.locator("#field-nome").fill("Oficina Exemplo")
        page.locator("#field-cnpj").fill("123")
        expect(page.locator("#field-cnpj")).to_have_value("12.3")
        page.locator("#save-customer").click()
        expect(page.locator("#field-cnpj")).to_have_attribute("aria-invalid", "true")
        expect(page.locator("#confirmation")).not_to_be_visible()
        page.locator("#field-cnpj").fill("12345678901234")
        expect(page.locator("#field-cnpj")).to_have_value("12.345.678/9012-34")
        page.locator("#save-customer").click()
        expect(page.locator(".confirm-missing")).to_contain_text("O que a empresa fornece")
        page.locator("#confirm-accept").click()
        expect(page.locator("#customer-rows tr")).to_have_count(1)
        expect(page.locator(".status-badge")).to_have_text("Pendente")
        page.reload()
        expect(page.locator(".customer-id")).to_have_text("12.345.678/9012-34")
        page.get_by_role("button", name="Editar Oficina Exemplo", exact=True).click()
        page.locator("#field-cnpj").fill("00000000000000")
        page.locator("#save-customer").click()
        page.locator("#confirm-accept").click()
        expect(page.locator(".customer-id")).to_have_text("00.000.000/0000-00")
        self.assertLessEqual(page.evaluate("document.documentElement.scrollWidth"), 390)
        page.screenshot(path=str(self.results / "vermelho-fornecedores-celular.png"), full_page=True)

    def test_switching_tabs_does_not_mix_records_or_filters(self):
        self.seed()
        with self.app.test_client() as client:
            client.post("/api/fornecedores", json=complete_supplier())
        page = self.page
        page.reload()
        page.locator("#search").fill("Ana")
        page.locator('[data-directory="fornecedores"]').click()
        expect(page.locator("#search")).to_have_value("")
        expect(page.locator(".customer-name")).to_have_text(["Aurora Materiais Ltda."])
        page.locator('[data-directory="clientes"]').click()
        expect(page.locator(".customer-name")).to_have_text(["Ana Oliveira"])
        page.go_back()
        expect(page.locator(".customer-name")).to_have_text(["Aurora Materiais Ltda."])
        expect(page.locator('[data-directory="fornecedores"]')).to_have_attribute("aria-current", "page")


if __name__ == "__main__":
    unittest.main()
