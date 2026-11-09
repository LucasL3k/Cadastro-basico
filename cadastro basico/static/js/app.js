import { api } from "./api.js";
import { directories } from "./directories.js";
import { cnpjMask } from "./supplier-validation.js";
import { icon, hydrateIcons } from "./icons.js";
import { normalize, phoneMask, cepMask } from "./validation.js";
import {
  escapeHtml,
  fullName,
  recordRow,
  emptyState,
  editorForm,
  recordDetails,
} from "./components.js";

const $ = (selector) => document.querySelector(selector);
const state = {
  records: [],
  mode: "clientes",
  listGeneration: 0,
  query: "",
  status: "all",
  city: "",
  uf: "",
  editing: null,
  detail: null,
  busy: false,
  formGeneration: 0,
};
const directory = () => directories[state.mode];
const sortRecords = () =>
  state.records.sort(
    (a, b) =>
      Number(!a.nome) - Number(!b.nome) ||
      a.nome.localeCompare(b.nome, "pt-BR", { sensitivity: "base" }) ||
      (a.sobrenome || "").localeCompare(b.sobrenome || "", "pt-BR", {
        sensitivity: "base",
      }) ||
      a.id - b.id,
  );

function toast(message, error = false) {
  const el = document.createElement("div");
  el.className = `toast${error ? " error" : ""}`;
  el.innerHTML = `${icon(error ? "alert" : "check")}<span>${escapeHtml(message)}</span>`;
  const modal = document.querySelector("dialog[open]");
  let modalHost;
  if (modal) {
    modalHost = document.createElement("div");
    modalHost.className = "toast-stack";
    modalHost.setAttribute("role", "status");
    modal.append(modalHost);
  }
  (modalHost || $("#toasts")).append(el);
  setTimeout(
    () => {
      el.remove();
      modalHost?.remove();
    },
    error ? 10000 : 5500,
  );
}

function updateFilterOptions() {
  for (const [id, key, label] of [
    ["filter-city", "cidade", "Todas as cidades"],
    ["filter-state", "uf", "Todos os estados"],
  ]) {
    const select = $(`#${id}`);
    const current = select.value;
    const values = [
      ...new Set(state.records.map((c) => c[key]).filter(Boolean)),
    ].sort((a, b) => a.localeCompare(b, "pt-BR"));
    if (current && !values.includes(current)) values.push(current);
    select.innerHTML = `<option value="">${label}</option>${values.map((value) => `<option value="${escapeHtml(value)}">${escapeHtml(value)}</option>`).join("")}`;
    select.value = current;
  }
}

function renderList() {
  sortRecords();
  const query = normalize(state.query.trim());
  const customers = state.records.filter((customer) => {
    const text = normalize(
      directory()
        .searchFields.map((key) => customer[key] || "")
        .join(" "),
    );
    return (
      (!query ||
        text.includes(query) ||
        (state.mode === "fornecedores" &&
          customer.cnpj
            .replace(/[./-]/g, "")
            .toLowerCase()
            .includes(query.replace(/[./-]/g, "")))) &&
      (!state.city || customer.cidade === state.city) &&
      (!state.uf || customer.uf === state.uf) &&
      (state.status === "all" ||
        (state.status === "complete" ? customer.completo : !customer.completo))
    );
  });
  const total = state.records.length;
  const complete = state.records.filter((c) => c.completo).length;
  $("#total-count").textContent =
    $(
      state.mode === "clientes" ? "#nav-count" : "#supplier-count",
    ).textContent =
    $("#count-all").textContent =
      total;
  $("#count-complete").textContent = complete;
  $("#count-pending").textContent = total - complete;
  $("#results-label").textContent =
    `${customers.length} ${customers.length === 1 ? directory().singular : directory().label.toLowerCase()}`;
  $("#footer-count").textContent =
    `Exibindo ${customers.length} de ${total} ${total === 1 ? directory().singular : directory().label.toLowerCase()}`;
  $("#customer-rows").innerHTML = customers
    .map((record) => recordRow(record, directory()))
    .join("");
  $("#list-state").hidden = customers.length > 0;
  if (!customers.length)
    $("#list-state").innerHTML = emptyState(
      !!(query || state.city || state.uf || state.status !== "all"),
      directory(),
    );
  document.querySelectorAll("[data-status]").forEach((button) => {
    const selected = button.dataset.status === state.status;
    button.classList.toggle("active", selected);
    button.setAttribute("aria-pressed", String(selected));
  });
  $("#filter-toggle .filter-dot").hidden = !(state.city || state.uf);
  updateFilterOptions();
}

