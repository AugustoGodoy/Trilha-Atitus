const TOKEN_KEY = 'trilha_token'

/** Base da API em produção (ex.: https://trilha-api.up.railway.app). Vazio = mesmo origin / proxy do Vite. */
export const API_BASE = (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, '') || ''

export function apiUrl(path: string): string {
  if (path.startsWith('http://') || path.startsWith('https://')) return path
  return `${API_BASE}${path.startsWith('/') ? path : `/${path}`}`
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string | null) {
  if (token) localStorage.setItem(TOKEN_KEY, token)
  else localStorage.removeItem(TOKEN_KEY)
}

export class ApiError extends Error {
  code: string
  status: number
  constructor(status: number, code: string, message: string) {
    super(message)
    this.status = status
    this.code = code
  }
}

async function parse<T>(res: Response): Promise<T> {
  const text = await res.text()
  const json = text ? JSON.parse(text) : null
  if (!res.ok) {
    const err = json?.error
    throw new ApiError(res.status, err?.code || 'ERROR', err?.message || res.statusText)
  }
  return json as T
}

function headers(json = true): HeadersInit {
  const h: Record<string, string> = {}
  if (json) h['Content-Type'] = 'application/json'
  const t = getToken()
  if (t) h.Authorization = `Bearer ${t}`
  return h
}

type Envelope<T> = { data: T; meta?: Record<string, unknown> }

export const api = {
  async get<T>(path: string): Promise<T> {
    return (await parse<Envelope<T>>(await fetch(apiUrl(path), { headers: headers(false) }))).data
  },
  async post<T>(path: string, body?: unknown): Promise<T> {
    return (await parse<Envelope<T>>(await fetch(apiUrl(path), {
      method: 'POST', headers: headers(), body: body === undefined ? undefined : JSON.stringify(body),
    }))).data
  },
  async patch<T>(path: string, body: unknown): Promise<T> {
    return (await parse<Envelope<T>>(await fetch(apiUrl(path), {
      method: 'PATCH', headers: headers(), body: JSON.stringify(body),
    }))).data
  },
  async del(path: string): Promise<void> {
    const res = await fetch(apiUrl(path), { method: 'DELETE', headers: headers(false) })
    if (!res.ok && res.status !== 204) await parse(res)
  },
  async postForm<T>(path: string, form: FormData): Promise<T> {
    return (await parse<Envelope<T>>(await fetch(apiUrl(path), {
      method: 'POST', headers: headers(false), body: form,
    }))).data
  },
}

export type Usuario = { id: number; nome: string; email: string; criado_em?: number; ultimo_acesso?: number }
export type Caderno = {
  id: number; titulo: string; hash: string; criado_em: number; atualizado_em?: number
  melhor_nota?: number | null; perguntas?: number
  fontes?: { arquivo: string; paginas: number }[]
  total_paginas?: number; restantes?: number; do_cache?: boolean
}
export type Estatisticas = {
  cadernos: number; quizzes: number; media: number | null; perguntas: number; cadernos_hoje?: number
}
export type Configuracao = {
  modo: string; usar_api: boolean
  limites: {
    max_paginas_por_jornada: number; max_tamanho_arquivo_mb: number
    perguntas_chat: number; perguntas_quiz: number; jornadas_por_dia: number
  }
}
