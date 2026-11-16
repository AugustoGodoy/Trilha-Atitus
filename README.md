# Trilha Atitus

Plataforma de estudo guiado com tutor inteligente. O aluno envia os slides ou PDFs da aula e segue uma jornada curta e guiada: **resumo, mapa mental, quiz e dúvidas**, sempre com citação de arquivo e página/slide.

Projeto do Grupo 4 da Universidade Atitus. A especificação, com o status de cada requisito, está em [`docs/specs.md`](docs/specs.md) (versão em PDF: [`docs/specs.pdf`](docs/specs.pdf)).

## Sumário

1. [Funcionalidades](#1-funcionalidades)
2. [Como executar](#2-como-executar)
3. [Configuração e modo de geração](#3-configuração-e-modo-de-geração)
4. [Dados e segurança](#4-dados-e-segurança)
5. [Estrutura do projeto](#5-estrutura-do-projeto)
6. [Requisitos implementados](#6-requisitos-implementados)
7. [Decisões e limitações](#7-decisões-e-limitações)

## 1. Funcionalidades

- **Login e cadastro** com e-mail e senha. Cada aluno vê apenas os próprios cadernos.
- **Cadernos**: cada material enviado (PDF ou PPTX) vira um caderno salvo na conta, com histórico de conversa e notas de quiz.
- **Estúdio** com quatro visões, na ordem que o aluno preferir:
  - **Dúvidas**: chat com limite de 3 perguntas por caderno; responde só com base no material, cita arquivo e página e recusa quando não há base.
  - **Resumo**: tópicos com termos-chave destacados e fonte.
  - **Mapa mental**: gerado em JSON, renderizado como grafo e editável (adicionar e remover nós).
  - **Quiz**: 5 questões com gabarito, justificativa, fonte e correção automática.
- **Painel inicial** com saudação pelo nome, estatísticas (cadernos, quizzes, nota média, perguntas ao tutor) e envio de novo material.
- **Custo controlado**: limites de páginas, tamanho e jornadas por dia validados antes de qualquer processamento, geração única e cache por hash.

## 2. Como executar

Requer Python 3.12 ou superior.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py          # http://localhost:8765
pytest                        # testes automatizados
```

No primeiro acesso, use a aba **Criar conta** da tela de login.

## 3. Configuração e modo de geração

Modelo, URL, preços e todos os limites ficam em [`config.toml`](config.toml).

| Limite | Valor |
|---|---|
| Páginas/slides por jornada | 40 |
| Tamanho por arquivo | 20 MB |
| Perguntas no chat | 3 por caderno |
| Questões no quiz | 5 |
| Jornadas por dia | 20 por usuário |

**Sem chave de API**, o app roda em **modo offline**: a geração é extrativa (trechos do próprio material) e tem custo zero. Serve para demonstração e testes, mas o resumo, o mapa e o quiz são básicos.

**Com chave de API**, o app usa um LLM barato compatível com a API da OpenAI (padrão: `gpt-4o-mini`):

```bash
export OPENAI_API_KEY=...     # fica só no servidor; o aluno nunca vê a chave
```

## 4. Dados e segurança

- **Banco SQLite** em `data/app.sqlite` (pasta fora do Git): `usuarios`, `sessoes`, `tentativas_login`, `cadernos`, `mensagens` e `resultados_quiz`.
- **Cache de conteúdo gerado** em `data/cache.sqlite`, por hash dos arquivos, compartilhado entre usuários.
- **Senhas** com scrypt e salt aleatório; a senha nunca é armazenada.
- **Sessão** por token: só o hash fica no banco, com validade de 7 dias.
- **Bloqueio temporário** após 5 falhas de login em 10 minutos; a mensagem de erro não revela se o e-mail existe.
- **Texto de usuários e arquivos** é escapado antes de entrar em HTML.
- **Aviso permanente** de que o app é ferramenta de apoio e não substitui o professor nem o material oficial da disciplina.

## 5. Estrutura do projeto

```
app.py              Ponto de entrada: autenticação, barra lateral e roteamento
estudo_guiado/      Regras de negócio
  extracao.py, chunking.py   Leitura de PDF/PPTX e divisão em trechos
  retrieval.py               Recuperação por BM25
  geracao.py, llm.py         Resumo, mapa, quiz e chat (offline ou via API)
  jornada.py, cache.py       Orquestração, limites e cache por hash
  banco.py, seguranca.py     Usuários, cadernos, sessões e senhas
interface/          Telas Streamlit (login, início, caderno) e tema visual
assets/             Logo e ícone da Universidade Atitus
docs/               Especificação do projeto (specs.md e specs.pdf)
tests/              Testes automatizados
config.toml         Limites, modelo, recuperação, cache e caminho dos bancos
```

## 6. Requisitos implementados

| Spec | Implementação |
|---|---|
| RF01-03 | `extracao.py`, `chunking.py`: PDF (PyMuPDF) e PPTX (python-pptx), texto por página/slide, trechos com sobreposição |
| RF02 / critério 4 | `Servico.validar`: páginas, MB por arquivo e jornadas por dia checados antes de qualquer processamento ou chamada ao LLM |
| RF04 | Resumo por tópicos com fonte; termos-chave só se existirem no texto; destaque aplicado por código |
| RF05-06 | Mapa mental em JSON renderizado com Graphviz; adicionar e remover nós; ver o trecho de cada nó |
| RF07-08 | Quiz com gabarito, justificativa, fonte e nível; correção por código |
| RF09-10 | Chat com 3 perguntas, contador, citação e recusa quando não há base (score mínimo de recuperação) |
| RF11 | Cache SQLite por hash dos arquivos; reabrir um caderno não chama o LLM |
| RF12 | Tabela `uso`: tokens e custo estimado (R$) por etapa |
| RF13 | Aviso permanente de ferramenta de apoio |

O status completo de todos os requisitos (RF01 a RF21 e RNF01 a RNF08) está em [`docs/specs.md`](docs/specs.md).

## 7. Decisões e limitações

- **Recuperação**: BM25 local, sem download de modelos, atrás da interface `IndiceBM25.buscar`. Trocar por embeddings multilíngues e ChromaDB é uma substituição isolada em `retrieval.py`.
- **Mapa mental**: o trecho de um nó é aberto por seletor, não por clique direto no grafo.
- **Pergunta recusada** não consome o limite de 3; o cache de conteúdo é compartilhado entre usuários.
- **Modo offline**: o quiz é de completar lacunas (nível "lembrar"); níveis variados de Bloom só com LLM.
- **Pendências**: aviso de privacidade e consentimento, exclusão de conta, avaliação quantitativa (RAGAs, Acerto@k, MRR), abrir o PDF na página citada e PDFs escaneados.
