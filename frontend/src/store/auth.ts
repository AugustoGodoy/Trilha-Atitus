import { create } from 'zustand'
import { api, getToken, setToken, type Usuario } from '../api/client'

type AuthState = {
  usuario: Usuario | null
  ready: boolean
  restaurar: () => Promise<void>
  login: (email: string, senha: string) => Promise<void>
  registrar: (nome: string, email: string, senha: string) => Promise<void>
  sair: () => Promise<void>
}

export const useAuth = create<AuthState>((set) => ({
  usuario: null,
  ready: false,
  async restaurar() {
    const token = getToken()
    if (!token) {
      set({ usuario: null, ready: true })
      return
    }
    const tentativas = 3
    for (let i = 0; i < tentativas; i++) {
      try {
        const usuario = await api.get<Usuario>('/v1/sessoes/atual')
        set({ usuario, ready: true })
        return
      } catch (e) {
        const status = e && typeof e === 'object' && 'status' in e ? Number((e as { status: number }).status) : 0
        // Sessão inválida → limpa token. Rede/timeout → tenta de novo (cold start Railway).
        if (status === 401 || status === 403) {
          setToken(null)
          set({ usuario: null, ready: true })
          return
        }
        if (i < tentativas - 1) {
          await new Promise((r) => setTimeout(r, 1500 * (i + 1)))
          continue
        }
        // Mantém o token; usuário vê login só se a API continuar fora
        set({ usuario: null, ready: true })
      }
    }
  },
  async login(email, senha) {
    const data = await api.post<{ token: string; usuario: Usuario }>('/v1/sessoes', { email, senha })
    setToken(data.token)
    set({ usuario: data.usuario })
  },
  async registrar(nome, email, senha) {
    await api.post('/v1/usuarios', { nome, email, senha })
    const data = await api.post<{ token: string; usuario: Usuario }>('/v1/sessoes', { email, senha })
    setToken(data.token)
    set({ usuario: data.usuario })
  },
  async sair() {
    try { await api.del('/v1/sessoes/atual') } catch { /* ignore */ }
    setToken(null)
    set({ usuario: null })
  },
}))
