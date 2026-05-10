const API_BASE = import.meta.env.VITE_API_URL || "https://vendafacil-api.cursar.space";

export function getToken(): string {
  return localStorage.getItem("vf_token") || "";
}

export function setToken(token: string) {
  localStorage.setItem("vf_token", token);
}

export function clearToken() {
  localStorage.removeItem("vf_token");
}

async function request(path: string, options: RequestInit = {}) {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  const data = await res.json();

  if (!res.ok) {
    throw new Error(data.detail || "Erro na requisição");
  }
  return data;
}

// Auth
export function login(email: string, senha: string) {
  return request("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, senha }),
  });
}

export function registro(email: string, nome: string, senha: string) {
  return request("/api/auth/registro", {
    method: "POST",
    body: JSON.stringify({ email, nome, senha }),
  });
}

export function getMe() {
  if (!getToken()) return Promise.resolve(null);
  return request("/api/auth/me")
    .then((d) => d.user)
    .catch(() => null);
}
