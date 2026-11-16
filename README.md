# Estudo Guiado

MVP da **Plataforma de Estudo Guiado com Tutor Inteligente** (spec do Grupo 4). O aluno envia PDF/PPTX e segue uma jornada curta: **resumo → mapa mental → quiz → dúvidas (3 perguntas)**, sempre com citação de arquivo e página/slide.

A especificação do projeto, alinhada ao que está implementado (com status por requisito), está em [`docs/specs.md`](docs/specs.md) (versão em PDF: `docs/specs.pdf`).

## Executar

```bash
pip install -r requirements.txt
streamlit run app.py          # http://localhost:8765
pytest                        # testes
```

## Interface, login e dados do usuário

Interface escura inspirada no NotebookLM, com a marca da Universidade Atitus (`assets/`): **Fontes** à esquerda, conversa com o tutor no centro e **Estúdio** (Dúvidas, Resumo, Mapa mental, Quiz) à direita.

* **Login obrigatório**: criação de conta e entrada com e-mail/senha. Senhas com scrypt + salt; sessão por token (só o hash fica no banco, validade de 7 dias, sobrevive ao recarregar a página); bloqueio temporário após 5 falhas seguidas.
* **Personalizado por usuário**: saudação pelo nome, cadernos próprios, histórico de chat, notas de cada quiz e estatísticas. Cada usuário só enxerga os próprios cadernos. O limite de jornadas por dia é **por usuário**.
* **Banco SQLite** em `data/app.sqlite` (`[banco]` em `config.toml`): `usuarios`, `sessoes`, `tentativas_login`, `cadernos`, `mensagens`, `resultados_quiz`. O conteúdo gerado continua no cache por hash (`data/cache.sqlite`), compartilhado entre usuários.
* Código: `estudo_guiado/` (regras, banco, segurança) e `interface/` (telas Streamlit); `app.py` só faz autenticação e roteamento.

Sem chave de API o app roda em **modo offline** (geração extrativa, custo zero), útil para demo e testes. Para usar um LLM barato via API compatível com OpenAI:

```bash
export OPENAI_API_KEY=...     # fica só no servidor; o aluno nunca vê a chave
```

Modelo, URL, preços e todos os limites ficam em [`config.toml`](config.toml) (RNF06).

## O que está implementado

| Spec | Implementação |
|---|---|
| RF01-03 | `extracao.py`, `chunking.py`: PDF (PyMuPDF) e PPTX (python-pptx), texto por página/slide, trechos com sobreposição, imagens extraídas por código |
| RF02 / critério 4 | `Servico.validar`: páginas, MB por arquivo e jornadas/dia checados antes de qualquer processamento ou chamada ao LLM |
| RF04 | Resumo por tópicos com fonte; termos-chave só se existirem no texto; destaque aplicado por código |
| RF05-06 | Mapa mental em JSON renderizado com Graphviz; adicionar/remover nós no front-end; ver trecho do nó |
| RF07-08 | Quiz com gabarito, justificativa, fonte e nível; correção por código |
| RF09-10 | Chat com 3 perguntas, contador, citação e recusa quando não há base (score mínimo de recuperação) |
| RF11 | Cache SQLite por hash dos arquivos; reabrir não chama o LLM |
| RF12 | Tabela `uso`: tokens e custo estimado (R$) por etapa |
| RF13 | Aviso permanente de ferramenta de apoio |

## Decisões e diferenças em relação ao spec

- **Recuperação**: BM25 local, sem download de modelos, atrás da interface `IndiceBM25.buscar`. Trocar por embeddings multilíngues + ChromaDB é uma substituição isolada em `retrieval.py`.
- **Interface**: Streamlit; o mapa mental não é clicável diretamente, o trecho é aberto por seletor de nó.
- **Decisões em aberto** (valores em `config.toml`): pergunta recusada **não** consome o limite; cache **compartilhado**, guardando conteúdo gerado e os trechos de texto (necessários para exibir fontes).
- **Modo offline**: quiz de completar lacunas (nível "lembrar"); níveis variados de Bloom só com LLM.
- **Fora do MVP**: avaliação quantitativa (RAGAs, Acerto@k, MRR), abrir PDF na página citada, PDFs escaneados.
