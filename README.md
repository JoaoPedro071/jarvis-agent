# Jarvis Agent

**Assistente de tarefas que entende pedidos em português, executa a ação num sistema real e mostra com números o quanto acerta.**

> Projeto pessoal em desenvolvimento. Ainda não foi validado com usuários de uma empresa.

## Em 30 segundos

| | |
|---|---|
| **Problema** | Pedidos de trabalho chegam em texto livre ("me lembra de entregar o relatório sexta"). Em agendas comuns, a tarefa vira um evento: passou o dia, ninguém cobra, e o que ficou pendente some. |
| **Solução** | Um agente com LLM entende o pedido, escolhe a ação certa (criar, listar, concluir, replanejar) e grava num banco. Tarefa atrasada não some: é replanejada e contada. |
| **Resultado** | Na avaliação interna (22 frases), o sistema acertou a decisão em 18 casos. Antes de mover o cálculo de datas do modelo para o código, eram 13. O número provavelmente é otimista: a validação com frases novas está em andamento. |
| **O que demonstra** | LLM com chamada de função, avaliação reprodutível, log de cada decisão, testes automatizados e decisões tomadas com base em medição. |
| **Custo e privacidade** | Roda local (Ollama): nenhum dado sai da máquina e não há custo por chamada. Em troca, cada decisão leva de 4 a 10 s no hardware usado (CPU, 16 GB de RAM). |

## O problema

Quem trabalha com prazos lida com pedidos que nascem em frases soltas: uma mensagem, uma reunião, um e-mail. Para registrar, é preciso abrir uma ferramenta, preencher título, data e categoria, e depois lembrar de voltar nela. Nas agendas tradicionais, a tarefa é tratada como um evento num horário. Quando o dia passa sem a tarefa ser feita, ela fica no passado e deixa de ser cobrada.

O resultado é conhecido: pendências esquecidas e tempo gasto reorganizando manualmente o que ficou para trás. Esse problema surgiu na minha própria rotina com o Google Agenda, e foi o ponto de partida do projeto.

## Como o projeto resolve

1. **Linguagem natural vira ação.** O usuário escreve como falaria ("me lembra de estudar banco de dados amanhã") e o agente decide qual ação executar.
2. **Tarefa e tempo são coisas separadas.** A tarefa vive num banco com estado. A rotina de replanejamento garante que **tarefa atrasada não some**: ela vai para hoje e ganha +1 no contador de adiamentos. Com 3 adiamentos, é sinalizada para ser quebrada em partes menores ou cancelada. Esse comportamento é garantido por teste automatizado.
3. **O modelo não decide tudo.** O que um modelo pequeno faz mal, como conta de calendário, passa para código determinístico. Isso elevou o acerto na criação de tarefas de 2 para 7 em 8 casos.
4. **Tudo é medido e registrado.** Cada decisão do agente fica num log, e uma avaliação reprodutível mostra onde o sistema acerta e onde erra.

## Onde o mesmo padrão se aplica

Estes cenários são **aplicações possíveis** do padrão (pedido em texto livre, ação num sistema, guarda de segurança em código, log e avaliação). O projeto não foi testado em nenhum deles.

- **Triagem de solicitações:** transformar mensagens de clientes ou chamados em registro com categoria, responsável e prazo.
- **Assistentes internos de operação:** criar, consultar e atualizar registros por linguagem natural, com trilha de auditoria das decisões.
- **Follow-ups de times comerciais e de suporte:** garantir que o que ficou pendente volte para a fila em vez de se perder.

## O que este projeto demonstra

| Competência | Evidência no repositório |
|---|---|
| LLM com ferramentas (function calling) | [`agent/tools.py`](agent/tools.py) e [`agent/agent.py`](agent/agent.py): o modelo escolhe a ferramenta e o código a executa |
| Medir antes de opinar | [`avaliacao/`](avaliacao/): 22 casos com gabarito, temperatura 0, quatro configurações comparadas |
| Reportar resultado negativo | A versão v3 piorou a escolha de ferramenta (14/22) e ficou registrada, com a análise do porquê |
| Decisão pragmática de engenharia | Datas extraídas por código ([`agent/datas.py`](agent/datas.py)) em vez de pedir ao modelo |
| Observabilidade | Log por decisão, com o que o modelo mandou e o que o código corrigiu |
| Qualidade de código | Testes automatizados em [`tests/`](tests/), incluindo um modelo simulado |
| Honestidade sobre limites | Seção de limitações abaixo, antes de qualquer promessa |

## Como foi construído

Construí o projeto em etapas, com apoio do Claude (assistente de IA) para gerar e revisar código. Defini o problema e o escopo, montei o ambiente no meu notebook, executei os testes e as avaliações e conduzi as decisões de cada etapa, como separar uma mudança por vez para saber o que de fato melhora o resultado.

---

# Detalhes técnicos

> Estado: fatia funcional da primeira etapa de um sistema maior (agentes para LinkedIn, estudos e agenda).

## Ferramentas do agente

| Ferramenta | O que faz |
|---|---|
| `add_task` | Cria uma tarefa (título e data opcional) |
| `list_tasks` | Lista tarefas abertas, de hoje ou atrasadas |
| `complete_task` | Conclui uma tarefa pelo id |
| `rollover_overdue` | Move as atrasadas para hoje e conta o adiamento |

## Como funciona

```
pedido do usuário
      |
      v
  LLM local (Ollama)  --->  escolhe uma ferramenta + argumentos
      |
      v
  código valida e ajusta os argumentos (ex.: datas)
      |
      v
  executa a ferramenta no SQLite  --->  resultado volta ao LLM  --->  resposta
      |
      +--->  log JSONL de cada decisão (logs/decisoes.jsonl)
```

Decisões de projeto:

