import { useEffect, useState } from 'react'
import { Outlet } from 'react-router-dom'
import { api, type Caderno } from '../api/client'
import { AVISO } from '../lib/format'
import { Sidebar } from './Sidebar'

export type OutletCtx = {
  cadernos: Caderno[]
  recarregarCadernos: () => Promise<void>
  setFontesSidebar: (f: { arquivo: string; paginas: number }[] | undefined) => void
  modoCriar: boolean
  setModoCriar: (v: boolean) => void
  excluirCaderno: (c: Caderno) => Promise<void>
}

export function Layout() {
  const [cadernos, setCadernos] = useState<Caderno[]>([])
  const [fontes, setFontes] = useState<{ arquivo: string; paginas: number }[] | undefined>()
  const [modoCriar, setModoCriar] = useState(false)

  async function recarregarCadernos() {
    const lista = await api.get<Caderno[]>('/v1/cadernos?limit=50&offset=0')
    setCadernos(lista)
  }

  async function excluirCaderno(c: Caderno) {
    if (!confirm(`Excluir o caderno "${c.titulo}"?`)) return
    await api.del(`/v1/cadernos/${c.id}`)
    await recarregarCadernos()
  }

  useEffect(() => {
    recarregarCadernos().catch(() => setCadernos([]))
  }, [])

  const ctx: OutletCtx = {
    cadernos,
    recarregarCadernos,
    setFontesSidebar: setFontes,
    modoCriar,
    setModoCriar,
    excluirCaderno,
  }

  return (
    <div className="app-shell">
      <Sidebar
        cadernos={cadernos}
        fontes={fontes}
        onNovo={() => setModoCriar(true)}
        onExcluir={excluirCaderno}
      />
      <div className="main" style={{ display: 'flex', flexDirection: 'column' }}>
        <div style={{ flex: 1 }}>
          <Outlet context={ctx} />
        </div>
        <p className="footer-aviso">{AVISO}</p>
      </div>
    </div>
  )
}
