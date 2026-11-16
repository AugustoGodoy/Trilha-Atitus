# specs.md: Plataforma de Estudo Guiado com Tutor Inteligente

Documento de especificação do protótipo (Grupo 4), **versão 1.1**. Esta versão foi alinhada ao protótipo implementado neste repositório: onde a versão 1.0 descrevia uma intenção, esta descreve o que existe e marca o que ainda não foi feito. Valores marcados com *(a definir)* continuam dependendo de confirmação do grupo.

**Legenda de status:** **Implementado** (existe no protótipo e foi verificado), **Parcial** (existe com ressalvas descritas) e **Pendente** (previsto, ainda não implementado).

## Histórico de revisões

| Versão | Data | Mudanças |
|---|---|---|
| 1.0 | n/d | Pré-projeto do Grupo 4 e decisões das discussões posteriores. |
| 1.1 | 16/11/2026 | Alinhamento ao protótipo: conta de usuário e login, cadernos persistentes por usuário, interface no estilo NotebookLM com a marca da Universidade Atitus, navegação livre entre as etapas, stack real (BM25 e SQLite), limite de jornadas por usuário, política de dados atualizada, decisões fechadas e status por requisito. Correções: contagem de etapas (eram 5, não 4) e erros de texto. |

## 1. Visão geral

### 1.1 O que é

Uma aplicação web com conta de usuário que recebe os slides ou PDFs de uma aula e conduz o aluno por uma jornada curta e guiada de estudo rápido, do conteúdo bruto até a verificação do que foi aprendido. Todo o conteúdo gerado é fundamentado no material enviado, com citação de arquivo e página/slide. Cada material enviado vira um **caderno** do usuário, que guarda o conteúdo gerado, o histórico de dúvidas e as notas dos quizzes.

### 1.2 Problema

Alunos que precisam estudar um conteúdo específico em pouco tempo (por exemplo, véspera de prova) acabam lendo slides longos sem método. Ferramentas como NotebookLM, ChatPDF e Open Notebook respondem perguntas sobre documentos, mas não conduzem o estudo: o aluno precisa saber o que perguntar.

### 1.3 Diferencial

1. Jornada guiada em etapas, do simples ao profundo (resumo, mapa mental, quiz, dúvidas), em vez de um chat aberto.
2. Fundamentação e recusa: toda saída cita a fonte, e o sistema informa quando o assunto não está no material, em vez de inventar.
3. Custo controlado por design: limites claros de envio e de interação, geração única com cache e uso de modelos baratos, de modo que o produto seja viável para um usuário final leigo sem que ele precise de chave de API própria. Há também um modo offline, de custo zero.
4. Qualidade medida: avaliação quantitativa da recuperação, da fidelidade das respostas, da correção dos gabaritos e do custo por jornada. **Status: Pendente** (seção 9).
5. Experiência personalizada: conta própria, saudação pelo nome, cadernos salvos, histórico de dúvidas, notas e estatísticas de uso.

### 1.4 Fora do escopo desta versão

- Modo Feynman (decidido não implementar).
- Bot no Telegram, podcast, exportação para Obsidian, cruzamento entre materiais, revisão espaçada.
- PDFs escaneados (sem texto selecionável).

Ficam como extensões futuras (seção 13).

## 2. Público-alvo

- **Usuário final:** estudante, leigo em tecnologia. Precisa criar uma conta na plataforma (nome, e-mail e senha), mas não precisa criar chave de API, instalar nada ou entender conceitos de IA.
- **Contexto de uso:** estudo rápido de uma aula ou tópico específico.

## 3. A jornada do aluno

### 3.1 Acesso e área do usuário

1. **Login obrigatório.** Ao abrir a aplicação, o usuário cria uma conta ou entra com e-mail e senha. A sessão sobrevive ao recarregamento da página e expira em 7 dias; o botão "Sair" encerra a sessão.
2. **Início.** Mostra a saudação pelo nome ("Bom dia, Maria"), estatísticas do usuário (cadernos, quizzes feitos, nota média, perguntas ao tutor), a lista de cadernos salvos e o painel "Novo caderno".
3. **Caderno.** Tela com três áreas, no estilo NotebookLM:
   - **Fontes** (barra lateral): arquivos do caderno, com número de páginas, e a lista "Meus cadernos".
   - **Centro:** título do caderno (renomeável) e a visão escolhida.
   - **Estúdio** (à direita): atalhos para Dúvidas, Resumo, Mapa mental e Quiz, mais o progresso (perguntas restantes, última nota, melhor nota e tentativas) e o custo estimado do caderno.