- **Erros voltam como dado.** Se o modelo manda um argumento inválido, a ferramenta devolve `{"error": ...}` e o modelo pode corrigir, em vez de o programa quebrar.
- **Limite de passos.** O loop para depois de 5 chamadas, para o agente não entrar em ciclo.
- **LLM trocável.** O agente recebe o "cérebro" como função, o que permite testes com um modelo simulado e a troca de provedor (local ou nuvem) sem mexer no resto.
- **Datas por código.** Um extrator por regras lê a data no pedido do usuário, e o modelo só informa o título.
- **Log transparente.** Pedido, ferramenta, argumentos, resultado e tempo ficam registrados. Quando o código corrige algo que o modelo mandou, os dois valores aparecem.

## Como rodar (Linux/Debian)

```bash
sudo apt install -y python3 python3-venv git curl zstd
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.2:3b

git clone https://github.com/JoaoPedro071/jarvis-agent.git
cd jarvis-agent
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python -m pytest -q      # testes automáticos
python -m agent.cli      # conversa com o agente
```

Frases para testar: `me lembra de estudar banco de dados amanhã`, `o que tenho para hoje?`, `conclui a tarefa 1`, `replaneja minhas tarefas atrasadas`.

### Configuração por variáveis de ambiente

| Variável | Padrão | Para que serve |
|---|---|---|
| `JARVIS_MODEL` | `llama3.2:3b` | Modelo do Ollama |
| `JARVIS_PROMPT` | `v2` | Versão do prompt (`v1`, `v2`, `v3`) |
| `JARVIS_DATAS` | `modelo` | `codigo` extrai a data do pedido por regras |
| `JARVIS_TEMPERATURA` | `0` | 0 deixa as respostas reproduzíveis |
| `JARVIS_DB` | `jarvis.db` | Arquivo do banco SQLite |
| `JARVIS_LOG` | `logs/decisoes.jsonl` | Arquivo do log de decisões |

## Avaliação

`python -m avaliacao.rodar` apresenta 22 frases ao modelo e compara a decisão com um gabarito: a ferramenta certa foi escolhida? Os argumentos estão certos? Nos casos de conversa ("oi", "obrigado!"), o certo é **não chamar nenhuma ferramenta**. A avaliação não executa as ferramentas, usa temperatura 0 e fixa a data de hoje (11/11/2026), então os resultados são reproduzíveis.

Resultados com `llama3.2:3b` (notebook com 16 GB de RAM, só CPU):

| Configuração | Acertos | Ferramenta certa | Criar tarefa | Conversa | Listar / concluir / replanejar |
|---|---|---|---|---|---|
| v1 (prompt base) | 12/22 | 18/22 | 2/8 | 0/4 | 10/10 |
| v2 (regras de conversa e de não inventar) | 13/22 | 19/22 | 2/8 | 1/4 | 10/10 |
| v3 (três mudanças de uma vez) | 12/22 | 14/22 | 2/8 | 1/4 | 9/10 |
| **v2 + datas por código** | **18/22** | 19/22 | **7/8** | 1/4 | 10/10 |

O que os números mostram:

- O modelo de 3B acerta as intenções bem marcadas (listar, concluir, replanejar) e erra em **saber quando não agir** e em **datas**.
- Reescrever o prompt deixou de render: v1, v2 e v3 ficaram entre 12 e 13 acertos.
- **O v3 piorou** a escolha de ferramenta. Ele mudou prompt, schema e extração de datas juntos, então não dá para atribuir a queda a uma causa só. Ficou registrado como experimento negativo.
- Isolar uma mudança por vez deu resultado: **tirar a conta de datas do modelo e passar para o código** subiu "criar tarefa" de 2/8 para 7/8.
- A decisão leva de 4 a 10 s na maioria dos casos. O primeiro caso de cada rodada leva cerca de 45 a 60 s, por causa do carregamento do modelo.

Os arquivos completos ficam em `avaliacao/resultados/`.

## Limitações e cuidados ao ler os números

- Os 22 casos foram escritos junto com o extrator de datas, olhando as mesmas frases. **O 18/22 é provavelmente otimista.** Está em andamento um conjunto de validação com frases novas, rodado uma única vez ao final.
- A melhora nas datas vem do código, não do modelo. A métrica descreve o desempenho do **sistema**.
- O modelo de 3B às vezes age quando deveria só conversar e corrompe acentos em títulos (ex.: "inglçãs").
- O extrator de datas é por regras: "estudar a segunda lei de Newton" seria lido como "segunda-feira".
- A avaliação mede só a decisão. O texto final da resposta pode inventar itens e ainda não é avaliado.
- Testado em um único notebook, com um único usuário.
- Para uso real em uma empresa faltariam, entre outras coisas: autenticação e múltiplos usuários, integração com os sistemas já usados (Google Agenda, Notion), revisão de segurança e validação com usuários reais.

## Estrutura

```
agent/
  agent.py     loop do agente, prompts, log
  tools.py     ferramentas e seus schemas
  datas.py     extração de datas em português
  db.py        SQLite
  cli.py       conversa no terminal
avaliacao/
  casos.py     22 casos com gabarito
  rodar.py     avaliador
  resultados/  saídas de cada rodada
tests/         testes automáticos
```

## Próximos passos

- Resolver a categoria "conversa", comparando um modelo maior (8B) e uma ferramenta explícita de resposta.
- Roteamento entre modelos: local para o que ele acerta, modelo maior ou em nuvem para o que é difícil, decidido com base na avaliação.
- Integração real com o Google Agenda e com o Notion.
- Agentes para LinkedIn e estudos.
- Vídeo curto de demonstração.

---

Autor: João Pedro | [github.com/JoaoPedro071](https://github.com/JoaoPedro071)