async function loadRecords() {
  const current = directory();
  const generation = ++state.listGeneration;
  try {
    const records = await current.api.list();
    if (current !== directory() || generation !== state.listGeneration) return;
    state.records = records;
    renderList();
  } catch (error) {
    if (current === directory() && generation === state.listGeneration)
      throw error;
  }
}

function clearFilters() {
  state.query = state.city = state.uf = "";
  state.status = "all";
  $("#search").value = $("#filter-city").value = $("#filter-state").value = "";
  renderList();
}

function confirmAction({
  title,
  description,
  accept,
  destructive = false,
  missing = [],
}) {
  const dialog = $("#confirmation");
  $("#confirm-content").innerHTML =
    `<div class="confirmation-icon ${destructive ? "destructive" : ""}">${icon(destructive ? "trash" : "alert")}</div><h2 id="confirm-title">${escapeHtml(title)}</h2><p id="confirm-description">${escapeHtml(description)}</p>${missing.length ? `<div class="confirm-missing">Não preenchidos: ${missing.map((key) => escapeHtml(directory().fields[key]?.[0] || key)).join(", ")}.</div>` : ""}<div class="confirm-actions"><button class="button secondary" id="confirm-cancel">${destructive ? "Cancelar" : "Voltar e preencher"}</button><button class="button ${destructive ? "destructive" : "primary"}" id="confirm-accept">${escapeHtml(accept)}</button></div>`;
  dialog.returnValue = "";
  return new Promise((resolve) => {
    dialog.addEventListener(
      "close",
      () => resolve(dialog.returnValue === "confirmed"),
      { once: true },
    );
    $("#confirm-cancel").onclick = () => dialog.close("cancel");
    $("#confirm-accept").onclick = () => dialog.close("confirmed");
    dialog.showModal();
    $("#confirm-cancel").focus();
  });
}

function formData() {
  return Object.fromEntries(
    Object.keys(directory().fields).map((key) => [
      key,
      $(`#field-${key}`).value.trim(),
    ]),
  );
}

function fieldError(key, message = "") {
  const field = $(`[data-field="${key}"]`);
  if (!field) return;
  field.classList.toggle("invalid", !!message);
  $(`#field-${key}`).setAttribute("aria-invalid", String(!!message));
  $(`#error-${key}`).textContent = message;
}

function displayValidation(errors, missing, focus = false) {
  for (const key of Object.keys(directory().fields))
    fieldError(
      key,
      errors[key] ||
        (missing.includes(key) ? "Este campo não foi preenchido." : ""),
    );
  const formError = $("#form-error");
  formError.hidden = !Object.keys(errors).length;
  formError.textContent =
    errors.geral ||
    "Confira os formatos dos campos destacados antes de continuar.";
  if (focus) {
    const key =
      Object.keys(errors).find((key) => directory().fields[key]) || missing[0];
    if (key) $(`#field-${key}`).focus();
  }
}

function lockForm(locked) {
  state.busy = locked;
  $("#customer-form")
    .querySelectorAll("button, input, textarea, select")
    .forEach((el) => {
      el.disabled = locked;
    });
  $("#save-customer").innerHTML = locked
    ? "Salvando…"
    : `${icon("check")}Salvar cadastro`;
}

async function submitForm(event) {
  event.preventDefault();
  if (state.busy) return;
  const data = formData();
  const { errors, missing } = directory().validate(data);
  displayValidation(errors, missing, true);
  if (Object.keys(errors).length) return;
  if (missing.length) {
    const accepted = await confirmAction({
      title: "Salvar com campos pendentes?",
      description:
        "Algumas informações não foram preenchidas. Tem certeza de que deseja salvar este cadastro assim? Você poderá completá-lo depois.",
      accept: "Salvar mesmo assim",
      missing,
    });
    if (!accepted) return;
    data.confirmar_incompleto = true;
  }
  lockForm(true);
  try {
    const wasEditing = !!state.editing;
    const customer = await directory().api.save(state.editing, data);
    state.records = state.records
      .filter((c) => c.id !== customer.id)
      .concat(customer);
    $("#editor").close();
    state.formGeneration++;
    clearFilters();
    toast(
      wasEditing
        ? "Cadastro atualizado com sucesso."
        : `${directory().singular === "cliente" ? "Cliente" : "Fornecedor"} cadastrado com sucesso.`,
    );
    // The committed response is already visible if a subsequent refresh fails.
    loadRecords().catch(() =>
      toast(
        "Cadastro salvo. Não foi possível sincronizar a lista agora; recarregue a página.",
        true,
      ),
    );
  } catch (error) {
    $("#form-error").hidden = false;
    $("#form-error").textContent = error.message;
    if (error.data?.errors) {
      displayValidation(error.data.errors, error.data.missing || [], true);
    } else $("#form-error").scrollIntoView({ block: "nearest" });
  } finally {
    lockForm(false);
  }
}

