import { icon } from "./icons.js";
import { states } from "./validation.js";
import { directories } from "./directories.js";

export const escapeHtml = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (char) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        char
      ],
  );
export const fullName = (record, directory = directories.clientes) =>
  `${record.nome || ""} ${record.sobrenome || ""}`.trim() ||
  `${directory.singular === "cliente" ? "Cliente" : "Fornecedor"} sem nome`;

export function avatar(record, large = false) {
  const secondName = record.sobrenome || record.nome?.split(" ")[1];
  const initials =
    `${record.nome?.[0] || ""}${secondName?.[0] || ""}`.toLocaleUpperCase(
      "pt-BR",
    ) || "?";
  return `<span class="avatar avatar-${record.id % 4 || 0} ${large ? "avatar-large" : ""}" aria-hidden="true">${escapeHtml(initials)}</span>`;
}

export function badge(record) {
  return `<span class="status-badge ${record.completo ? "complete" : "pending"}"><span></span>${record.completo ? "Completo" : "Pendente"}</span>`;
}

function recordActions(record, name, directory) {
  return `<div class="row-actions"><button class="icon-button" data-action="view" data-id="${record.id}" aria-label="Visualizar ${name} em tela cheia" title="Visualizar em tela cheia">${icon("expand")}</button><button class="icon-button" data-action="edit" data-id="${record.id}" aria-label="Editar ${name}" title="Editar ${directory.singular}">${icon("edit")}</button><button class="icon-button danger" data-action="delete" data-id="${record.id}" aria-label="Excluir ${name}" title="Excluir ${directory.singular}">${icon("trash")}</button></div>`;
}

export function recordRow(record, directory = directories.clientes) {
  const name = escapeHtml(fullName(record, directory));
  const city = escapeHtml(
    [record.cidade, record.uf].filter(Boolean).join(", "),
  );
  const reference =
    directory.key === "fornecedores"
      ? record.cnpj || "CNPJ não informado"
      : `Cliente #${String(record.id).padStart(3, "0")}`;
  return `<tr data-id="${record.id}"><td><div class="customer-identity">${avatar(record)}<div><button class="customer-name" data-action="view" data-id="${record.id}" title="Visualizar ${name}">${name}</button><span class="customer-id">${escapeHtml(reference)}</span></div></div></td><td><div class="contact-line">${icon("mail")}<span>${escapeHtml(record.email) || '<span class="muted">E-mail não informado</span>'}</span></div><div class="contact-line secondary-line">${icon("phone")}<span>${escapeHtml(record.telefone) || "Telefone não informado"}</span></div></td><td><div class="location-line">${icon("pin")}<span>${city || '<span class="muted">Não informada</span>'}</span></div><span class="address-line">${escapeHtml(record.bairro) || "—"}</span></td><td>${badge(record)}</td><td>${recordActions(record, name, directory)}</td></tr>`;
}

export function emptyState(filtered = false, directory = directories.clientes) {
  return `<div class="empty-illustration"><div class="illustration-halo"></div><div class="illustration-card">${icon(filtered ? "search" : directory.key === "fornecedores" ? "building" : "contact")}<span></span><i></i></div><span class="illustration-plus">${icon(filtered ? "search" : "plus")}</span><span class="illustration-spark spark-one"></span><span class="illustration-spark spark-two"></span></div><h3>${filtered ? `Nenhum ${directory.singular} encontrado` : "Sua lista começa com uma conexão"}</h3><p>${filtered ? "Tente outro nome ou ajuste os filtros para encontrar quem procura." : `Cadastre seu primeiro ${directory.singular} e tenha as informações<br>que importam sempre à mão.`}</p><button class="button ${filtered ? "secondary" : "primary"}" data-action="${filtered ? "clear" : "new"}">${icon(filtered ? "filter" : "plus")}${filtered ? "Limpar busca e filtros" : `Cadastrar primeiro ${directory.singular}`}</button>`;
}

function field(name, data, schema, opts = {}) {
  const [label, limit] = schema[name];
  const value = escapeHtml(data[name] || "");
  const attr = `id="field-${name}" name="${name}" aria-describedby="error-${name}"`;
  let input;
  if (name === "uf")
    input = `<select ${attr} autocomplete="address-level1"><option value="">Selecione</option>${states.map((uf) => `<option value="${uf}" ${data.uf === uf ? "selected" : ""}>${uf}</option>`).join("")}</select>`;
  else if (opts.multiline)
    input = `<textarea ${attr} maxlength="${limit}" rows="3" placeholder="${escapeHtml(opts.placeholder)}">${value}</textarea>`;
  else
    input = `<input ${attr} type="${opts.type || "text"}" maxlength="${limit}" value="${value}" placeholder="${escapeHtml(opts.placeholder || "")}" autocomplete="${opts.autocomplete || "off"}" ${opts.mode ? `inputmode="${opts.mode}"` : ""}>`;
  if (name === "cep")
    input = `<div class="cep-input">${input}<button type="button" id="lookup-cep" title="Buscar endereço pelo CEP" aria-label="Buscar endereço pelo CEP">${icon("search")}</button></div>`;
  return `<div class="field ${opts.className || ""}" data-field="${name}"><label for="field-${name}">${escapeHtml(label)}${name === "complemento" ? '<span class="optional">opcional</span>' : ""}</label>${input}<span class="field-error" id="error-${name}"></span></div>`;
}

