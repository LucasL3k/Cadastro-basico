"""Validation shared by every customer write, including requests outside the UI."""

import re
import unicodedata

STATES = "AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO".split()
FIELDS = {
    "nome": ("Nome", 80), "sobrenome": ("Sobrenome", 120),
    "telefone": ("Telefone", 14), "email": ("E-mail", 254),
    "cep": ("CEP", 9), "logradouro": ("Rua / avenida", 180),
    "numero": ("Número", 20), "complemento": ("Complemento", 100),
    "bairro": ("Bairro", 100), "cidade": ("Cidade", 100),
    "uf": ("Estado", 2), "observacoes": ("Observações", 2000),
}
REQUIRED = tuple(field for field in FIELDS if field != "complemento")
EMAIL = re.compile(r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?)*\.[A-Za-z]{2,}$")
PHONE = re.compile(r"^\([1-9][0-9]\)[2-9][0-9]{3,4}-[0-9]{4}$")


def search_key(value):
    normalized = unicodedata.normalize("NFKD", value.casefold())
    return "".join(char for char in normalized if not unicodedata.combining(char))


def missing_fields(customer, required=REQUIRED):
    return [field for field in required if not customer.get(field)]


def validate_customer(payload):
    return validate_record(payload, FIELDS, name_fields=("nome", "sobrenome"))


def validate_record(payload, fields, name_fields=()):
    """Validate common contact/address fields without changing customer rules."""
    if not isinstance(payload, dict):
        return {}, {"geral": "Informe um objeto de cadastro válido."}, []
    customer, errors = {}, {}
    for field, (label, limit) in fields.items():
        value = payload.get(field, "")
        if not isinstance(value, str):
            errors[field] = f"{label}: informe um texto válido."
            value = ""
        value = value.strip()
        customer[field] = value
        if len(value) > limit:
            errors[field] = f"Use até {limit} caracteres."
        if any(unicodedata.category(char) == "Cc" and char not in "\n\r\t" for char in value):
            errors[field] = "Remova os caracteres de controle."
    customer["uf"] = customer["uf"].upper()
    for field in name_fields:
        value = customer[field]
        if value and (not any(c.isalpha() for c in value) or any(not (c.isalpha() or c in " '-.’") for c in value)):
            errors[field] = "Use letras, espaços, hífens ou apóstrofos."
    if customer["telefone"] and not PHONE.fullmatch(customer["telefone"]):
        errors["telefone"] = "Use (11)99999-9999 ou (11)3333-3333, com DDD válido."
    email = customer["email"]
    if email and (not EMAIL.fullmatch(email) or email.startswith(".") or ".." in email.split("@")[0] or ".@" in email):
        errors["email"] = "Informe um e-mail válido, como nome@exemplo.com."
    if customer["cep"] and not re.fullmatch(r"[0-9]{5}-[0-9]{3}", customer["cep"]):
        errors["cep"] = "Use o formato 00000-000."
    if customer["uf"] and customer["uf"] not in STATES:
        errors["uf"] = "Selecione um estado válido."
    if not any(customer.values()):
        errors["geral"] = "Preencha pelo menos um campo para criar o cadastro."
    required = tuple(field for field in fields if field != "complemento")
    return customer, errors, missing_fields(customer, required)
