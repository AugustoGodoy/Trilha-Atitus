export function iniciais(nome: string): string {
  const partes = nome.trim().split(/\s+/)
  if (!partes[0]) return '?'
  return (partes[0][0] + (partes.length > 1 ? partes[partes.length - 1][0] : '')).toUpperCase()
}

export function primeiroNome(nome: string): string {
  return nome.trim().split(/\s+/)[0] || nome
}

export function saudacaoDoDia(d = new Date()): string {
  const h = d.getHours()
  return h >= 5 && h < 12 ? 'Bom dia' : h >= 12 && h < 18 ? 'Boa tarde' : 'Boa noite'
}

export function dataCurta(ts: number): string {
  return new Date(ts * 1000).toLocaleDateString('pt-BR')
}

/** Converte **negrito** escapando HTML. */
export function negritoHtml(texto: string): string {
  const esc = texto
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
  return esc.replace(/\*\*(.+?)\*\*/g, '<b>$1</b>')
}

export const AVISO =
  'Ferramenta de apoio ao estudo. Não substitui o professor nem o material oficial da disciplina.'
