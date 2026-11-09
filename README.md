# Vermelho · Cadastro de clientes e empresas

Sistema web local para cadastrar, consultar, editar e excluir clientes e fornecedores. Interface em português, responsiva, com a marca Vermelho, logo em V e identidade em tons de vermelho. Backend em Python/Flask, servidor Waitress e banco SQLite em arquivo. Frontend em HTML, CSS e JavaScript modular, sem etapa de compilação.

## Novidades desta atualização

- Marca, logo, favicon, título da página, navegação, botões e demais elementos visuais atualizados para **Vermelho**.
- **Novo cadastro** agora é um botão flutuante vermelho no canto inferior direito. Permanece disponível durante a rolagem e abre o formulário da aba ativa. Fica oculto enquanto um diálogo está aberto.
- Nova aba **Fornecedores** na área de trabalho, com cadastro de empresa/razão social, CNPJ, endereço com busca de CEP, e-mail, telefone e descrição do que a empresa fornece.
- Fornecedores têm busca por empresa, CNPJ (com ou sem pontuação), e-mail ou fornecimento, filtros, visualização em tela cheia, edição e exclusão com confirmação.
- Rodapé: **Cadastro de clientes e empresas** / **Busque de forma rápida seus contatos**.
- A estrutura do projeto e o arquivo SQLite existente foram mantidos. A atualização acrescenta somente a tabela `fornecedores`; não recria nem altera os registros de `clientes`.

## Requisitos

- Python 3.10 ou superior (verificado com Python 3.12.4 no Windows).
- Navegador atualizado, como Chrome, Edge ou Firefox.
- Internet para instalar as dependências e consultar o CEP. Cadastro, busca, edição, visualização e exclusão funcionam sem internet após a instalação.

## Instalação no Windows

Abra o PowerShell na pasta do projeto:

```powershell
cd "E:\programa rapido\cadastro basico"
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Não é necessário ativar o ambiente virtual nem mudar a política de execução do PowerShell.

## Execução

```powershell
.\.venv\Scripts\python.exe app.py
```

Acesse **http://127.0.0.1:8000** no navegador. Mantenha o terminal aberto enquanto utiliza o sistema. Para encerrar, pressione `Ctrl+C` nesse terminal. Para voltar a usar, execute o mesmo comando; os registros anteriores serão carregados.

Se o servidor estava aberto durante a atualização, encerre e execute novamente o comando para carregar as novas rotas de fornecedores. Depois, recarregue a página. Não é necessário reinstalar dependências nem substituir o banco.

Se a porta estiver em uso:

```powershell
$env:PORT = "8001"
.\.venv\Scripts\python.exe app.py
```

Nesse caso, acesse **http://127.0.0.1:8001**. O servidor fica restrito ao computador local.

### Linux e macOS

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python app.py
```

## Utilização