async function lookupCep() {
  const cep = $("#field-cep").value;
  if (!/^\d{5}-\d{3}$/.test(cep)) {
    fieldError("cep", "Preencha o CEP no formato 00000-000.");
    $("#field-cep").focus();
    return;
  }
  const generation = state.formGeneration;
  const before = formData();
  const button = $("#lookup-cep");
  button.disabled = true;
  $("#cep-status").className = "cep-help";
  $("#cep-status").textContent = "Buscando endereço…";
  try {
    const address = await api.cep(cep.replace("-", ""));
    if (
      generation !== state.formGeneration ||
      !$("#editor").open ||
      $("#field-cep").value !== cep ||
      state.busy
    )
      return;
    for (const key of ["logradouro", "bairro", "cidade", "uf"]) {
      if ($(`#field-${key}`).value.trim() === before[key]) {
        $(`#field-${key}`).value = address[key];
        fieldError(key, address[key] ? "" : "Complete este campo manualmente.");
      }
    }
    fieldError("cep");
    $("#cep-status").className = "cep-help success";
    $("#cep-status").textContent =
      "Endereço encontrado. Confira os dados e informe o número.";
    $("#field-numero").focus();
  } catch (error) {
    if (
      generation !== state.formGeneration ||
      !$("#editor").open ||
      $("#field-cep").value !== cep
    )
      return;
    $("#cep-status").className = "cep-help error";
    $("#cep-status").textContent = error.message;
  } finally {
    if (generation === state.formGeneration && !state.busy)
      button.disabled = false;
  }
}

function closeEditor() {
  if (state.busy) return;
  state.formGeneration++;
  $("#editor").close();
}

function openEditor(customer = {}) {
  state.editing = customer.id || null;
  state.formGeneration++;
  $("#details").close();
  $("#editor-content").innerHTML = editorForm(customer, directory());
  $("#customer-form").addEventListener("submit", submitForm);
  document
    .querySelectorAll(".close-editor")
    .forEach((button) => button.addEventListener("click", closeEditor));
  $("#lookup-cep").addEventListener("click", lookupCep);
  for (const key of Object.keys(directory().fields)) {
    const input = $(`#field-${key}`);
    input.addEventListener("blur", () => {
      const data = formData();
      const { errors, missing } = directory().validate(data);
      fieldError(
        key,
        errors[key] ||
          (missing.includes(key) ? "Este campo não foi preenchido." : ""),
      );
    });
    input.addEventListener("input", () => {
      if (key === "telefone") input.value = phoneMask(input.value);
      if (key === "cnpj") input.value = cnpjMask(input.value);
      if (key === "cep") {
        input.value = cepMask(input.value);
        $("#cep-status").className = "cep-help";
        $("#cep-status").textContent =
          "Clique na lupa para buscar o endereço deste CEP.";
        $("#lookup-cep").disabled = false;
      }
      if (key === directory().notesField)
        $("#notes-count").textContent = input.value.length;
      if (input.closest(".field").classList.contains("invalid")) {
        const { errors, missing } = directory().validate(formData());
        fieldError(
          key,
          errors[key] ||
            (missing.includes(key) ? "Este campo não foi preenchido." : ""),
        );
      }
    });
  }
  $("#editor").showModal();
  if (customer.id) displayValidation({}, customer.campos_pendentes || []);
  $("#field-nome").focus();
}

async function viewRecord(id) {
  const current = directory();
  try {
    const customer = await current.api.get(id);
    if (current !== directory()) return;
    state.detail = customer.id;
    $("#detail-content").innerHTML = recordDetails(customer, directory());
    $("#close-details").onclick = () => $("#details").close();
    $("[data-close-details]").onclick = () => $("#details").close();
    $("#details").showModal();
  } catch (error) {
    toast(error.message, true);
  }
}

async function deleteRecord(id) {
  if (state.busy) return;
  const customer = state.records.find((c) => c.id === id);
  if (!customer) return;
  const accepted = await confirmAction({
    title: `Excluir este ${directory().singular}?`,
    description: `O cadastro de ${fullName(customer, directory())} será excluído permanentemente. Esta ação não pode ser desfeita.`,
    accept: `Excluir ${directory().singular}`,
    destructive: true,
  });
  if (!accepted) return;
  state.busy = true;
  try {
    await directory().api.remove(id);
    state.records = state.records.filter((c) => c.id !== id);
    if (state.detail === id) $("#details").close();
    renderList();
    toast("Cadastro excluído com sucesso.");
    loadRecords().catch(() =>
      toast(
        "Cadastro excluído. Não foi possível sincronizar a lista agora.",
        true,
      ),
    );
  } catch (error) {
    toast(error.message, true);
  } finally {
    state.busy = false;
  }
}