function addressFields(render) {
  return `${render("cep", { placeholder: "00000-000", mode: "numeric", autocomplete: "postal-code" })}<div class="cep-help" id="cep-status" role="status">${icon("pin")}<span>Digite o CEP e clique na lupa.<br>Ou preencha o endereço manualmente.</span></div>${render("logradouro", { className: "span-three", placeholder: "Rua, avenida, praça…", autocomplete: "address-line1" })}${render("numero", { placeholder: "123 ou s/n" })}${render("complemento", { className: "span-two", placeholder: "Apartamento, bloco…", autocomplete: "address-line2" })}${render("bairro", { className: "span-two", placeholder: "Nome do bairro" })}${render("cidade", { className: "span-three", placeholder: "Nome da cidade", autocomplete: "address-level2" })}${render("uf")}`;
}

export function editorForm(data = {}, directory = directories.clientes) {
  const render = (key, opts) => field(key, data, directory.fields, opts);
  return `<form id="customer-form" novalidate><header class="dialog-header"><div><div class="eyebrow">DIRETÓRIO DE ${directory.label.toUpperCase()}</div><h2 id="editor-title">${data.id ? `Editar ${directory.singular}` : "Novo cadastro"}</h2><p>${data.id ? "Mantenha as informações deste contato em dia." : "Um novo contato, tudo no lugar certo."}</p></div><button class="icon-button close-editor" type="button" aria-label="Fechar cadastro">${icon("close")}</button></header><div class="form-body"><div id="form-error" class="form-error" role="alert" hidden></div><section class="form-section"><div class="section-heading"><span>01</span><h3>${directory.section}</h3><p>Vamos começar pelo essencial.</p></div><div class="form-grid">${render("nome", { placeholder: directory.identityPlaceholder, autocomplete: directory.key === "clientes" ? "given-name" : "organization" })}${render(directory.secondField, { placeholder: directory.secondPlaceholder, autocomplete: directory.key === "clientes" ? "family-name" : "off" })}${render("email", { placeholder: "nome@exemplo.com", type: "email", autocomplete: "email" })}${render("telefone", { placeholder: "(11)99999-9999", type: "tel", autocomplete: "tel", mode: "tel" })}</div></section><section class="form-section"><div class="section-heading"><span>02</span><h3>Endereço</h3><p>Busque pelo CEP para preencher.</p></div><div class="form-grid address-grid">${addressFields(render)}</div></section><section class="form-section"><div class="section-heading"><span>03</span><h3>${directory.notesTitle}</h3><p>${directory.notesHint}</p></div>${render(directory.notesField, { multiline: true, placeholder: directory.notesPlaceholder })}<div class="character-count"><span id="notes-count">${(data[directory.notesField] || "").length}</span> / 2.000 caracteres</div></section></div><footer class="dialog-footer"><p>${icon("alert")}Campos vazios serão sinalizados antes de salvar.</p><div><button class="button secondary close-editor" type="button">Cancelar</button><button class="button primary" id="save-customer" type="submit">${icon("check")}Salvar cadastro</button></div></footer></form>`;
}

function detailField(label, value) {
  return `<div class="detail-field"><dt>${escapeHtml(label)}</dt><dd class="${value ? "" : "not-filled"}">${escapeHtml(value) || "Não informado"}</dd></div>`;
}

export function recordDetails(record, directory = directories.clientes) {
  const notes = record[directory.notesField];
  return `<header class="detail-topbar"><button class="text-button" id="close-details">${icon("back")}Voltar para ${directory.label.toLowerCase()}</button><span class="detail-breadcrumb">${directory.singular.toUpperCase()} #${String(record.id).padStart(3, "0")}</span><button class="icon-button" data-close-details aria-label="Fechar visualização">${icon("close")}</button></header><div class="detail-main"><div class="detail-hero"><div class="detail-identity">${avatar(record, true)}<div><div class="eyebrow">PERFIL DO ${directory.singular.toUpperCase()}</div><h1 id="detail-title">${escapeHtml(fullName(record, directory))}</h1>${badge(record)}</div></div><div class="detail-actions"><button class="button secondary danger" data-action="delete" data-id="${record.id}">${icon("trash")}Excluir</button><button class="button primary" data-action="edit" data-id="${record.id}">${icon("edit")}Editar cadastro</button></div></div><div class="detail-grid"><section class="detail-card"><h2>${icon(directory.icon)}${directory.section}</h2><dl>${detailField(directory.identityLabel, record.nome)}${detailField(directory.fields[directory.secondField][0], record[directory.secondField])}${detailField("E-mail", record.email)}${detailField("Telefone", record.telefone)}</dl></section><section class="detail-card"><h2>${icon("pin")}Endereço</h2><dl>${detailField("CEP", record.cep)}${detailField("Rua / avenida", record.logradouro)}${detailField("Número", record.numero)}${detailField("Complemento", record.complemento)}${detailField("Bairro", record.bairro)}${detailField("Cidade / estado", [record.cidade, record.uf].filter(Boolean).join(" / "))}</dl></section><section class="detail-card notes-card"><h2>${icon("note")}${directory.notesTitle}</h2><p class="notes-text ${notes ? "" : "not-filled"}">${escapeHtml(notes) || "Não informado"}</p></section></div></div>`;
}