4. Cada usuário só enxerga os próprios cadernos. É possível renomear e excluir um caderno.
5. Um aviso permanente informa que a ferramenta é de apoio ao estudo e não substitui o professor.

### 3.2 Etapas da jornada

A jornada tem **5 etapas** (0 a 4). Depois do envio, as quatro visões ficam disponíveis no Estúdio e o aluno escolhe a ordem; a ordem recomendada é a do fluxo abaixo. *Decisão da versão 1.1: a navegação livre substitui o avanço sequencial obrigatório da versão 1.0.*

#### Etapa 0: Envio do material

- O aluno envia slides (PPTX) e/ou PDFs com texto selecionável.
- O sistema valida os limites (seção 4) antes de processar.
- O sistema extrai o texto por página/slide, limpa e divide em trechos de cerca de 450 palavras (faixa de 500 a 800 tokens), com sobreposição de 60 palavras, sem cruzar fronteiras de página. Cada trecho guarda arquivo e página/slide, e todos são indexados em um índice BM25 local.
- Imagens e diagramas (até 3 por página) são extraídos por código, sem IA, e associados à página/slide de origem.

#### Etapa 1: Resumo do conteúdo

- Resumo organizado por tópicos, em linguagem simples e didática (com LLM: 6 a 10 tópicos).
- Lista de termos-chave para memorizar (até 10), com definição de uma linha.
- Cada tópico cita arquivo e página/slide de origem.
- Os termos-chave aparecem destacados. O destaque é aplicado por código, e os termos devem existir no texto original; termos inventados são descartados.

#### Etapa 2: Mapa mental

- Mapa gerado a partir dos conceitos e relações do material (com LLM: até 15 nós).
- A IA devolve apenas a estrutura em JSON (nós e relações), e a interface renderiza o mapa com Graphviz, em tema escuro. Relações hierárquicas ("contém") são linhas contínuas; relações laterais ("relaciona-se") são tracejadas.
- Cada nó indica a página/slide de origem. Ao selecionar um nó em uma lista, a interface mostra o trecho correspondente e até 2 imagens da página.
- O usuário pode adicionar e remover nós. A edição é feita no front-end, sem chamar IA, e vale apenas para a sessão atual (não é gravada).

#### Etapa 3: Quiz

- Quiz de múltipla escolha com 5 questões, gerado uma única vez.
- Cada questão tem enunciado, 4 alternativas, gabarito, justificativa, trecho-fonte e nível cognitivo (lembrar, compreender ou aplicar, baseados na taxonomia de Bloom revisada, Anderson e Krathwohl, 2001). Níveis variados dependem do LLM; no modo offline todas as questões são de completar lacuna, nível "lembrar".
- A correção é feita pela interface (comparação com o gabarito), sem custo de IA.
- Ao final, mostra a nota (0 a 10) e, para cada erro, a justificativa e a fonte. O resultado é gravado no histórico do caderno e o aluno pode refazer o quiz.

#### Etapa 4: Dúvidas (chat limitado)

- O aluno pode fazer no máximo 3 perguntas por caderno. Cada resposta é gerada com a recuperação de 4 trechos do material e cita a origem.
- A interface mostra um contador visível ("Perguntas restantes: 2 de 3").
- Se não houver base no material (score de recuperação abaixo do mínimo), o sistema informa que o assunto não é coberto. Essa recusa **não** consome uma das 3 perguntas (decisão fechada).
- Antes da primeira pergunta, a interface sugere até 3 perguntas baseadas nos termos-chave, apenas as que a recuperação consegue responder.
- Ao esgotar as 3 perguntas, a entrada é desabilitada e a jornada é concluída. O histórico de perguntas e respostas fica salvo no caderno.