- **Área de trabalho:** alterne entre Clientes e Fornecedores pela navegação. A aba também fica identificada na URL (`#clientes` ou `#fornecedores`) e é preservada ao recarregar.
- **Novo cadastro:** use o botão flutuante no canto inferior direito. Em Clientes, preencha nome, sobrenome, telefone, e-mail, endereço e observações. Em Fornecedores, preencha empresa/razão social, CNPJ, telefone, e-mail, endereço e o que a empresa fornece.
- **CEP:** digite oito números e clique na lupa. Rua, bairro, cidade e estado são preenchidos pela consulta ao [ViaCEP](https://viacep.com.br/). Confira o resultado e informe o número. Em caso de CEP inexistente ou indisponibilidade do serviço, o endereço pode ser preenchido manualmente.
- **Busca:** pesquisa instantânea por nome, sobrenome ou e-mail em Clientes; por empresa, CNPJ, e-mail ou fornecimento em Fornecedores. Ignora diferenças de maiúsculas e acentos.
- **Filtros:** use cidade, estado e as opções Todos, Completos ou Pendentes. Os filtros podem ser combinados com a busca.
- **Visualização:** clique no nome do cliente/fornecedor ou no ícone de expandir para abrir a ficha em tela cheia dentro do navegador.
- **Edição:** clique no lápis na listagem ou em Editar cadastro na ficha.
- **Exclusão:** clique na lixeira e confirme. Cancelar ou pressionar `Esc` mantém o registro.
- **Listagem:** clientes são ordenados por nome e sobrenome; fornecedores, por empresa/razão social. Após salvar, busca e filtros são limpos para que o registro apareça na lista atualizada da aba correspondente.

### Validações e campos vazios

- Telefone com máscara automática: `(11)99999-9999`; também aceita fixo `(11)3333-3333`.
- E-mail com domínio e extensão, por exemplo `nome@empresa.com` ou `nome@empresa.com.br`.
- CEP no formato `00000-000` e estado entre as UFs brasileiras.
- Nomes de clientes aceitam letras com acentos, espaços, apóstrofos e hífens. Razão social aceita números e pontuação, como `Aurora & Filhos Ltda.`. Todos os campos têm limite de tamanho, inclusive observações e descrição do fornecimento (2.000 caracteres).
- CNPJ com máscara de preenchimento: aceita valores reais ou fictícios, como `12.345.678/9012-34` e `00.000.000/0000-00`, além do formato alfanumérico. É exigido apenas o formato completo; não há verificação dos dígitos de controle nem consulta à situação cadastral da empresa.
- Campos vazios são destacados em vermelho ao sair do campo ou tentar salvar. Ao editar um cadastro pendente, os campos ausentes já aparecem destacados.
- Campos ausentes exigem confirmação explícita para salvar; o cadastro fica como **Pendente**. Em Clientes, observações também são consideradas; em Fornecedores, a descrição do fornecimento é considerada. Apenas complemento é opcional, pois nem todo endereço o possui.
- Um cadastro totalmente vazio não é salvo. Formatos inválidos precisam ser corrigidos, mesmo se você confirmar os campos ausentes.
- As validações e as confirmações de cadastro incompleto e exclusão também são exigidas pela API.

## Arquivo SQLite e persistência

Os dados ficam em **`dados/clientes.sqlite3`**, criado automaticamente na primeira execução. O caminho é resolvido a partir da pasta do projeto, independentemente de onde o comando for executado. A aplicação não usa memória do navegador como banco e não insere clientes de demonstração.

O mesmo arquivo mantém duas tabelas independentes: `clientes` e `fornecedores`. Na inicialização, `CREATE TABLE IF NOT EXISTS` acrescenta a tabela de fornecedores de forma idempotente. IDs, campos, datas e sequência de IDs dos clientes existentes são preservados. Editar ou excluir um fornecedor não afeta um cliente que tenha o mesmo ID.

Antes desta atualização, foi feita uma cópia do banco em `dados/backups/antes-vermelho-20261109-182417.sqlite3`. Essa pasta está ignorada pelo Git para não incluir registros locais no versionamento.

Cada alteração é gravada em uma transação SQLite, com `synchronous=FULL`, consultas parametrizadas e espera de até 10 segundos por bloqueios de escrita. A resposta de sucesso só é enviada após o commit. Em caso de falha ao salvar, a interface mantém os campos e apresenta uma mensagem para permitir nova tentativa. O modo de journal mantém um único arquivo principal após cada transação concluída.

Para guardar uma cópia dos registros, encerre o servidor e copie `dados/clientes.sqlite3` para um local seguro. Para restaurar, com o servidor parado, recoloque o arquivo nesse caminho. Não exclua esse arquivo ao atualizar o código. Falhas físicas de disco ou exclusão manual não são evitadas pelo software; mantenha uma cópia se os registros forem importantes.

O caminho pode ser alterado com a variável `CADASTRO_DATABASE`, preferencialmente usando um caminho absoluto. Os testes usam arquivos temporários separados e não alteram o banco de uso real.

## Testes

### Resultado da verificação — 09/11/2026

**37 testes aprovados:** 24 de API/persistência e 13 de navegador, sem erros JavaScript nos fluxos exercitados. O botão flutuante foi verificado em 320, 390, 768 e 1440 pixels, inclusive após rolar a página e abrir/fechar o formulário. A identidade vermelha, a marca e as frases do rodapé também foram verificadas.

No banco de uso real, a comparação antes/depois confirmou os **100 clientes existentes preservados integralmente**, incluindo campos, IDs, datas e sequência. A nova tabela de fornecedores iniciou vazia e o `PRAGMA integrity_check` retornou `ok`.

Os testes de regressão dos clientes foram mantidos. A suíte inclui também migração aditiva, isolamento entre as tabelas, cadastro de fornecedores, CNPJ numérico/alfanumérico, navegação entre abas, identidade Vermelho e posição/funcionamento do botão flutuante durante a rolagem.

As verificações usam Windows, Python 3.12.4 e Chromium via Playwright 1.64.1, com layouts de 320, 390, 768, 1024 e 1440 pixels. As capturas usam apenas dados de teste em bancos temporários. Os dados reais existentes permanecem no arquivo original.

### Backend e persistência

Após instalar `requirements.txt`:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_api tests.test_suppliers -v
```

Verifica CRUD, confirmações obrigatórias, formatos, ordenação com acentos, dados preservados após recriar a aplicação, integridade do arquivo SQLite, gravações concorrentes, tratamento de falha de disco, entrada JSON e consulta de CEP com respostas simuladas.

### Navegador e suíte completa

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m playwright install chromium
.\.venv\Scripts\python.exe -m unittest tests.test_api tests.test_suppliers tests.test_browser -v
```

Os testes abrem o Chromium em segundo plano e iniciam um servidor temporário automaticamente. Não é necessário executar `app.py` antes. Verificam o fluxo real da interface, confirmação de campos ausentes, erro de salvamento sem perda do formulário, busca e filtros, máscaras, endereço por CEP, edição, exclusão, visualização em tela cheia e layout de celular. Capturas são salvas em `test-results/`.

Os testes de CEP da suíte são determinísticos e simulam respostas do provedor. Para verificar a consulta real, com o servidor ativo:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/cep/01001000
```

### Verificação manual

1. Crie um cliente com os campos preenchidos e confirme que ele aparece na lista.
2. Recarregue a página, encerre e reinicie o servidor; o cliente deve permanecer.
3. Busque por nome, sobrenome e e-mail; combine os filtros.
4. Abra a ficha, edite o nome e confirme a nova posição alfabética.
5. Tente salvar com e-mail inválido: a gravação deve ser bloqueada.
6. Deixe um campo vazio: ele deve ficar vermelho e a confirmação deve aparecer antes de salvar.
7. Cancele uma exclusão, confira que o registro permaneceu e depois confirme a exclusão.
8. Reduza a largura do navegador e confira listagem, formulário e ficha.
9. Role a página e verifique que Novo cadastro permanece no canto inferior direito, em vermelho.
10. Abra Fornecedores, cadastre uma empresa, pesquise pelo CNPJ e pelo que ela fornece, edite e visualize a ficha.
11. Confirme que um CNPJ fictício completo pode ser salvo, que um formato incompleto é sinalizado e que campos ausentes exigem confirmação.
12. Retorne a Clientes e confira que seus registros continuam intactos.

## Organização

```text
app.py                      Inicialização do servidor local
cadastro/
  __init__.py               Rotas HTTP, consulta de CEP e tratamento de erros
  database.py               Conexões, transações e operações SQLite
  validation.py             Regras de validação no servidor
  supplier_validation.py    Campos de empresa e validação de CNPJ
  supplier_repository.py    Persistência isolada na tabela fornecedores
  supplier_routes.py        API de fornecedores
templates/index.html        Estrutura da página e diálogos
static/
  favicon.svg               Logo em V e favicon da marca Vermelho
  css/styles.css            Estilos e identidade visual
  css/responsive.css        Adaptação para tablet e celular
  js/api.js                 Comunicação HTTP
  js/app.js                 Estado, eventos e fluxos da interface
  js/components.js          Componentes reutilizáveis de tabela e formulários
  js/icons.js               Ícones SVG reutilizáveis
  js/validation.js          Validação e máscaras da interface
  js/supplier-validation.js Campos, máscara e validação de CNPJ
  js/directories.js         Configuração das abas Clientes e Fornecedores
dados/clientes.sqlite3      Banco local, criado automaticamente
tests/                      Testes isolados de API e navegador
requirements.txt            Dependências de execução
requirements-dev.txt        Dependências para testes no navegador
```

## Arquivos desta atualização

- **Interface e marca:** `templates/index.html`, `static/favicon.svg`, `static/css/styles.css` e `static/css/responsive.css`.
- **Componentes e fluxos:** `static/js/app.js`, `static/js/components.js`, `static/js/api.js`, `static/js/icons.js` e `static/js/validation.js`; novos `static/js/directories.js` e `static/js/supplier-validation.js`.
- **Backend e banco:** `cadastro/__init__.py`, `cadastro/database.py` e `cadastro/validation.py`; novos `cadastro/supplier_routes.py`, `cadastro/supplier_repository.py` e `cadastro/supplier_validation.py`.
- **Testes e documentação:** `tests/fixtures.py`, `tests/test_browser.py`, novo `tests/test_suppliers.py`, `.gitignore` e `README.md`.

O projeto mantém o escopo de cadastro de clientes e fornecedores solicitado.
