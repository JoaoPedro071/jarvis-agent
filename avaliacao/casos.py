"""Casos de teste da avaliacao. Hoje fixo = quarta-feira, 2026-11-11.

esperado.tool: nome da ferramenta, ou None quando o agente NAO deve chamar ferramenta.
esperado.args: cada chave deve bater.
  - texto/numero: igualdade
  - {"contem": "x"}: o argumento precisa conter x (sem diferenciar maiusculas e acentos)
  - None: o argumento nao pode ser preenchido
"""

CASOS = [
    # conversa: nao deve chamar ferramenta
    {"id": "c01", "categoria": "conversa", "frase": "oi", "esperado": {"tool": None, "args": {}}},
    {"id": "c02", "categoria": "conversa", "frase": "bom dia, tudo bem?", "esperado": {"tool": None, "args": {}}},
    {"id": "c03", "categoria": "conversa", "frase": "obrigado!", "esperado": {"tool": None, "args": {}}},
    {"id": "c04", "categoria": "conversa", "frase": "qual a capital da França?", "esperado": {"tool": None, "args": {}}},

    # criar tarefa
    {"id": "c05", "categoria": "criar", "frase": "me lembra de estudar banco de dados amanhã",
     "esperado": {"tool": "add_task", "args": {"title": {"contem": "banco de dados"}, "due_date": "2026-11-12"}}},
    {"id": "c06", "categoria": "criar", "frase": "anota: entregar o ME1 sexta-feira",
     "esperado": {"tool": "add_task", "args": {"title": {"contem": "ME1"}, "due_date": "2026-11-13"}}},
    {"id": "c07", "categoria": "criar", "frase": "preciso pagar a internet hoje",
     "esperado": {"tool": "add_task", "args": {"title": {"contem": "internet"}, "due_date": "2026-11-11"}}},
    {"id": "c08", "categoria": "criar", "frase": "adiciona estudar inglês na segunda",
     "esperado": {"tool": "add_task", "args": {"title": {"contem": "ingles"}, "due_date": "2026-11-16"}}},
    {"id": "c09", "categoria": "criar", "frase": "me lembra de ligar para o dentista depois de amanhã",
     "esperado": {"tool": "add_task", "args": {"title": {"contem": "dentista"}, "due_date": "2026-11-13"}}},
    {"id": "c10", "categoria": "criar", "frase": "anota comprar café dia 20",
     "esperado": {"tool": "add_task", "args": {"title": {"contem": "cafe"}, "due_date": "2026-11-20"}}},
    {"id": "c11", "categoria": "criar", "frase": "criar tarefa revisar o README",
     "esperado": {"tool": "add_task", "args": {"title": {"contem": "readme"}, "due_date": None}}},
    {"id": "c12", "categoria": "criar", "frase": "me lembra de estudar",
     "esperado": {"tool": "add_task", "args": {"title": {"contem": "estudar"}, "due_date": None}}},

    # listar
    {"id": "c13", "categoria": "listar", "frase": "o que tenho para hoje?",
     "esperado": {"tool": "list_tasks", "args": {"scope": "today"}}},
    {"id": "c14", "categoria": "listar", "frase": "mostra minhas tarefas atrasadas",
     "esperado": {"tool": "list_tasks", "args": {"scope": "overdue"}}},
    {"id": "c15", "categoria": "listar", "frase": "tenho algo atrasado?",
     "esperado": {"tool": "list_tasks", "args": {"scope": "overdue"}}},
    {"id": "c16", "categoria": "listar", "frase": "quais são todas as minhas tarefas?",
     "esperado": {"tool": "list_tasks", "args": {"scope": "open"}}},
    {"id": "c17", "categoria": "listar", "frase": "o que está pendente?",
     "esperado": {"tool": "list_tasks", "args": {"scope": "open"}}},

    # concluir
    {"id": "c18", "categoria": "concluir", "frase": "conclui a tarefa 3",
     "esperado": {"tool": "complete_task", "args": {"task_id": 3}}},
    {"id": "c19", "categoria": "concluir", "frase": "terminei a tarefa número 7",
     "esperado": {"tool": "complete_task", "args": {"task_id": 7}}},
    {"id": "c20", "categoria": "concluir", "frase": "marca como feita a tarefa 12",
     "esperado": {"tool": "complete_task", "args": {"task_id": 12}}},

    # replanejar
    {"id": "c21", "categoria": "replanejar", "frase": "replaneja minhas tarefas atrasadas",
     "esperado": {"tool": "rollover_overdue", "args": {}}},
    {"id": "c22", "categoria": "replanejar", "frase": "organiza o que ficou para trás",
     "esperado": {"tool": "rollover_overdue", "args": {}}},
]