#### Resumo do fluxo

Login → Envio → Resumo / Mapa mental / Quiz / Dúvidas (ordem livre) → Fim (ao esgotar as 3 perguntas).

## 4. Limites de uso (controle de tokens)

Para tornar o custo previsível, o sistema impõe limites. Os limites de uso e os parâmetros de modelo e recuperação ficam em `config.toml`.

| Limite | Valor atual | Observação |
|---|---|---|
| Slides/páginas por jornada | 40 | Soma de todos os arquivos enviados no mesmo caderno |
| Tamanho máximo por arquivo | 20 MB | Validação antes do processamento |
| Perguntas no chat | 3 | Decisão fechada |
| Perguntas no quiz | 5 | Gerado uma única vez |
| Jornadas por usuário por dia | 20 | Conta cadernos novos criados no dia; reabrir um caderno não conta |
| Pergunta recusada consome o limite? | Não | `recusa_consome_pergunta = false` |

Limites de segurança de conta, fixados no código (`estudo_guiado/banco.py` e `seguranca.py`): bloqueio temporário após 5 falhas seguidas de login em 10 minutos, senha com no mínimo 8 caracteres combinando letras e números, e sessão de 7 dias.

**Comportamento ao exceder o limite:** a interface avisa antes de processar e orienta o usuário (por exemplo, "O material tem 42 páginas/slides; o máximo é 40. Selecione o trecho da aula que quer estudar e envie novamente."). Nada é enviado ao LLM antes dessa validação.

## 5. Estratégia de economia de tokens

| # | Estratégia | Status |
|---|---|---|
| 1 | **Gerar uma vez e reaproveitar.** Resumo, termos-chave, mapa mental e quiz são gerados no processamento e guardados em cache. Reabrir um caderno não gasta tokens. | Implementado |
| 2 | **Cache compartilhado por hash.** O hash combina o conteúdo dos arquivos com o modo de geração e os parâmetros de quiz e de divisão em trechos. O nome do arquivo não entra no hash. | Implementado |
| 3 | **Modelo barato para quase tudo** (padrão: `gpt-4o-mini` via API compatível com OpenAI). Usar um modelo mais forte apenas se a checagem de qualidade falhar. | Parcial (não há checagem de qualidade nem modelo de reserva) |
| 4 | **Código no lugar de IA onde possível:** destaque de termos, correção do quiz, extração de imagens, renderização do mapa, contador de perguntas e validação das saídas do modelo. | Implementado |
| 5 | **Prompts enxutos:** instruções fixas no início, recuperação de poucos trechos e saída em JSON compacto. | Implementado |
| 6 | **Resumo hierárquico** para materiais longos (acima de 9.000 palavras): resume por seção, em grupos de cerca de 2.500 palavras, e depois consolida. | Implementado |
| 7 | **Chave de API no servidor**, lida da variável de ambiente `OPENAI_API_KEY`. O usuário nunca lida com chaves. | Implementado |
| 8 | **Modo offline** (extrativo, sem custo): usado automaticamente quando não há chave de API. | Implementado |

## 6. Arquitetura

### 6.1 Componentes

| Camada | Tecnologia no protótipo | Observação em relação à versão 1.0 |
|---|---|---|
| Extração de texto e imagens | Python, PyMuPDF, python-pptx | Igual ao previsto |
| Orquestração | Código próprio (`jornada.py`) | Não usa LlamaIndex nem LangChain |
| Recuperação | BM25 local (`retrieval.py`), atrás da interface `IndiceBM25.buscar` | Substitui embeddings multilíngues e ChromaDB; a troca é isolada nesse módulo |
| LLM de geração | API compatível com OpenAI (cliente próprio, sem dependências extras); padrão `gpt-4o-mini` | Modelo e preços em `config.toml`; testes comparativos de modelos em português ainda não foram feitos |
| Cache de conteúdo gerado | SQLite (`data/cache.sqlite`) e imagens em disco, indexados por hash | Igual ao previsto |
| Banco da aplicação | SQLite (`data/app.sqlite`) | Novo: usuários, sessões, cadernos, chat e resultados de quiz |
| Interface | Streamlit, com tema escuro próprio (CSS) e a marca da Universidade Atitus | Layout em três áreas, no estilo NotebookLM |
| Avaliação | Não implementada | Previsto: RAGAs e scripts próprios |
| Versionamento e documentação | GitHub | Igual ao previsto |

