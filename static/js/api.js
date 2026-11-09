export class ApiError extends Error {
  constructor(message, data, status) {
    super(message);
    this.data = data;
    this.status = status;
  }
}
export async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(`/api${path}`, {
      ...options,
      headers: { "Content-Type": "application/json", ...options.headers },
    });
  } catch {
    throw new ApiError(
      "Não foi possível conectar ao sistema. Verifique se o servidor está aberto. Seus campos foram mantidos.",
      {},
      0,
    );
  }
  if (response.status === 204) return null;
  let data;
  try {
    data = await response.json();
  } catch {
    throw new ApiError(
      "O servidor retornou uma resposta inesperada. Tente novamente.",
      {},
      response.status,
    );
  }
  if (!response.ok)
    throw new ApiError(
      data.message || "Não foi possível concluir a operação.",
      data,
      response.status,
    );
  return data;
}
export function directoryApi(resource) {
  const base = `/${resource}`;
  return {
    list: () => request(base),
    get: (id) => request(`${base}/${id}`),
    save: (id, data) =>
      request(`${base}${id ? `/${id}` : ""}`, {
        method: id ? "PUT" : "POST",
        body: JSON.stringify(data),
      }),
    remove: (id) =>
      request(`${base}/${id}`, {
        method: "DELETE",
        body: JSON.stringify({ confirmar_exclusao: true }),
      }),
  };
}
export const api = {
  ...directoryApi("clientes"),
  cep: (code) => request(`/cep/${code}`, { signal: AbortSignal.timeout(9000) }),
};