document.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-action]");
  if (!button || state.busy) return;
  const { action, id } = button.dataset;
  if (action === "new") openEditor();
  else if (action === "clear") clearFilters();
  else if (action === "view") await viewRecord(Number(id));
  else if (action === "delete") await deleteRecord(Number(id));
  else if (action === "edit") {
    const current = directory();
    try {
      const record = await current.api.get(Number(id));
      if (current === directory()) openEditor(record);
    } catch (error) {
      toast(error.message, true);
    }
  } else if (action === "retry") initialize();
});

$("#editor").addEventListener("cancel", (event) => {
  if (state.busy) event.preventDefault();
  else state.formGeneration++;
});
$("#search").addEventListener("input", (event) => {
  state.query = event.target.value;
  renderList();
});
$("#filter-toggle").addEventListener("click", () => {
  $("#filters").hidden = !$("#filters").hidden;
  $("#filter-toggle").setAttribute(
    "aria-expanded",
    String(!$("#filters").hidden),
  );
});
$("#filter-city").addEventListener("change", (event) => {
  state.city = event.target.value;
  renderList();
});
$("#filter-state").addEventListener("change", (event) => {
  state.uf = event.target.value;
  renderList();
});
$("#clear-filters").addEventListener("click", clearFilters);
document.querySelectorAll("[data-status]").forEach((button) =>
  button.addEventListener("click", () => {
    state.status = button.dataset.status;
    renderList();
  }),
);

async function initialize() {
  try {
    await loadRecords();
  } catch (error) {
    $("#list-state").hidden = false;
    $("#list-state").innerHTML =
      `${icon("alert")}<h3>Não foi possível carregar os cadastros</h3><p>${escapeHtml(error.message)}</p><button class="button secondary" data-action="retry">Tentar novamente</button>`;
    $("#results-label").textContent = "Falha ao carregar";
  }
}
function switchDirectory() {
  const requested = location.hash.slice(1);
  const mode = Object.hasOwn(directories, requested) ? requested : "clientes";
  if (state.busy) {
    history.replaceState(null, "", `#${state.mode}`);
    return;
  }
  state.mode = mode;
  state.records = [];
  state.editing = state.detail = null;
  state.formGeneration++;
  state.listGeneration++;
  for (const selector of ["#editor", "#details", "#confirmation"])
    $(selector).close();
  const current = directory();
  document.querySelectorAll("[data-directory]").forEach((link) => {
    const active = link.dataset.directory === mode;
    link.classList.toggle("active", active);
    if (active) link.setAttribute("aria-current", "page");
    else link.removeAttribute("aria-current");
  });
  $("#breadcrumb-current").textContent = current.label;
  $("#page-title").innerHTML = `${current.title}<span>.</span>`;
  $("#page-description").textContent = current.description;
  $("#directory-heading").textContent =
    `Lista de ${current.label.toLowerCase()}`;
  $("#directory-icon").innerHTML = icon(current.icon);
  $("#identity-heading").innerHTML =
    `${mode === "clientes" ? "CLIENTE" : "EMPRESA / CNPJ"} ${icon("arrow-down")}`;
  $("#search").placeholder = `${current.search}…`;
  $("#search").setAttribute("aria-label", current.search);
  $("#new-record").title = `Cadastrar ${current.singular}`;
  $("#filters").hidden = true;
  $("#filter-toggle").setAttribute("aria-expanded", "false");
  clearFilters();
  $("#list-state").innerHTML =
    '<div class="loading-ring"></div><p>Carregando seus contatos…</p>';
  $("#results-label").textContent = "Carregando…";
  document.title = `Vermelho · ${current.label}`;
  initialize();
}

window.addEventListener("hashchange", switchDirectory);
hydrateIcons();
switchDirectory();
// Keep the inactive navigation counter accurate without touching the active list.
const other =
  directories[state.mode === "clientes" ? "fornecedores" : "clientes"];
other.api
  .list()
  .then((records) => {
    if (directory() !== other)
      $(
        other.key === "clientes" ? "#nav-count" : "#supplier-count",
      ).textContent = records.length;
  })
  .catch(() => {});