### 6.2 Fluxo de dados

1. Login → upload → validação de limites (incluindo o limite diário do usuário) → cálculo do hash.
2. Se o hash já existe em cache, carrega o conteúdo pronto. Caso contrário: extração → divisão em trechos → índice BM25.
3. Geração única de resumo, termos-chave, grafo de conceitos (JSON) e quiz (JSON), com armazenamento em cache e registro de tokens e custo por etapa.
4. O caderno é registrado para o usuário (um caderno por usuário e material). A interface apresenta as etapas lendo o conteúdo do cache.
5. No chat, cada pergunta aciona recuperação + geração (ou resposta extrativa no modo offline), com decremento do contador. A pergunta e a resposta são gravadas no caderno.

### 6.3 Formatos de saída do LLM

Toda saída passa por validação em código antes de ser usada: fontes inexistentes são trocadas pela fonte mais próxima, termos ausentes do texto são descartados, ids duplicados e relações inválidas do mapa são removidos, e questões sem 4 alternativas ou sem gabarito válido são descartadas. As alternativas são guardadas sem o prefixo da letra, e o nível inválido vira "compreender".

Quiz (JSON):

```json
{
  "questoes": [
    {
      "enunciado": "...",
      "alternativas": ["A ...", "B ...", "C ...", "D ..."],
      "gabarito": "B",
      "justificativa": "...",
      "fonte": {"arquivo": "aula3.pdf", "pagina": 12},
      "nivel": "compreender"
    }
  ]
}
```

Mapa mental (JSON):

```json
{
  "nos": [{"id": "n1", "rotulo": "...", "fonte": {"arquivo": "aula3.pdf", "pagina": 4}}],
  "relacoes": [{"de": "n1", "para": "n2", "tipo": "contém"}]
}
```

### 6.4 Organização do código

| Caminho | Conteúdo |
|---|---|
| `app.py` | Ponto de entrada: autenticação, barra lateral e roteamento entre telas |
| `estudo_guiado/` | Regras de negócio: `extracao`, `chunking`, `retrieval`, `llm`, `geracao`, `cache`, `jornada`, `banco`, `seguranca`, `config` |
| `interface/` | Telas Streamlit: `estilo`, `login`, `home`, `caderno`, `sessao` |
| `assets/` | Logo e ícone da Universidade Atitus |
| `config.toml` | Limites, modelo, recuperação, cache e caminho dos bancos |
| `tests/` | Testes automatizados (pytest) |

### 6.5 Modelo de dados da aplicação (`data/app.sqlite`)

| Tabela | Conteúdo |
|---|---|
| `usuarios` | Nome, e-mail (único), hash da senha, datas de criação e do último acesso |
| `sessoes` | Hash do token de sessão, usuário e validade |
| `tentativas_login` | E-mail, data e sucesso de cada tentativa (usada no bloqueio temporário) |
| `cadernos` | Usuário, título, hash do material e datas; único por usuário e material |
| `mensagens` | Perguntas e respostas do chat, fontes, indicação de recusa e se consumiu o limite |
| `resultados_quiz` | Nota, acertos e total de cada tentativa de quiz |

### 6.6 Segurança de conta

- Senhas guardadas com **scrypt** (N=2^14, r=8, p=1) e salt aleatório de 16 bytes por usuário; a senha nunca é armazenada.
- Token de sessão aleatório de 32 bytes; o banco guarda apenas o hash SHA-256 do token. O token viaja na URL (`?s=...`) para sobreviver ao recarregamento da página.
- Mensagem de erro de login genérica ("E-mail ou senha incorretos"), que não revela se o e-mail existe, e bloqueio temporário após 5 falhas seguidas.
- Todo texto vindo do usuário ou dos arquivos enviados é escapado antes de entrar em HTML.

## 7. Requisitos funcionais

