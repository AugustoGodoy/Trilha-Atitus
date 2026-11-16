import { Link, useNavigate, useParams } from 'react-router-dom'
import type { Caderno } from '../api/client'
import { iniciais } from '../lib/format'
import { useAuth } from '../store/auth'
import { useTheme } from '../store/theme'

type Props = {
  cadernos: Caderno[]
  fontes?: { arquivo: string; paginas: number }[]
  onNovo: () => void
  onExcluir: (c: Caderno) => Promise<void>
}

export function Sidebar({ cadernos, fontes, onNovo, onExcluir }: Props) {
  const { usuario, sair } = useAuth()
  const { tema, alternar } = useTheme()
  const nav = useNavigate()
  const { id } = useParams()
  const ativo = id ? Number(id) : null

  async function onSair() {
    await sair()
    nav('/login')
  }

  function novo() {
    onNovo()
    nav('/')
  }

  return (
    <aside className="sidebar">
      <div className="logo-wrap">
        <img src="/atitus_logo.png" alt="Universidade Atitus" />
      </div>
      <button className="btn primary" type="button" onClick={novo}>+ Novo caderno</button>

      {fontes && fontes.length > 0 && (
        <>
          <div className="rotulo-secao">Fontes</div>
          {fontes.map((f) => {
            const ext = f.arquivo.split('.').pop()?.toLowerCase() || 'pdf'
            return (
              <div className="fonte" key={f.arquivo}>
                <span className={`tipo ${ext === 'pptx' ? 'pptx' : 'pdf'}`}>{ext.toUpperCase()}</span>
                <span className="nome" title={f.arquivo}>{f.arquivo}</span>
                <span className="pg">{f.paginas} pág.</span>
              </div>
            )
          })}
        </>
      )}

      <div className="rotulo-secao">Cadernos</div>
      {cadernos.length === 0 ? (
        <p className="sub" style={{ fontSize: '0.82rem', margin: '0.2rem 0.4rem' }}>
          Nenhum caderno ainda. Crie o primeiro com o botão acima.
        </p>
      ) : (
        cadernos.slice(0, 30).map((c) => (
          <div className="nav-item" key={c.id}>
            <Link to={`/cadernos/${c.id}`} style={{ textDecoration: 'none', flex: 1, minWidth: 0 }}>
              <button className={`btn nav ${ativo === c.id ? 'active' : ''}`} type="button">
                <span className="titulo" title={c.titulo}>{c.titulo}</span>
              </button>
            </Link>
            <button
              className="btn icon"
              type="button"
              title="Excluir"
              onClick={() => onExcluir(c)}
            >
              ×
            </button>
          </div>
        ))
      )}

      <div style={{ marginTop: 'auto' }}>
        <div className="rotulo-secao">Conta</div>
        {usuario && (
          <div className="usuario">
            <div className="avatar">{iniciais(usuario.nome)}</div>
            <div>
              <div className="nome">{usuario.nome}</div>
              <div className="email">{usuario.email}</div>
            </div>
          </div>
        )}
        <button className="btn tema" type="button" onClick={alternar}>
          {tema === 'dark' ? '☀ Modo claro' : '☾ Modo escuro'}
        </button>
        <button className="btn" style={{ marginTop: '0.45rem' }} type="button" onClick={onSair}>Sair</button>
      </div>
    </aside>
  )
}
