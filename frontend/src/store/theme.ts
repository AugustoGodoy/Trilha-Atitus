import { create } from 'zustand'

export type Tema = 'dark' | 'light'

const KEY = 'trilha_tema'

function aplicar(tema: Tema) {
  document.documentElement.setAttribute('data-theme', tema)
}

function ler(): Tema {
  const salvo = localStorage.getItem(KEY)
  return salvo === 'light' ? 'light' : 'dark'
}

aplicar(ler())

type ThemeState = {
  tema: Tema
  alternar: () => void
  definir: (t: Tema) => void
}

export const useTheme = create<ThemeState>((set, get) => ({
  tema: ler(),
  definir(t) {
    localStorage.setItem(KEY, t)
    aplicar(t)
    set({ tema: t })
  },
  alternar() {
    get().definir(get().tema === 'dark' ? 'light' : 'dark')
  },
}))