| ID | Requisito | Status |
|---|---|---|
| RF01 | O sistema deve aceitar upload de PDF e PPTX com texto selecionável. | Implementado |
| RF02 | O sistema deve validar o limite de slides/páginas e o tamanho antes de processar. | Implementado |
| RF03 | O sistema deve extrair, dividir e indexar o conteúdo com metadados de arquivo e página/slide. | Implementado (índice BM25, não vetorial) |
| RF04 | O sistema deve gerar um resumo por tópicos com termos-chave destacados e citação de fonte. | Implementado |
| RF05 | O sistema deve gerar e renderizar um mapa mental a partir de JSON. | Implementado |
| RF06 | O usuário deve poder adicionar e remover nós do mapa mental. | Implementado (a edição vale só para a sessão) |
| RF07 | O sistema deve gerar um quiz de múltipla escolha com gabarito, justificativa e fonte. | Implementado |
| RF08 | A interface deve corrigir o quiz sem chamar o LLM. | Implementado |
| RF09 | O chat deve permitir no máximo 3 perguntas por jornada, com contador visível. | Implementado |
| RF10 | Cada resposta do chat deve citar a origem e recusar quando não houver base no material. | Implementado |
| RF11 | O sistema deve guardar em cache o conteúdo gerado e reaproveitá-lo. | Implementado |
| RF12 | O sistema deve registrar tokens e custo estimado por etapa e por jornada. | Implementado (o registro é por conteúdo/hash, compartilhado entre usuários que enviam o mesmo material) |
| RF13 | O sistema deve exibir aviso de que é ferramenta de apoio e não substitui o professor. | Implementado (aviso permanente no rodapé e na tela de login) |
| RF14 | O sistema deve permitir criar conta e entrar com e-mail e senha. | Implementado |
| RF15 | O sistema deve manter a sessão ao recarregar a página e permitir sair. | Implementado |
| RF16 | O sistema deve guardar, por usuário, os cadernos, o histórico de dúvidas e as notas dos quizzes, sem expor dados de um usuário a outro. | Implementado |
| RF17 | O usuário deve poder reabrir, renomear e excluir seus cadernos. | Implementado |
| RF18 | O sistema deve exibir estatísticas do usuário (cadernos, quizzes, nota média, perguntas). | Implementado |
| RF19 | O limite de jornadas por período deve valer por usuário. | Implementado (por dia) |
| RF20 | O usuário deve poder excluir a própria conta e os dados pessoais associados. | Pendente |
| RF21 | O cadastro deve exibir aviso de privacidade e coletar o consentimento do usuário. | Pendente |

## 8. Requisitos não funcionais

| ID | Requisito | Status |
|---|---|---|
| RNF01 | Usabilidade: usuário leigo conclui a jornada sem configurar chaves ou ferramentas. | Implementado (não validado com usuários reais) |
| RNF02 | Custo: custo médio por jornada completa mensurado e reportado (meta a definir após medição). | Parcial (o registro existe; ainda não há medição com LLM real nem relatório) |
| RNF03 | Fidelidade: nenhuma afirmação sem fonte; destaques somente de termos existentes no texto. | Implementado |
| RNF04 | Idioma: conteúdo e interface em português. | Implementado |
| RNF05 | Reprodutibilidade: código aberto, com instruções de instalação e execução no repositório. | Implementado (README, `requirements.txt` e testes) |
| RNF06 | Configurabilidade: limites e modelos ajustáveis sem alterar código. | Parcial (limites, modelo e recuperação estão em `config.toml`; parâmetros de segurança de conta estão no código) |
| RNF07 | Segurança de credenciais: senhas com hash forte e salt, sessões revogáveis e proteção contra tentativas repetidas de login. | Implementado |
| RNF08 | Identidade visual: interface escura, moderna, com a marca da Universidade Atitus. | Implementado |

## 9. Avaliação de desempenho

**Status geral: Pendente.** Nenhuma métrica desta seção foi calculada. O registro de tokens e custo (RF12) é o único insumo já disponível. Os 20 testes automatizados (pytest) verificam comportamento, e não a qualidade das respostas. Eles cobrem a extração de PDF e PPTX, a validação de limites antes de processar, o cache, a recusa fora do material, o destaque de termos, e o banco e a autenticação.

