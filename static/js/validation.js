export const states =
  "AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO".split(
    " ",
  );
export const fields = {
  nome: ["Nome", 80],
  sobrenome: ["Sobrenome", 120],
  telefone: ["Telefone", 14],
  email: ["E-mail", 254],
  cep: ["CEP", 9],
  logradouro: ["Rua / avenida", 180],
  numero: ["Número", 20],
  complemento: ["Complemento", 100],
  bairro: ["Bairro", 100],
  cidade: ["Cidade", 100],
  uf: ["Estado", 2],
  observacoes: ["Observações", 2000],
};
export const required = Object.keys(fields).filter(
  (key) => key !== "complemento",
);
export function normalize(text) {
  return text
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLocaleLowerCase("pt-BR");
}
export function phoneMask(text) {
  const d = text.replace(/\D/g, "").slice(0, 11);
  if (!d) return "";
  if (d.length <= 2) return `(${d}`;
  const split = d.length > 10 ? 7 : 6;
  return `(${d.slice(0, 2)})${d.slice(2, split)}${d.length > split ? `-${d.slice(split)}` : ""}`;
}
export function cepMask(text) {
  const d = text.replace(/\D/g, "").slice(0, 8);
  return d.length > 5 ? `${d.slice(0, 5)}-${d.slice(5)}` : d;
}
export function validate(
  data,
  schema = fields,
  nameFields = ["nome", "sobrenome"],
) {
  const errors = {};
  const missing = Object.keys(schema).filter(
    (key) => key !== "complemento" && !data[key],
  );
  for (const [key, [label, limit]] of Object.entries(schema)) {
    if (data[key]?.length > limit)
      errors[key] = `Use até ${limit} caracteres em ${label.toLowerCase()}.`;
  }
  for (const key of nameFields) {
    if (
      data[key] &&
      (!/\p{L}/u.test(data[key]) || !/^[\p{L} '\-.’]+$/u.test(data[key]))
    )
      errors[key] = "Use letras, espaços, hífens ou apóstrofos.";
  }
  if (
    data.telefone &&
    !/^\([1-9][0-9]\)[2-9][0-9]{3,4}-[0-9]{4}$/.test(data.telefone)
  )
    errors.telefone = "Use (11)99999-9999 ou (11)3333-3333, com DDD válido.";
  if (
    data.email &&
    (!/^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?)*\.[A-Za-z]{2,}$/.test(
      data.email,
    ) ||
      data.email.startsWith(".") ||
      data.email.split("@")[0].includes("..") ||
      data.email.includes(".@"))
  )
    errors.email = "Informe um e-mail válido, como nome@exemplo.com.";
  if (data.cep && !/^\d{5}-\d{3}$/.test(data.cep))
    errors.cep = "Use o formato 00000-000.";
  if (data.uf && !states.includes(data.uf))
    errors.uf = "Selecione um estado válido.";
  if (!Object.values(data).some(Boolean))
    errors.geral = "Preencha pelo menos um campo para criar o cadastro.";
  return { errors, missing };
}
