"""HTTP routes for the supplier directory."""

from flask import Blueprint, jsonify, request

from . import supplier_repository as repository
from .supplier_validation import validate_supplier

suppliers = Blueprint("suppliers", __name__, url_prefix="/api/fornecedores")


@suppliers.get("")
def list_suppliers():
    return jsonify(repository.list_suppliers())


@suppliers.get("/<int:supplier_id>")
def get_supplier(supplier_id):
    supplier = repository.get_supplier(supplier_id)
    if supplier is None:
        return jsonify(message="Este fornecedor não foi encontrado."), 404
    return jsonify(supplier)


@suppliers.post("")
@suppliers.put("/<int:supplier_id>")
def save_supplier(supplier_id=None):
    payload = request.get_json(silent=True)
    supplier, errors, missing = validate_supplier(payload)
    if errors:
        return jsonify(message="Revise os campos destacados antes de salvar.", errors=errors, missing=missing), 422
    if missing and payload.get("confirmar_incompleto") is not True:
        return jsonify(message="Confirme o cadastro com campos não preenchidos.", missing=missing, requires_confirmation=True), 409
    saved = repository.save_supplier(supplier, supplier_id)
    if saved is None:
        return jsonify(message="Este fornecedor não foi encontrado."), 404
    return jsonify(saved), 201 if supplier_id is None else 200


@suppliers.delete("/<int:supplier_id>")
def delete_supplier(supplier_id):
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or payload.get("confirmar_exclusao") is not True:
        return jsonify(message="Confirme a exclusão do fornecedor."), 409
    if not repository.delete_supplier(supplier_id):
        return jsonify(message="Este fornecedor não foi encontrado."), 404
    return "", 204