| Dimensão | Como medir | Métrica |
|---|---|---|
| Recuperação | Perguntas de referência, verificando se o trecho-fonte correto aparece entre os k primeiros | Acerto@k e MRR |
| Respostas do chat | Comparação com resposta de referência, checagem de apoio nos trechos (RAGAs), LLM como juiz e revisão manual de amostra | Fidelidade, relevância e acerto (%) |
| Quiz | Revisão humana das questões geradas | % de gabaritos corretos; nota de 1 a 5 para distratores |
| Resumo e mapa mental | Revisão humana: cobertura dos conceitos centrais e fidelidade à fonte | Nota de 1 a 5; % de nós/termos com fonte válida |
| Linha de base | Mesmas perguntas respondidas pelo LLM sem recuperação | Diferença de acerto com RAG vs. sem RAG |
| Custo | Registro de tokens e preço por etapa | R$ por jornada; comparação com a versão sem cache e sem modelo barato |
| Ganho de aprendizagem (desejável) | Pequeno teste com colegas: grupo que usa a jornada vs. grupo que estuda só com o PDF, mesmo quiz de verificação | Diferença de acerto |

**Metas de qualidade**

- Pelo menos 80% de acerto na recuperação do trecho correto entre os 3 primeiros resultados.
- Pelo menos 90% de gabaritos corretos nos quizzes revisados.
- Melhora mensurável sobre a linha de base sem RAG.
- Custo por jornada documentado e comparado com a arquitetura ingênua.

**Conjunto de avaliação:** a ser criado pelo grupo a partir de material de uma disciplina do curso e de documentos de licença aberta, com perguntas, resposta de referência e trecho-fonte indicado. **Status: Pendente.**

## 10. Aspectos éticos e legais

### 10.1 Dados que o sistema guarda

A versão 1.0 previa processar os arquivos sem armazenamento permanente de dados pessoais. Com a conta de usuário (versão 1.1), essa premissa foi substituída por **minimização e transparência**: o sistema guarda o necessário para a personalização e deve explicar isso ao usuário (pendência RF21).

| Dado | Onde | Finalidade | Retenção |
|---|---|---|---|
| Nome e e-mail | `usuarios` | Identificar o usuário e personalizar a interface | Sem prazo definido; não há exclusão de conta pela interface (RF20) |
| Hash da senha (scrypt) | `usuarios` | Autenticação | Igual ao anterior; a senha em si nunca é guardada |
| Hash do token de sessão | `sessoes` | Manter o login | 7 dias; sessões vencidas são removidas quando uma nova sessão é criada |
| E-mail, data e resultado das tentativas de login | `tentativas_login` | Bloqueio temporário contra tentativas repetidas | Sem prazo definido |
| Título e hash do material de cada caderno | `cadernos` | Reabrir o caderno | Até o usuário excluir o caderno |
| Perguntas e respostas do chat, notas do quiz | `mensagens`, `resultados_quiz` | Histórico personalizado | Removidos junto com o caderno |
| Conteúdo gerado, trechos do texto e imagens extraídas do material | `cache.sqlite` e `data/imagens` | Reaproveitar o conteúdo (RF11) e exibir as fontes | Sem prazo; compartilhado entre usuários |
| Arquivos originais enviados | Não são gravados pelo sistema | n/a | n/a |

**Cache compartilhado (decisão fechada):** o cache é compartilhado entre usuários e indexado apenas pelo hash do material. Ele não contém identificação de usuário, mas guarda, além do conteúdo gerado, os trechos do texto e as imagens do material, necessários para mostrar as fontes. O vínculo entre usuário e material existe somente em `cadernos`.

### 10.2 Pendências de conformidade (LGPD)

- Aviso de privacidade e consentimento no cadastro (RF21).
- Exclusão da conta e dos dados pessoais (RF20).
- Prazo de retenção para dados de conta, tentativas de login e cache.
- Definir se o texto do material guardado no cache exige tratamento específico.

### 10.3 Demais aspectos

