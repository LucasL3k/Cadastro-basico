import {
  fields as customerFields,
  validate as validateContact,
} from "./validation.js";

export const supplierFields = {
  nome: ["Empresa / razão social", 160],
  cnpj: ["CNPJ", 18],
  ...Object.fromEntries(
    Object.entries(customerFields).filter(
      ([key]) => !["nome", "sobrenome", "observacoes"].includes(key),
    ),
  ),
  fornecimento: ["O que a empresa fornece", 2000],
};

export function cnpjMask(value) {
  const text = value
    .toUpperCase()
    .replace(/[^A-Z0-9]/g, "")
    .slice(0, 14);
  let masked = "";
  for (let i = 0; i < text.length; i++) {
    masked += { 2: ".", 5: ".", 8: "/", 12: "-" }[i] || "";
    masked += text[i];
  }
  return masked;
}

export function validCnpjFormat(value) {
  // Fictitious values are allowed; only the complete format is required.
  return /^[A-Z0-9]{2}\.[A-Z0-9]{3}\.[A-Z0-9]{3}\/[A-Z0-9]{4}-[0-9]{2}$/.test(value);
}

export function validateSupplier(data) {
  const result = validateContact(data, supplierFields, []);
  if (data.cnpj && !validCnpjFormat(data.cnpj.toUpperCase()))
    result.errors.cnpj =
      "Preencha o CNPJ no formato 00.000.000/0000-00. Números fictícios são aceitos.";
  return result;
}
