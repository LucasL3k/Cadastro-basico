"""Company fields and CNPJ format validation, including fictitious values."""

import re

from .validation import FIELDS as CUSTOMER_FIELDS, validate_record

FIELDS = {
    "nome": ("Empresa / razão social", 160),
    "cnpj": ("CNPJ", 18),
    **{key: value for key, value in CUSTOMER_FIELDS.items()
       if key not in {"nome", "sobrenome", "observacoes"}},
    "fornecimento": ("O que a empresa fornece", 2000),
}
REQUIRED = tuple(key for key in FIELDS if key != "complemento")


def valid_cnpj_format(value):
    """Keep the mask/length contract without checking authenticity or checksum."""
    return bool(re.fullmatch(r"[A-Z0-9]{2}\.[A-Z0-9]{3}\.[A-Z0-9]{3}/[A-Z0-9]{4}-[0-9]{2}", value))


def validate_supplier(payload):
    supplier, errors, missing = validate_record(payload, FIELDS)
    if not supplier:
        return supplier, errors, missing
    supplier["cnpj"] = supplier["cnpj"].upper()
    if supplier["cnpj"] and not valid_cnpj_format(supplier["cnpj"]):
        errors["cnpj"] = "Preencha o CNPJ no formato 00.000.000/0000-00. Números fictícios são aceitos."
    return supplier, errors, missing