- **Direitos autorais:** o sistema usa apenas o material que o próprio usuário envia, sem redistribuí-lo.
- **Confiabilidade:** citação de fonte e recusa reduzem o risco de alucinação, e o sistema avisa que não substitui o professor.
- **Integridade acadêmica:** o foco é estudo e revisão, não resolver avaliações.

## 11. Riscos e mitigações

| Risco | Mitigação |
|---|---|
| Custo de API acima do previsto | Limites de uso, cache, modelo barato, medição contínua de tokens |
| Qualidade ruim do modelo barato em português | Testar 2 ou 3 modelos no conjunto de avaliação antes de fixar (ainda não feito) |
| Mapa mental editável consome muito tempo de interface | Versão mínima (adicionar/remover nós); evolução se sobrar tempo |
| PDFs escaneados ou com pouco texto | Declarado como não suportado nesta versão, com aviso ao usuário |
| Limite de slides frustra o usuário | Mensagem clara e sugestão de dividir o material por tópico |
| Escopo grande para 8 semanas | Priorizar o núcleo (seção 12) e tratar o restante como extensão |
| Recuperação lexical (BM25) recusa perguntas legítimas, sobretudo em materiais pequenos | Ajustar `score_minimo` em `config.toml`; evoluir para embeddings |
| Token de sessão na URL pode ser compartilhado por engano (quem copiar o link logado herda a sessão) | Evoluir para cookie `HttpOnly`; orientar o usuário a não compartilhar o link |
| Servidor escutando em todas as interfaces de rede (`0.0.0.0`), expondo a aplicação na rede | Usar `localhost` em uso local; colocar atrás de HTTPS em produção |
| Dados pessoais sem aviso de privacidade nem exclusão de conta | Implementar RF20 e RF21 e definir prazos de retenção |
| Saída do modo offline é simples (nó central é o nome do arquivo, distratores fracos) | Usar o modo com LLM para demonstrações de qualidade |
| O hash ignora o nome do arquivo: o mesmo PDF renomeado reaproveita o cache e as citações mostram o nome antigo | Aceitável no protótipo; avaliar incluir o nome no hash ou remapear as fontes |

## 12. Priorização e cronograma (8 semanas)

### Essencial (núcleo)

| Item | Status |
|---|---|
| Extração, indexação e cache | Implementado (indexação lexical) |
| Etapa 1 (resumo), etapa 2 (mapa mental), etapa 3 (quiz) e etapa 4 (chat limitado) | Implementado |
| Citação de fonte e recusa | Implementado |
| Limites de uso e registro de custo | Implementado |
| Avaliação quantitativa | Pendente |

### Desejável

| Item | Status |
|---|---|
| Edição do mapa mental pelo usuário | Implementado (não persiste) |
| Teste de ganho de aprendizagem com colegas | Pendente |
| Clique na citação abrindo o PDF/slide na página correspondente | Pendente |

### Cronograma sugerido

| Semanas | Atividade |
|---|---|
| 1 | Pesquisa, definição final de limites e escolha dos modelos candidatos |
| 1 a 2 | Preparação dos dados e do conjunto de avaliação |
| 2 a 3 | Extração, divisão em trechos, embeddings e indexação |
| 3 a 5 | Geração de resumo, mapa mental e quiz; cache; chat limitado |
| 4 a 6 | Interface (Streamlit) e integração das etapas |
| 6 a 7 | Avaliação de qualidade e de custo; ajustes |
| 7 a 8 | Documentação, preparação e apresentação |

## 13. Extensões futuras (fora do escopo atual)

- Embeddings multilíngues com ChromaDB no lugar do BM25 (a troca é isolada em `retrieval.py`).
- Avaliação automática com RAGAs, Acerto@k e MRR.
- Suporte a PDFs escaneados (OCR).
- Exclusão de conta, recuperação de senha e cookie `HttpOnly` para a sessão.
- Persistência das edições do mapa mental.
- Bot no Telegram com revisão espaçada dos termos-chave.
- Exportação do resumo e do grafo para Obsidian (Markdown com links).
- GraphRAG completo como base do mapa mental e da recuperação.
- Podcast de estudo com TTS.
- Cruzamento entre múltiplos materiais.
- Mapa de domínio (cores dos nós conforme desempenho no quiz).
- Modo "tenho X minutos".

