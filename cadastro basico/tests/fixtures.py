def complete_customer(**changes):
    customer = {
        "nome": "Ana", "sobrenome": "Oliveira", "telefone": "(11)99999-1234",
        "email": "ana@exemplo.com", "cep": "01001-000", "logradouro": "Praça da Sé",
        "numero": "100", "complemento": "", "bairro": "Sé", "cidade": "São Paulo",
        "uf": "SP", "observacoes": "Contato preferencial por e-mail.",
    }
    return customer | changes


def complete_supplier(**changes):
    supplier = {
        key: value for key, value in complete_customer().items()
        if key not in {"nome", "sobrenome", "observacoes"}
    }
    return supplier | {
        "nome": "Aurora Materiais Ltda.", "cnpj": "11.222.333/0001-81",
        "email": "contato@aurora.exemplo.com",
        "fornecimento": "Materiais de escritório e embalagens.",
    } | changes
