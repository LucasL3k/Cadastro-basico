"""Application factory and HTTP routes for the local customer directory."""

import json
import os
import sqlite3
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from flask import Flask, jsonify, render_template, request
from werkzeug.exceptions import HTTPException

from . import database
from .validation import validate_customer
from .supplier_routes import suppliers

ROOT = Path(__file__).resolve().parent.parent


def create_app(config=None):
    app = Flask(__name__, template_folder=str(ROOT / "templates"), static_folder=str(ROOT / "static"))
    app.config.update(
        DATABASE=os.environ.get("CADASTRO_DATABASE", str(ROOT / "dados" / "clientes.sqlite3")),
        MAX_CONTENT_LENGTH=64 * 1024,
        JSON_SORT_KEYS=False,
    )
    if config:
        app.config.update(config)
    database.init_app(app)
    app.register_blueprint(suppliers)

    @app.before_request
    def protect_local_writes():
        # JSON-only same-origin writes prevent other websites from changing local data.
        if request.method in {"POST", "PUT", "DELETE"}:
            if not request.is_json:
                return jsonify(message="Envie os dados no formato JSON."), 415
            if request.headers.get("Origin") not in {None, request.host_url.rstrip("/")}:
                return jsonify(message="Origem da solicitação não permitida."), 403

    @app.after_request
    def response_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "img-src 'self' data:; font-src 'self'; connect-src 'self'; "
            "frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        )
        if request.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/api/clientes")
    def list_customers():
        return jsonify(database.list_customers())

    @app.get("/api/clientes/<int:customer_id>")
    def get_customer(customer_id):
        customer = database.get_customer(customer_id)
        if customer is None:
            return jsonify(message="Este cliente não foi encontrado."), 404
        return jsonify(customer)

    def save_customer(customer_id=None):
        payload = request.get_json(silent=True)
        customer, errors, missing = validate_customer(payload)
        if errors:
            return jsonify(message="Revise os campos destacados antes de salvar.", errors=errors, missing=missing), 422
        if missing and payload.get("confirmar_incompleto") is not True:
            return jsonify(message="Confirme o cadastro com campos não preenchidos.", missing=missing, requires_confirmation=True), 409
        if customer_id is None:
            saved = database.create_customer(customer)
            return jsonify(saved), 201
        saved = database.update_customer(customer_id, customer)
        if saved is None:
            return jsonify(message="Este cliente não foi encontrado."), 404
        return jsonify(saved)

    @app.post("/api/clientes")
    def create_customer():
        return save_customer()

    @app.put("/api/clientes/<int:customer_id>")
    def update_customer(customer_id):
        return save_customer(customer_id)

    @app.delete("/api/clientes/<int:customer_id>")
    def delete_customer(customer_id):
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict) or payload.get("confirmar_exclusao") is not True:
            return jsonify(message="Confirme a exclusão do cliente."), 409
        if not database.delete_customer(customer_id):
            return jsonify(message="Este cliente não foi encontrado."), 404
        return "", 204

    @app.get("/api/cep/<cep>")
    def lookup_postcode(cep):
        if len(cep) != 8 or not cep.isascii() or not cep.isdigit():
            return jsonify(message="Informe um CEP com 8 números."), 422
        try:
            req = Request(f"https://viacep.com.br/ws/{cep}/json/", headers={"User-Agent": "CadastroClientes/1.0"})
            with urlopen(req, timeout=6) as response:
                address = json.load(response)
            if not isinstance(address, dict):
                raise ValueError("Invalid provider response")
            if address.get("erro"):
                return jsonify(message="CEP não encontrado. Confira o número ou preencha o endereço manualmente."), 404
            return jsonify(
                logradouro=address.get("logradouro", ""), bairro=address.get("bairro", ""),
                cidade=address.get("localidade", ""), uf=address.get("uf", ""),
            )
        except (HTTPError, URLError, TimeoutError, OSError, ValueError):
            return jsonify(message="A busca de CEP está indisponível. Você pode preencher o endereço manualmente."), 502

    @app.errorhandler(sqlite3.Error)
    def database_error(error):
        app.logger.exception("Erro de persistência no SQLite")
        return jsonify(message="Não foi possível concluir a operação no banco. Seus campos foram mantidos; tente novamente."), 503

    @app.errorhandler(HTTPException)
    def http_error(error):
        return jsonify(message={400: "Dados JSON inválidos.", 413: "O cadastro ultrapassa o tamanho permitido."}.get(error.code, error.description)), error.code

    return app
