"""Run the local application with a Windows-compatible WSGI server."""

import os

from waitress import serve

from cadastro import create_app

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    print(f"Cadastro de clientes disponível em http://127.0.0.1:{port}", flush=True)
    serve(app, host="127.0.0.1", port=port, threads=4)
