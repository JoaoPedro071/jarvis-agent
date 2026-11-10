from datetime import date

from agent.db import conexao


def hoje() -> date:
    """Existe só para os testes conseguirem fingir que hoje é outro dia."""
    return date.today()


def _com_flag(row) -> dict:
    tarefa = dict(row)
    # depois de 3 adiamentos, o agente deve sugerir quebrar ou cancelar
    tarefa["precisa_quebrar"] = tarefa["postponed_count"] >= 3
    return tarefa


def add_task(title: str, due_date: str | None = None) -> dict:
    if not title or not title.strip():
        return {"error": "title vazio"}
    if due_date is not None:
        try:
            date.fromisoformat(due_date)
        except ValueError:
            return {"error": f"due_date invalida: {due_date}. Use YYYY-MM-DD."}
    with conexao() as conn:
        cur = conn.execute(
            "INSERT INTO tasks (title, due_date) VALUES (?, ?)",
            (title.strip(), due_date),
        )
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (cur.lastrowid,)).fetchone()
    return _com_flag(row)


def list_tasks(scope: str = "open") -> dict:
    hoje_str = hoje().isoformat()
    consultas = {
        "open": (
            "SELECT * FROM tasks WHERE status = 'open' ORDER BY due_date IS NULL, due_date, id",
            (),
        ),
        "today": (
            "SELECT * FROM tasks WHERE status = 'open' AND due_date = ? ORDER BY id",
            (hoje_str,),
        ),
        "overdue": (
            "SELECT * FROM tasks WHERE status = 'open' AND due_date < ? ORDER BY due_date, id",
            (hoje_str,),
        ),
    }
    if scope not in consultas:
        return {"error": f"scope invalido: {scope}. Use open, today ou overdue."}
    sql, params = consultas[scope]
    with conexao() as conn:
        rows = conn.execute(sql, params).fetchall()
    return {"tasks": [_com_flag(r) for r in rows]}


def complete_task(task_id: int) -> dict:
    with conexao() as conn:
        cur = conn.execute(
            "UPDATE tasks SET status = 'done' WHERE id = ? AND status = 'open'",
            (task_id,),
        )
        if cur.rowcount == 0:
            return {"error": f"nenhuma tarefa aberta com id {task_id}"}
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    return _com_flag(row)


def rollover_overdue() -> dict:
    """Tarefas abertas com prazo vencido não somem: vão para hoje e ganham +1 adiamento."""
    hoje_str = hoje().isoformat()
    with conexao() as conn:
        ids = [
            r["id"]
            for r in conn.execute(
                "SELECT id FROM tasks WHERE status = 'open' AND due_date < ?", (hoje_str,)
            ).fetchall()
        ]
        for tid in ids:
            conn.execute(
                "UPDATE tasks SET due_date = ?, postponed_count = postponed_count + 1 WHERE id = ?",
                (hoje_str, tid),
            )
        moved = [
            _com_flag(conn.execute("SELECT * FROM tasks WHERE id = ?", (tid,)).fetchone())
            for tid in ids
        ]
    return {"moved": moved}


# Descrições que o LLM lê para decidir qual ferramenta chamar.
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "add_task",
            "description": "Cria uma tarefa nova. Use due_date (YYYY-MM-DD) quando o usuario citar um dia.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Texto curto da tarefa"},
                    "due_date": {"type": "string", "description": "Data no formato YYYY-MM-DD (opcional)"},
                },
                "required": ["title"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_tasks",
            "description": "Lista tarefas abertas. scope: open (todas), today (de hoje) ou overdue (atrasadas).",
            "parameters": {
                "type": "object",
                "properties": {
                    "scope": {"type": "string", "enum": ["open", "today", "overdue"]},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "complete_task",
            "description": "Marca uma tarefa como concluida pelo id.",
            "parameters": {
                "type": "object",
                "properties": {"task_id": {"type": "integer"}},
                "required": ["task_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "rollover_overdue",
            "description": "Move todas as tarefas atrasadas para hoje e conta o adiamento. Use quando o usuario pedir para replanejar ou organizar atrasadas.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]

TOOLS = {
    "add_task": add_task,
    "list_tasks": list_tasks,
    "complete_task": complete_task,
    "rollover_overdue": rollover_overdue,
}


def run_tool(name: str, args: dict) -> dict:
    """Executa a ferramenta pedida pelo LLM. Erros voltam como dado, para o modelo poder corrigir."""
    func = TOOLS.get(name)
    if func is None:
        return {"error": f"ferramenta desconhecida: {name}"}
    try:
        return func(**args)
    except TypeError as e:
        return {"error": f"argumentos invalidos: {e}"}