## 14. Critérios de aceite do protótipo

| # | Critério | Status | Como foi verificado |
|---|---|---|---|
| 1 | Um aluno leigo cria conta, envia um PDF ou PPTX dentro do limite e conclui as etapas sem configurar nada. | Implementado | Conta criada e caderno percorrido na interface; geração testada com PDF e PPTX nos testes automatizados. O envio pelo seletor de arquivos não foi exercitado no navegador de teste |
| 2 | Todo conteúdo gerado exibe a fonte (arquivo e página/slide). | Implementado | Inspeção da interface; os termos-chave não exibem fonte individual |
| 3 | O chat bloqueia a 4ª pergunta e mostra o contador corretamente. | Implementado | Contador verificado na interface; o bloqueio é feito por código (entrada desabilitada com 0 restantes) |
| 4 | Um envio acima do limite é recusado com mensagem clara, antes de qualquer chamada ao LLM. | Implementado | Teste com LLM simulado: excesso de páginas, de MB, formato inválido, PDF corrompido e limite diário |
| 5 | Reabrir uma jornada já processada não gera novas chamadas ao LLM. | Implementado | Teste com LLM simulado contando chamadas |
| 6 | As métricas da seção 9 são calculadas e documentadas no repositório. | Pendente | n/a |
| 7 | Um usuário cria conta, sai, entra de novo e encontra seus cadernos, histórico de dúvidas e notas. | Implementado | Fluxo executado no navegador |
| 8 | Um usuário não acessa os cadernos de outro. | Implementado | Teste automatizado do banco |

Observação: o caminho com LLM real não foi exercitado (não havia chave de API). Ele foi verificado apenas com um LLM simulado que devolve saídas inválidas de propósito, para testar as validações.

## 15. Decisões

### 15.1 Decisões fechadas

- [x] **Valores dos limites:** 40 páginas/slides por jornada, 20 MB por arquivo, 5 perguntas no quiz, 3 no chat e 20 jornadas por usuário por dia (ajustáveis em `config.toml`).
- [x] **Pergunta recusada** por falta de base **não** consome o limite de 3 do chat.
- [x] **Cache compartilhado entre usuários**, indexado por hash, guardando o conteúdo gerado e os trechos do texto.
- [x] **Conta de usuário obrigatória**, com cadernos e histórico por usuário.
- [x] **Navegação livre** entre Resumo, Mapa mental, Quiz e Dúvidas depois do envio.
- [x] **Recuperação inicial com BM25**, com troca por embeddings prevista.

### 15.2 Decisões em aberto

- [ ] Modelo(s) de API a utilizar, após teste em português (o padrão atual é `gpt-4o-mini`).
- [ ] Política de privacidade: texto do aviso, consentimento, prazos de retenção e exclusão de conta (RF20 e RF21).
- [ ] Hospedagem para demonstração (rodar localmente ou publicar), HTTPS e como a chave de API será protegida.
- [ ] Definir se haverá teste de ganho de aprendizagem com colegas.
- [ ] Meta de custo por jornada, após a medição com LLM real.

## 16. Referências

- ANDERSON, L. W.; KRATHWOHL, D. R. (ed.). A taxonomy for learning, teaching, and assessing: a revision of Bloom's taxonomy of educational objectives. New York: Longman, 2001.
- BRASIL. Lei nº 13.709, de 14 de agosto de 2018. Lei Geral de Proteção de Dados Pessoais (LGPD).
- ES, S. et al. RAGAs: automated evaluation of retrieval augmented generation. EACL: System Demonstrations, 2024.
- LEWIS, P. et al. Retrieval-augmented generation for knowledge-intensive NLP tasks. NeurIPS, 2020.
- REIMERS, N.; GUREVYCH, I. Sentence-BERT: sentence embeddings using Siamese BERT-networks. EMNLP-IJCNLP, 2019.
- ZHENG, L. et al. Judging LLM-as-a-judge with MT-Bench and Chatbot Arena. NeurIPS, 2023.
