from datetime import date

import pytest

from agent import tools


@pytest.fixture(autouse=True)
def banco_temporario(tmp_path, monkeypatch):
    monkeypatch.setenv("JARVIS_DB", str(tmp_path / "teste.db"))
    monkeypatch.setattr(tools, "hoje", lambda: date(2026, 11, 10))


def test_add_e_list():
    t = tools.add_task("Estudar banco de dados", "2026-11-10")
    assert t["id"] == 1
    assert tools.list_tasks("today")["tasks"][0]["title"] == "Estudar banco de dados"


def test_data_invalida_volta_como_erro():
    assert "error" in tools.add_task("x", "algum dia")


def test_rollover_nao_perde_tarefa():
    tools.add_task("Atrasada", "2026-11-05")
    r = tools.rollover_overdue()
    assert len(r["moved"]) == 1
    assert r["moved"][0]["due_date"] == "2026-11-10"
    assert r["moved"][0]["postponed_count"] == 1
    assert tools.list_tasks("overdue")["tasks"] == []


def test_precisa_quebrar_depois_de_3_adiamentos():
    tools.add_task("Teimosa", "2026-11-01")
    for _ in range(3):
        tools.rollover_overdue()
        # simula virar o dia: volta o prazo para o passado
        from agent.db import conexao
        with conexao() as c:
            c.execute("UPDATE tasks SET due_date = '2026-11-01'")
    t = tools.list_tasks("overdue")["tasks"][0]
    assert t["precisa_quebrar"] is True


def test_complete_task():
    tools.add_task("Fazer")
    assert tools.complete_task(1)["status"] == "done"
    assert "error" in tools.complete_task(1)


def test_run_tool_erros():
    assert "error" in tools.run_tool("nao_existe", {})
    assert "error" in tools.run_tool("add_task", {"errado": 1})
